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
GROUP_EDGE_LIMIT = 60
_FRONTMATTER_DELIMITER = "---"


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


def _source_fingerprint(src_root: Path) -> str:
    """Return one cheap content-adjacent fingerprint for source-tree drift checks."""
    digest = hashlib.sha256()
    for py_file in sorted(src_root.rglob("*.py")):
        if py_file.name.endswith(".pyi"):
            continue
        if "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(src_root).as_posix()
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(py_file.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest()


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


def _extract_import_targets(tree: ast.AST, source_module: str) -> list[str]:
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(_import_targets_from_import(node))
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level == 0:
            targets.extend(_import_targets_from_absolute_import_from(node))
            continue

        targets.extend(_import_targets_from_relative_import_from(node, source_module))

    return targets


def _allowed_edge(source_layer: str, target_layer: str) -> bool:
    allowed_targets = LAYER_IMPORT_MATRIX.get(source_layer, frozenset())
    return target_layer in allowed_targets


def _parsed_module_tree(source_file: Path) -> ast.AST | None:
    try:
        source = source_file.read_text(encoding="utf-8")
        return ast.parse(source)
    except SyntaxError:
        return None


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
    """Parse project imports and return aggregated dependency snapshot."""
    layer_counter: Counter[tuple[str, str]] = Counter()
    group_counter: Counter[tuple[str, str]] = Counter()
    source_fingerprint = _source_fingerprint(src_root)

    scanned_modules = 0
    total_internal_imports = 0

    for source_module, source_file in _iter_modules(src_root):
        source_layer = _layer_of(source_module)
        source_group = _group_of(source_module)
        if source_layer is None or source_group is None:
            continue

        scanned_modules += 1
        tree = _parsed_module_tree(source_file)
        if tree is None:
            continue

        for target_module in _extract_import_targets(tree, source_module):
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
        source_fingerprint=source_fingerprint,
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


def _check_file_sync(path: Path, expected: str) -> bool:
    if not path.exists():
        print(f"[drift] missing file: {path.relative_to(PROJECT_ROOT)}")
        return False
    actual = path.read_text(encoding="utf-8")
    if path.suffix == ".md":
        _, actual = _split_frontmatter(actual)
    if actual == expected:
        return True
    print(f"[drift] mismatch: {path.relative_to(PROJECT_ROOT)}")
    return False


def _markdown_to_write(path: Path, markdown: str) -> str:
    """Preserve frontmatter from existing markdown output when present."""
    current_markdown = path.read_text(encoding="utf-8") if path.exists() else ""
    frontmatter, _ = _split_frontmatter(current_markdown)
    return f"{frontmatter}{markdown}" if frontmatter else markdown


def _snapshot_from_json_payload(payload: dict[str, object]) -> DependencySnapshot | None:
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
