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
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
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
    "interfaces": frozenset(
        {"domain", "application", "infrastructure", "composition", "interfaces"}
    ),
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


def _extract_import_targets(tree: ast.AST, source_module: str) -> list[str]:
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        if node.level == 0:
            if node.module:
                targets.append(node.module)
                if node.module == "bioetl":
                    for alias in node.names:
                        if alias.name != "*":
                            targets.append(f"bioetl.{alias.name}")
            continue

        base_parts = _resolve_relative_import_base(source_module, node.level)
        if not base_parts:
            continue
        if node.module:
            targets.append(".".join([*base_parts, node.module]))
            continue
        for alias in node.names:
            if alias.name == "*":
                continue
            targets.append(".".join([*base_parts, alias.name]))

    return targets


def _allowed_edge(source_layer: str, target_layer: str) -> bool:
    allowed_targets = LAYER_IMPORT_MATRIX.get(source_layer, frozenset())
    return target_layer in allowed_targets


def collect_dependency_snapshot(src_root: Path) -> DependencySnapshot:
    """Parse project imports and return aggregated dependency snapshot."""
    layer_counter: Counter[tuple[str, str]] = Counter()
    group_counter: Counter[tuple[str, str]] = Counter()

    scanned_modules = 0
    total_internal_imports = 0

    for source_module, source_file in _iter_modules(src_root):
        source_layer = _layer_of(source_module)
        source_group = _group_of(source_module)
        if source_layer is None or source_group is None:
            continue

        scanned_modules += 1
        try:
            source = source_file.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for target_module in _extract_import_targets(tree, source_module):
            if not target_module.startswith("bioetl."):
                continue
            target_layer = _layer_of(target_module)
            if target_layer is None:
                continue

            total_internal_imports += 1
            layer_counter[(source_layer, target_layer)] += 1

            if source_layer != target_layer:
                target_group = _group_of(target_module)
                if target_group is not None:
                    group_counter[(source_group, target_group)] += 1

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
    )


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
        "## Layer Dependency Graph",
        "",
        "```mermaid",
        "flowchart LR",
    ]

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

    lines.extend(
        [
            "```",
            "",
            "## Layer Edge Table",
            "",
        ]
    )

    layer_rows = [
        [
            f"`{edge.source}`",
            f"`{edge.target}`",
            str(edge.imports),
            "allowed" if edge.allowed else "violation",
        ]
        for edge in snapshot.layer_edges
    ]
    if not layer_rows:
        layer_rows.append(["`-`", "`-`", "0", "-"])
    lines.extend(
        _render_markdown_table(
            ["From", "To", "Imports", "Policy"],
            layer_rows,
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

    group_rows = [
        [f"`{edge.source}`", f"`{edge.target}`", str(edge.imports)]
        for edge in snapshot.cross_layer_group_edges
    ]
    if not group_rows:
        group_rows.append(["`-`", "`-`", "0"])
    lines.extend(
        _render_markdown_table(
            ["From Group", "To Group", "Imports"],
            group_rows,
            right_align_columns=frozenset({2}),
        )
    )

    lines.extend(["", "## Policy Violations", ""])
    if snapshot.violations:
        for edge in snapshot.violations:
            lines.append(
                f"- `{edge.source} -> {edge.target}` (imports: {edge.imports})"
            )
    else:
        lines.append("- None.")

    lines.append("")
    return "\n".join(lines)


def build_json(snapshot: DependencySnapshot) -> str:
    """Render machine-readable JSON report."""
    import json

    payload = {
        "summary": {
            "scanned_modules": snapshot.scanned_modules,
            "total_internal_imports": snapshot.total_internal_imports,
            "layer_edges": len(snapshot.layer_edges),
            "cross_layer_group_edges": len(snapshot.cross_layer_group_edges),
            "cross_layer_group_edges_total": snapshot.cross_layer_group_edges_total,
            "violations": len(snapshot.violations),
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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

    current_markdown = (
        args.md_output.read_text(encoding="utf-8") if args.md_output.exists() else ""
    )
    frontmatter, _ = _split_frontmatter(current_markdown)
    markdown_to_write = f"{frontmatter}{markdown}" if frontmatter else markdown
    _write_text(args.md_output, markdown_to_write)
    _write_text(args.json_output, json_text)
    print(
        "[updated] wrote architecture dependency docs:\n"
        f"  - {args.md_output.relative_to(PROJECT_ROOT)}\n"
        f"  - {args.json_output.relative_to(PROJECT_ROOT)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
