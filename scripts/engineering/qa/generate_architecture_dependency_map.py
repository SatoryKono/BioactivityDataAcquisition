#!/usr/bin/env python3
"""Generate architecture dependency map docs from source imports.

The script scans ``src/bioetl`` Python modules, aggregates imports by layer and
module groups, and emits compact architecture docs artifacts:

- Markdown report for docs navigation
- JSON report for machine checks and CI artifacts

Use ``--check`` in CI to fail on drift between code and committed docs.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import time
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SRC_ROOT = PROJECT_ROOT / "src" / "bioetl"
DEFAULT_MD_OUTPUT = (
    PROJECT_ROOT / "docs" / "02-architecture" / "generated" / "module-dependency-map.md"
)
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT
    / "docs"
    / "02-architecture"
    / "generated"
    / "module-dependency-map.json"
)

LAYER_IMPORT_MATRIX: dict[str, frozenset[str]] = {
    "domain": frozenset({"domain"}),
    "application": frozenset({"domain", "application"}),
    "infrastructure": frozenset({"domain", "infrastructure"}),
    "composition": frozenset(
        {"domain", "application", "infrastructure", "composition"}
    ),
    "interfaces": frozenset({"domain", "application", "composition", "interfaces"}),
}

LAYER_ORDER = tuple(LAYER_IMPORT_MATRIX.keys())
GROUP_EDGE_LIMIT = 55
TYPE_CHECKING_NAME = "TYPE_CHECKING"
_FRONTMATTER_DELIMITER = "---"
MAX_SOURCE_TREE_STABILIZATION_ATTEMPTS = 8
SOURCE_TREE_STABILIZATION_SLEEP_SECONDS = 0.1


def _render_markdown_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    right_align_columns: frozenset[int] = frozenset(),
) -> list[str]:
    """Render a stable aligned markdown table."""
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def _format_row(row: list[str]) -> str:
        formatted_cells: list[str] = []
        for index, cell in enumerate(row):
            width = widths[index]
            if index in right_align_columns:
                formatted_cells.append(cell.rjust(width))
            else:
                formatted_cells.append(cell.ljust(width))
        return f"| {' | '.join(formatted_cells)} |"

    separator_cells: list[str] = []
    for index, width in enumerate(widths):
        if index in right_align_columns:
            separator_cells.append("-" * max(width - 1, 1) + ":")
        else:
            separator_cells.append("-" * width)

    rendered = [_format_row(headers), f"| {' | '.join(separator_cells)} |"]
    rendered.extend(_format_row(row) for row in rows)
    return rendered


@dataclass(frozen=True)
class LayerEdge:
    """Aggregated dependency between architecture layers."""

    source: str
    target: str
    imports: int
    allowed: bool


@dataclass(frozen=True)
class GroupEdge:
    """Aggregated dependency between compact module groups."""

    source: str
    target: str
    imports: int


@dataclass(frozen=True)
class DependencySnapshot:
    """Full snapshot used for markdown/json generation."""

    scanned_modules: int
    total_internal_imports: int
    layer_edges: list[LayerEdge]
    cross_layer_group_edges: list[GroupEdge]
    cross_layer_group_edges_total: int
    violations: list[LayerEdge]
    source_fingerprint: str


@dataclass(frozen=True)
class _SourceModuleSnapshot:
    """Stable source snapshot used for fingerprinting and AST collection."""

    module_name: str
    relative_path: str
    source_bytes: bytes


def _module_name_from_path(path: Path, src_root: Path) -> str:
    rel = path.relative_to(src_root)
    parts = list(rel.parts)
    if not parts:
        return "bioetl"
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = Path(parts[-1]).stem
    return ".".join(["bioetl", *parts]) if parts else "bioetl"


def _iter_modules(src_root: Path) -> Iterable[tuple[str, Path]]:
    for py_file in sorted(src_root.rglob("*.py")):
        if py_file.name.endswith(".pyi"):
            continue
        if "__pycache__" in py_file.parts:
            continue
        yield _module_name_from_path(py_file, src_root), py_file


def _read_source_module_snapshots_once(src_root: Path) -> list[_SourceModuleSnapshot]:
    """Read one full source-tree snapshot, skipping transiently vanished files."""
    snapshots: list[_SourceModuleSnapshot] = []
    for module_name, py_file in _iter_modules(src_root):
        try:
            source_bytes = py_file.read_bytes()
        except FileNotFoundError:
            continue
        except (OSError, PermissionError):
            continue
        snapshots.append(
            _SourceModuleSnapshot(
                module_name=module_name,
                relative_path=py_file.relative_to(src_root).as_posix(),
                source_bytes=source_bytes,
            )
        )
    return snapshots


def _snapshot_digest(snapshots: Iterable[_SourceModuleSnapshot]) -> str:
    """Return a deterministic fingerprint for one source snapshot."""
    digest = hashlib.sha256()
    for snapshot in snapshots:
        digest.update(snapshot.relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(snapshot.source_bytes).digest())
        digest.update(b"\0")
    return digest.hexdigest()


def _read_stable_source_module_snapshots(
    src_root: Path,
    *,
    max_attempts: int = MAX_SOURCE_TREE_STABILIZATION_ATTEMPTS,
) -> tuple[list[_SourceModuleSnapshot], str]:
    """Retry shared-drive reads and prefer the largest stable readable snapshot."""
    best_snapshots: list[_SourceModuleSnapshot] | None = None
    best_digest: str | None = None
    best_paths: tuple[str, ...] = ()
    previous_paths: tuple[str, ...] | None = None
    previous_digest: str | None = None

    for attempt in range(max_attempts):
        snapshots = _read_source_module_snapshots_once(src_root)
        digest = _snapshot_digest(snapshots)
        repo_paths = tuple(snapshot.relative_path for snapshot in snapshots)
        if best_snapshots is None or len(repo_paths) > len(best_paths):
            best_snapshots = snapshots
            best_digest = digest
            best_paths = repo_paths
        if repo_paths == previous_paths and digest == previous_digest:
            return snapshots, digest
        previous_paths = repo_paths
        previous_digest = digest
        if attempt + 1 < max_attempts:
            time.sleep(SOURCE_TREE_STABILIZATION_SLEEP_SECONDS)

    assert best_snapshots is not None and best_digest is not None
    return best_snapshots, best_digest


def _source_fingerprint(src_root: Path) -> str:
    """Return one cheap content-adjacent fingerprint for source-tree drift checks."""
    _, digest = _read_stable_source_module_snapshots(src_root)
    return digest


def _layer_of(module_name: str) -> str | None:
    parts = module_name.split(".")
    if len(parts) < 2 or parts[0] != "bioetl":
        return None
    layer = parts[1]
    return layer if layer in LAYER_IMPORT_MATRIX else None


def _group_of(module_name: str) -> str | None:
    parts = module_name.split(".")
    layer = _layer_of(module_name)
    if layer is None:
        return None
    if len(parts) < 3:
        return f"{layer}._root"
    return f"{layer}.{parts[2]}"


def _resolve_relative_import_base(source_module: str, level: int) -> list[str]:
    package_parts = source_module.split(".")[:-1]
    depth = max(level - 1, 0)
    if depth > len(package_parts):
        return []
    if depth == 0:
        return package_parts
    return package_parts[:-depth]


def _import_targets_from_import(node: ast.Import) -> list[str]:
    return [alias.name for alias in node.names]


def _import_targets_from_absolute_import_from(node: ast.ImportFrom) -> list[str]:
    if not node.module:
        return []
    targets = [node.module]
    if node.module == "bioetl":
        targets.extend(
            f"bioetl.{alias.name}" for alias in node.names if alias.name != "*"
        )
    return targets


def _import_targets_from_relative_import_from(
    node: ast.ImportFrom,
    source_module: str,
) -> list[str]:
    base_parts = _resolve_relative_import_base(source_module, node.level)
    if not base_parts:
        return []
    if node.module:
        return [".".join([*base_parts, node.module])]
    return [
        ".".join([*base_parts, alias.name]) for alias in node.names if alias.name != "*"
    ]


def _is_type_checking_guard(test: ast.AST) -> bool:
    """Return True when an ``if`` branch is guarded by ``TYPE_CHECKING``."""
    if isinstance(test, ast.Name):
        return test.id == TYPE_CHECKING_NAME
    if isinstance(test, ast.Attribute):
        return test.attr == TYPE_CHECKING_NAME
    if isinstance(test, ast.BoolOp):
        if isinstance(test.op, ast.And):
            return any(_is_type_checking_guard(value) for value in test.values)
        if isinstance(test.op, ast.Or):
            return all(_is_type_checking_guard(value) for value in test.values)
    return False


class _RuntimeImportTargetVisitor(ast.NodeVisitor):
    """Collect imports that affect runtime dependency topology."""

    def __init__(self, source_module: str) -> None:
        self._source_module = source_module
        self.targets: list[str] = []

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_guard(node.test):
            for child in node.orelse:
                self.visit(child)
            return
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        self.targets.extend(_import_targets_from_import(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.level == 0:
            self.targets.extend(_import_targets_from_absolute_import_from(node))
            return
        self.targets.extend(
            _import_targets_from_relative_import_from(node, self._source_module)
        )


def _extract_import_targets(tree: ast.AST, source_module: str) -> list[str]:
    visitor = _RuntimeImportTargetVisitor(source_module)
    visitor.visit(tree)
    return visitor.targets


def _allowed_edge(source_layer: str, target_layer: str) -> bool:
    allowed_targets = LAYER_IMPORT_MATRIX.get(source_layer, frozenset())
    return target_layer in allowed_targets


def _parsed_module_tree_from_source(source: str) -> ast.AST | None:
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _parsed_module_tree(source_file: Path) -> ast.AST | None:
    return _parsed_module_tree_from_source(source_file.read_text(encoding="utf-8"))


def _record_import_target(
    target_module: str,
    *,
    source_layer: str,
    source_group: str,
    layer_counter: Counter[tuple[str, str]],
    group_counter: Counter[tuple[str, str]],
) -> int:
    if not target_module.startswith("bioetl."):
        return 0

    target_layer = _layer_of(target_module)
    if target_layer is None:
        return 0

    layer_counter[(source_layer, target_layer)] += 1
    if source_layer != target_layer:
        target_group = _group_of(target_module)
        if target_group is not None:
            group_counter[(source_group, target_group)] += 1
    return 1


def collect_dependency_snapshot(src_root: Path) -> DependencySnapshot:
    """Parse runtime project imports and return aggregated dependency snapshot."""
    layer_counter: Counter[tuple[str, str]] = Counter()
    group_counter: Counter[tuple[str, str]] = Counter()
    snapshots, source_digest = _read_stable_source_module_snapshots(src_root)

    scanned_modules = 0
    total_internal_imports = 0

    for snapshot in snapshots:
        source_layer = _layer_of(snapshot.module_name)
        source_group = _group_of(snapshot.module_name)
        if source_layer is None or source_group is None:
            continue

        scanned_modules += 1
        tree = _parsed_module_tree_from_source(snapshot.source_bytes.decode("utf-8"))
        if tree is None:
            continue

        for target_module in _extract_import_targets(tree, snapshot.module_name):
            total_internal_imports += _record_import_target(
                target_module,
                source_layer=source_layer,
                source_group=source_group,
                layer_counter=layer_counter,
                group_counter=group_counter,
            )

    layer_edges = [
        LayerEdge(
            source=source,
            target=target,
            imports=count,
            allowed=_allowed_edge(source, target),
        )
        for (source, target), count in sorted(layer_counter.items())
    ]

    sorted_group_edges = sorted(
        group_counter.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    )
    group_edges_total = len(sorted_group_edges)

    group_edges = [
        GroupEdge(source=source, target=target, imports=count)
        for (source, target), count in sorted_group_edges[:GROUP_EDGE_LIMIT]
    ]

    violations = [edge for edge in layer_edges if not edge.allowed]

    return DependencySnapshot(
        scanned_modules=scanned_modules,
        total_internal_imports=total_internal_imports,
        layer_edges=layer_edges,
        cross_layer_group_edges=group_edges,
        cross_layer_group_edges_total=group_edges_total,
        violations=violations,
        source_fingerprint=source_digest,
    )


def _summary_section(snapshot: DependencySnapshot) -> list[str]:
    """Render summary bullets for markdown output."""
    return [
        "## Summary",
        "",
        f"- Scanned modules: `{snapshot.scanned_modules}`",
        f"- Internal import edges (raw): `{snapshot.total_internal_imports}`",
        f"- Aggregated layer edges: `{len(snapshot.layer_edges)}`",
        f"- Layer policy violations: `{len(snapshot.violations)}`",
        f"- Cross-layer module-group edges (total): "
        f"`{snapshot.cross_layer_group_edges_total}`",
        f"- Cross-layer module-group edges (top {GROUP_EDGE_LIMIT}): "
        f"`{len(snapshot.cross_layer_group_edges)}`",
        "",
    ]


def _layer_graph_section(snapshot: DependencySnapshot) -> list[str]:
    """Render mermaid layer dependency graph section."""
    lines = ["## Layer Dependency Graph", "", "```mermaid", "flowchart LR"]
    for layer in LAYER_ORDER:
        lines.append(f"    {layer}[{layer}]")
    if snapshot.layer_edges:
        for edge in snapshot.layer_edges:
            marker = "OK" if edge.allowed else "VIOLATION"
            lines.append(
                f"    {edge.source} -->|{edge.imports} {marker}| {edge.target}"
            )
    else:
        lines.append("    domain --> domain")
    lines.extend(["```", ""])
    return lines


def _layer_edge_rows(snapshot: DependencySnapshot) -> list[list[str]]:
    """Return markdown table rows for layer edges."""
    rows = [
        [
            f"`{edge.source}`",
            f"`{edge.target}`",
            str(edge.imports),
            "allowed" if edge.allowed else "violation",
        ]
        for edge in snapshot.layer_edges
    ]
    return rows or [["`-`", "`-`", "0", "-"]]


def _group_edge_rows(snapshot: DependencySnapshot) -> list[list[str]]:
    """Return markdown table rows for cross-layer group edges."""
    rows = [
        [f"`{edge.source}`", f"`{edge.target}`", str(edge.imports)]
        for edge in snapshot.cross_layer_group_edges
    ]
    return rows or [["`-`", "`-`", "0"]]


def _policy_violations_section(snapshot: DependencySnapshot) -> list[str]:
    """Render policy violations list for markdown output."""
    lines = ["## Policy Violations", ""]
    if snapshot.violations:
        for edge in snapshot.violations:
            lines.append(
                f"- `{edge.source} -> {edge.target}` (imports: {edge.imports})"
            )
    else:
        lines.append("- None.")
    lines.append("")
    return lines


def build_markdown(snapshot: DependencySnapshot) -> str:
    """Render markdown report for docs."""
    lines: list[str] = [
        "# Module Dependency Map (Auto-Generated)",
        "",
        "> Generated by `scripts/engineering/qa/generate_architecture_dependency_map.py`. "
        "Do not edit manually.",
        "> This artifact is a layer-policy and coarse topology snapshot only. "
        "It is not a hotspot, duplication, size, or churn scorecard.",
        "",
        *_summary_section(snapshot),
        *_layer_graph_section(snapshot),
    ]

    lines.extend(
        [
            "## Layer Edge Table",
            "",
        ]
    )
    lines.extend(
        _render_markdown_table(
            ["From", "To", "Imports", "Policy"],
            _layer_edge_rows(snapshot),
            right_align_columns=frozenset({2}),
        )
    )

    lines.extend(
        [
            "",
            "## Cross-Layer Module-Group Edges (Compact)",
            "",
        ]
    )
    lines.extend(
        _render_markdown_table(
            ["From Group", "To Group", "Imports"],
            _group_edge_rows(snapshot),
            right_align_columns=frozenset({2}),
        )
    )
    lines.extend(["", *_policy_violations_section(snapshot)])
    return "\n".join(lines)


def build_json(snapshot: DependencySnapshot) -> str:
    """Render machine-readable JSON report."""
    payload = {
        "summary": {
            "scanned_modules": snapshot.scanned_modules,
            "total_internal_imports": snapshot.total_internal_imports,
            "layer_edges": len(snapshot.layer_edges),
            "cross_layer_group_edges": len(snapshot.cross_layer_group_edges),
            "cross_layer_group_edges_total": snapshot.cross_layer_group_edges_total,
            "violations": len(snapshot.violations),
            "source_fingerprint": snapshot.source_fingerprint,
        },
        "layer_edges": [asdict(edge) for edge in snapshot.layer_edges],
        "cross_layer_group_edges": [
            asdict(edge) for edge in snapshot.cross_layer_group_edges
        ],
        "violations": [asdict(edge) for edge in snapshot.violations],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith(f"{_FRONTMATTER_DELIMITER}\n"):
        return None, text
    parts = text.split(f"\n{_FRONTMATTER_DELIMITER}\n", 1)
    if len(parts) != 2:
        return None, text
    frontmatter, body = parts
    return f"{frontmatter}\n{_FRONTMATTER_DELIMITER}\n", body


def _write_text(path: Path, content: str) -> None:
    safe_path = PROJECT_ROOT / path.relative_to(PROJECT_ROOT)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    safe_path.write_text(content, encoding="utf-8")


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _json_summary_field(payload: str, field_name: str) -> object | None:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    summary = decoded.get("summary")
    if not isinstance(summary, dict):
        return None
    return summary.get(field_name)


def _without_source_fingerprint(payload: str) -> object | None:
    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, dict):
        return None
    summary = decoded.get("summary")
    if isinstance(summary, dict):
        summary = dict(summary)
        summary.pop("source_fingerprint", None)
        decoded = dict(decoded)
        decoded["summary"] = summary
    return decoded


def _print_json_drift_details(path: Path, *, actual: str, expected: str) -> None:
    actual_fingerprint = _json_summary_field(actual, "source_fingerprint")
    expected_fingerprint = _json_summary_field(expected, "source_fingerprint")
    display_path = _display_path(path)
    if actual_fingerprint != expected_fingerprint:
        print(
            "[drift] source fingerprint mismatch: "
            f"{display_path} actual={actual_fingerprint!r} "
            f"expected={expected_fingerprint!r}"
        )
        if _without_source_fingerprint(actual) == _without_source_fingerprint(expected):
            print(
                "[drift] topology content matches after removing "
                "summary.source_fingerprint; rerun --update to bind the artifact "
                "to the current src/ tree"
            )


def _check_file_sync(path: Path, expected: str) -> bool:
    if not path.exists():
        print(f"[drift] missing file: {_display_path(path)}")
        return False
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    actual = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        _, actual = _split_frontmatter(actual)
    if actual == expected:
        return True
    print(f"[drift] mismatch: {_display_path(path)}")
    if path.suffix == ".json":
        _print_json_drift_details(path, actual=actual, expected=expected)
    return False


def _markdown_to_write(path: Path, markdown: str) -> str:
    """Preserve frontmatter from existing markdown output when present."""
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    current_markdown = path.read_text(encoding="utf-8") if path.exists() else ""
    frontmatter, _ = _split_frontmatter(current_markdown)
    return f"{frontmatter}{markdown}" if frontmatter else markdown


def _snapshot_from_json_payload(
    payload: dict[str, object],
) -> DependencySnapshot | None:
    """Rehydrate one snapshot from the committed JSON artifact."""
    summary = payload.get("summary")
    layer_edges = payload.get("layer_edges")
    group_edges = payload.get("cross_layer_group_edges")
    violations = payload.get("violations")
    if not isinstance(summary, dict):
        return None
    if not isinstance(layer_edges, list):
        return None
    if not isinstance(group_edges, list):
        return None
    if not isinstance(violations, list):
        return None

    source_fingerprint = summary.get("source_fingerprint")
    if not isinstance(source_fingerprint, str) or not source_fingerprint:
        return None

    try:
        return DependencySnapshot(
            scanned_modules=int(summary["scanned_modules"]),
            total_internal_imports=int(summary["total_internal_imports"]),
            layer_edges=[LayerEdge(**edge) for edge in layer_edges],
            cross_layer_group_edges=[GroupEdge(**edge) for edge in group_edges],
            cross_layer_group_edges_total=int(summary["cross_layer_group_edges_total"]),
            violations=[LayerEdge(**edge) for edge in violations],
            source_fingerprint=source_fingerprint,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _load_cached_snapshot(
    json_output: Path,
    *,
    src_root: Path,
) -> DependencySnapshot | None:
    """Return one cached snapshot when source fingerprint still matches."""
    # Script may be invoked as ``python path/to/file.py`` (CI preflight) without
    # package context; ensure repo root is importable for ``scripts.*``.
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    json_output = resolve_output_path(json_output, root=REPO_ROOT)
    if not json_output.exists():
        return None
    try:
        payload = json.loads(json_output.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    snapshot = _snapshot_from_json_payload(payload)
    if snapshot is None:
        return None
    if snapshot.source_fingerprint != _source_fingerprint(src_root):
        return None
    return snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate/check architecture dependency map artifacts.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed artifacts differ from generated output.",
    )
    mode.add_argument(
        "--update",
        action="store_true",
        help="Write generated artifacts to disk (default mode).",
    )
    parser.add_argument(
        "--src-root",
        type=Path,
        default=DEFAULT_SRC_ROOT,
        help="Path to source root to analyze.",
    )
    parser.add_argument(
        "--md-output",
        type=Path,
        default=DEFAULT_MD_OUTPUT,
        help="Markdown output path.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help="JSON output path.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    snapshot = (
        _load_cached_snapshot(args.json_output, src_root=args.src_root)
        if args.check
        else None
    )
    if snapshot is None:
        snapshot = collect_dependency_snapshot(args.src_root)
    markdown = build_markdown(snapshot)
    json_text = build_json(snapshot)

    if args.check:
        md_ok = _check_file_sync(args.md_output, markdown)
        json_ok = _check_file_sync(args.json_output, json_text)
        if md_ok and json_ok:
            print("[ok] architecture dependency docs are up to date")
            return 0
        print(
            "[hint] run: "
            "python scripts/engineering/qa/generate_architecture_dependency_map.py --update"
        )
        return 1

    _write_text(args.md_output, _markdown_to_write(args.md_output, markdown))
    _write_text(args.json_output, json_text)
    print(
        "[updated] wrote architecture dependency docs:\n"
        f"  - {args.md_output.relative_to(PROJECT_ROOT)}\n"
        f"  - {args.json_output.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
