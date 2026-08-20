#!/usr/bin/env python3
"""Generate Markdown bundles for diagram collections.

Produces class-diagrams-quality descriptions by parsing mermaid metadata:
- Title and focus from comments
- Node/edge counts
- Key subgraph names
- Key node labels
- Diagram type and level
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT, bundle_markdown_path
except ImportError:  # pragma: no cover - direct script execution
    REPO_ROOT = Path(__file__).resolve().parents[3]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT, bundle_markdown_path


MMD_BASE = DIAGRAM_ROOT

# Collection definitions: (dir_name, file_ext, output_name, collection_title)
COLLECTIONS = [
    ("foundation", ".mmd", "foundation.bundle", "BioETL Foundation Diagrams Bundle"),
    (
        "architecture",
        ".mmd",
        "architecture.bundle",
        "BioETL Architecture Diagrams Bundle",
    ),
    ("views", ".mermaid", "views.bundle", "BioETL Views Diagrams Bundle"),
    ("class-diagrams", ".mmd", "class.bundle", "BioETL Class Diagrams Bundle"),
]
COLLECTION_KEYS = tuple(dir_name for dir_name, _, _, _ in COLLECTIONS)

# ── Diagram type labels for Russian descriptions ──
TYPE_LABELS = {
    "flowchart": "блок-схема потоков (flowchart)",
    "sequencediagram": "диаграмма последовательности (sequence)",
    "classdiagram": "диаграмма классов (class diagram)",
    "statediagram": "диаграмма состояний (state diagram)",
    "statediagram-v2": "диаграмма состояний (state diagram v2)",
    "erdiagram": "ER-диаграмма",
    "mindmap": "интеллект-карта (mindmap)",
    "graph": "блок-схема (graph)",
}

# ── Collection-specific phrasing ──
COLLECTION_PHRASES = {
    "foundation": (
        "из foundation-набора фиксирует устойчивый архитектурный "
        "или процессный паттерн проекта BioETL"
    ),
    "architecture": (
        "из architecture-набора детализирует конкретный "
        "архитектурный компонент или подсистему BioETL"
    ),
    "views": (
        "из views-набора представляет фокусированный срез "
        "родительской диаграммы для точечного анализа"
    ),
    "class-diagrams": (
        "показывает архитектурную модель модуля и фиксирует контракты, "
        "роли и отношения между сущностями слоя"
    ),
}
VIEW_SUFFIX_ORDER = ("-full", "-overview", "-dataflow", "-domain", "-infra")
COMMENT_METADATA_PATTERNS = (
    (re.compile(r"Title:\s*([^\n]+)"), "title"),
    (re.compile(r"Covers:\s*([^\n]+)"), "covers"),
    (re.compile(r"Components:\s*([^\n]+)"), "components"),
    (re.compile(r"@type\s+([^\n]+)"), "type"),
    (re.compile(r"@date\s+([^\n]+)"), "date"),
    (re.compile(r"@level\s+([^\n]+)"), "level"),
    (re.compile(r"@nodes\s+([^\n]+)"), "nodes_meta"),
    (re.compile(r"@reference\s+([^\n]+)"), "reference"),
    (re.compile(r"@adr\s+([^\n]+)"), "adr"),
    (re.compile(r"Parent source:\s*([^\n]+)"), "parent_source"),
)
SHOWS_PATTERN = re.compile(r"Shows\s+([^\n]+)")


def _extract_comment_metadata(lines: list[str], meta: dict[str, object]) -> None:
    """Populate metadata from Mermaid comment headers."""
    for line in lines:
        stripped_line = line.strip()
        if not stripped_line.startswith("%%"):
            if stripped_line and not stripped_line.startswith("%%{"):
                break
            continue

        stripped = stripped_line.lstrip("% ").strip()
        if _apply_comment_metadata_pattern(stripped, meta):
            continue
        _apply_comment_fallbacks(stripped, meta)


def _apply_comment_metadata_pattern(stripped: str, meta: dict[str, object]) -> bool:
    for pattern, key in COMMENT_METADATA_PATTERNS:
        match = pattern.match(stripped)
        if not match:
            continue
        meta[key] = match.group(1).strip()
        return True

    if parsed_view := _parse_view_comment(stripped):
        meta["view_type"] = parsed_view[0]
        if parsed_view[1]:
            meta["parent"] = parsed_view[1]
        return True

    if "covers" not in meta and (match := SHOWS_PATTERN.match(stripped)):
        meta["covers"] = match.group(1).strip()
        return True
    return False


def _apply_comment_fallbacks(stripped: str, meta: dict[str, object]) -> None:
    if stripped.startswith("@"):
        return
    if "title" not in meta and "—" in stripped:
        meta["title"] = stripped.split("—", 1)[1].strip()
    elif "covers" not in meta and len(stripped) > 10:
        meta["covers"] = stripped


def _parse_view_comment(line: str) -> tuple[str, str | None] | None:
    if not line.startswith("View:"):
        return None

    payload = line.partition(":")[2].strip()
    if not payload:
        return None

    view_type, separator, remainder = payload.partition("|")
    parsed_view = view_type.strip()
    if not parsed_view:
        return None
    if not separator:
        return parsed_view, None

    candidate_parent = remainder.strip()
    if not candidate_parent.startswith("Parent:"):
        return parsed_view, None

    parent = candidate_parent.partition(":")[2].strip()
    return parsed_view, parent or None


def _detect_diagram_type(lines: list[str], meta: dict[str, object]) -> None:
    """Infer Mermaid diagram type from content when metadata is absent."""
    if "type" in meta:
        return

    prefixes = (
        "flowchart",
        "sequencediagram",
        "classdiagram",
        "statediagram-v2",
        "statediagram",
        "erdiagram",
        "mindmap",
        "graph",
    )
    for line in lines[:30]:
        lowered = line.strip().lower()
        matched_prefix = next(
            (prefix for prefix in prefixes if lowered.startswith(prefix)),
            None,
        )
        if matched_prefix:
            meta["type"] = matched_prefix
            return


def _collect_class_node_names(lines: list[str]) -> list[str]:
    """Extract class names from class diagrams."""
    class_pattern = re.compile(r"^\s+class\s+(\w+)\s*[\{:]?")
    node_names: list[str] = []
    for line in lines:
        match = class_pattern.match(line)
        if not match:
            continue
        name = match.group(1)
        if name and len(name) < 80:
            node_names.append(name)
    return node_names


def _collect_flow_node_names(lines: list[str]) -> list[str]:
    """Extract readable node labels from flowchart-like diagrams."""
    node_pattern = re.compile(
        r'^\s+(\w+)\["([^"]+)"\]'  # N1["Label"]
        r'|^\s+(\w+)\["([^"]+)"'  # N1["Label"
        r"|^\s+(\w+)\[([^\]]+)\]"  # N1[Label]
    )
    node_names: list[str] = []
    for line in lines:
        match = node_pattern.match(line)
        if not match:
            continue
        label = match.group(2) or match.group(4) or match.group(6) or ""
        label = re.sub(r"<br\s*/?>", " ", label)
        label = re.sub(r"<[^>]+>", "", label).strip()
        if label and len(label) < 80:
            node_names.append(label)
    return node_names


def _count_edges(lines: list[str], is_class_diagram: bool) -> int:
    """Count Mermaid relationships for class and flow diagrams."""
    if is_class_diagram:
        class_edge_pattern = re.compile(
            r"<\|--|--\*|--o|-->|<--|\.\.>|\.\.\|>|\*--(?!>)|o--(?!>)"
        )
        return sum(len(class_edge_pattern.findall(line)) for line in lines)

    edge_pattern = re.compile(r"(?:==>|-.->|--[>o]|<--|~~~)")
    return sum(len(edge_pattern.findall(line)) for line in lines)


def _collect_subgraph_names(lines: list[str]) -> list[str]:
    """Extract Mermaid subgraph and namespace labels."""
    subgraph_names: list[str] = []
    for line in lines:
        name = _extract_subgraph_name(line)
        if name and name != "direction":
            subgraph_names.append(name)
        namespace_name = _extract_namespace_name(line)
        if namespace_name:
            subgraph_names.append(namespace_name)
    return subgraph_names


def _extract_subgraph_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("subgraph "):
        return None

    payload = stripped[len("subgraph ") :].strip()
    if not payload:
        return None

    if payload.endswith('"]') and '["' in payload:
        _, _, label = payload.partition('["')
        return label[:-2].strip() or None

    name = payload.split(maxsplit=1)[0]
    return name or None


def _extract_namespace_name(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("namespace "):
        return None

    payload = stripped[len("namespace ") :].strip()
    if not payload:
        return None

    name = payload.rstrip("{").strip().split(maxsplit=1)[0]
    if not name.isidentifier():
        return None
    return name.replace("_", " ")


def parse_mermaid(path: Path) -> dict[str, object]:
    """Parse a mermaid file and extract rich metadata."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    meta: dict[str, object] = {
        "stem": path.stem,
        "filename": path.name,
    }

    _extract_comment_metadata(lines, meta)
    _detect_diagram_type(lines, meta)

    is_class_diagram = str(meta.get("type", "")).lower() == "classdiagram"
    node_names = (
        _collect_class_node_names(lines)
        if is_class_diagram
        else _collect_flow_node_names(lines)
    )
    edge_count = _count_edges(lines, is_class_diagram)
    subgraph_names = _collect_subgraph_names(lines)

    meta["node_count"] = len(node_names)
    meta["node_names"] = node_names
    meta["edge_count"] = edge_count
    meta["subgraph_names"] = subgraph_names

    return meta


def format_title(meta: dict[str, object]) -> str:
    """Get human-readable title."""
    if "title" in meta:
        return str(meta["title"])
    stem = str(meta["stem"])
    # Strip view suffixes
    for suffix in ("-overview", "-domain", "-infra", "-dataflow", "-full"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem.replace("-", " ").title()


def _append_description_context(
    parts: list[str],
    *,
    level: str,
    view_type: str,
    parent: str,
    covers: str,
    components: str,
) -> None:
    if level:
        parts.append(f" и служит ориентиром на уровне детализации «{level}»")
    parts.append(".")
    if view_type:
        parts.append(f" Тип представления: {view_type}.")
    if parent:
        parts.append(f" Родительская диаграмма: `{parent}`.")
    if covers:
        parts.append(
            f" В комментариях исходника зафиксирован фокус диаграммы: {covers}."
        )
    elif components:
        parts.append(f" Основные компоненты: {components}.")


def _append_description_density(
    parts: list[str], *, display_nodes: str, edge_count: int
) -> None:
    if display_nodes == "0":
        return
    density_parts = [f"Схема имеет плотность порядка {display_nodes} узлов"]
    if edge_count > 0:
        density_parts.append(f" и {edge_count} связей")
    density_parts.append(
        "; её удобно использовать как обзорный архитектурный срез для "
        "проверки влияния изменений, согласования интерфейсов и подготовки "
        "рефакторинга, но не как исчерпывающий каталог текущей кодовой "
        "поверхности."
    )
    parts.append(" " + "".join(density_parts))


def _append_description_examples(
    parts: list[str], *, subgraph_names: list[str], node_names: list[str]
) -> None:
    if subgraph_names:
        parts.append(f" Ключевые блоки/подграфы: {', '.join(subgraph_names[:6])}.")
    if node_names:
        parts.append(
            " Показательные узлы для быстрого чтения: "
            f"{', '.join(node_names[:6])}."
        )


def build_description(meta: dict[str, object], collection: str) -> str:
    """Build a rich description matching class-diagrams quality."""
    title = format_title(meta)
    diagram_type = str(meta.get("type", "flowchart"))
    type_label = TYPE_LABELS.get(diagram_type.lower(), diagram_type)
    level = str(meta.get("level", ""))
    covers = str(meta.get("covers", ""))
    components = str(meta.get("components", ""))
    reference = str(meta.get("reference", ""))
    view_type = str(meta.get("view_type", ""))
    parent = str(meta.get("parent", ""))
    adr = str(meta.get("adr", ""))
    node_count_value = meta.get("node_count", 0)
    edge_count_value = meta.get("edge_count", 0)
    node_names_value = meta.get("node_names", [])
    subgraph_names_value = meta.get("subgraph_names", [])
    node_count = node_count_value if isinstance(node_count_value, int) else 0
    edge_count = edge_count_value if isinstance(edge_count_value, int) else 0
    node_names = (
        [item for item in node_names_value if isinstance(item, str)]
        if isinstance(node_names_value, list)
        else []
    )
    subgraph_names = (
        [item for item in subgraph_names_value if isinstance(item, str)]
        if isinstance(subgraph_names_value, list)
        else []
    )
    nodes_meta = str(meta.get("nodes_meta", ""))

    # Use @nodes from metadata if available, otherwise counted
    display_nodes = (
        nodes_meta if nodes_meta and nodes_meta != "n/a" else str(node_count)
    )

    phrase = COLLECTION_PHRASES.get(collection, "фиксирует паттерн проекта BioETL")

    parts: list[str] = []

    # Opening sentence
    parts.append(
        f"Диаграмма «{title}» {phrase}. Она представлена в формате {type_label}"
    )
    _append_description_context(
        parts,
        level=level,
        view_type=view_type,
        parent=parent,
        covers=covers,
        components=components,
    )
    _append_description_density(
        parts, display_nodes=display_nodes, edge_count=edge_count
    )
    _append_description_examples(
        parts, subgraph_names=subgraph_names, node_names=node_names
    )

    # Reference / decomposition note
    if reference:
        parts.append(f" Примечание: {reference}.")

    # ADR reference
    if adr:
        parts.append(f" Связанный ADR: {adr}.")

    return "".join(parts)


def _view_family_key(stem: str) -> str:
    for suffix in VIEW_SUFFIX_ORDER:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def _preferred_view_anchor(
    entries: list[tuple[Path, dict[str, object]]],
) -> tuple[Path, dict[str, object]]:
    for suffix in VIEW_SUFFIX_ORDER:
        for entry in entries:
            if entry[0].stem.endswith(suffix):
                return entry
    return entries[0]


def _view_variant_label(meta: dict[str, object], stem: str) -> str:
    view_type = str(meta.get("view_type", "")).strip()
    if view_type:
        return view_type.lower()
    for suffix in VIEW_SUFFIX_ORDER:
        if stem.endswith(suffix):
            return suffix.removeprefix("-")
    return "variant"


def build_toc_lines(
    parsed_diagrams: list[tuple[Path, dict[str, object]]],
    collection_key: str,
) -> list[str]:
    lines = ["## Table of Contents\n"]

    if collection_key != "views":
        for diagram_path, meta in parsed_diagrams:
            title = format_title(meta)
            lines.append(f"- [{diagram_path.stem} — {title}](#{diagram_path.stem})")
        lines.append("")
        return lines

    grouped: dict[str, list[tuple[Path, dict[str, object]]]] = {}
    for diagram_path, meta in parsed_diagrams:
        family_key = _view_family_key(diagram_path.stem)
        grouped.setdefault(family_key, []).append((diagram_path, meta))

    for family_key, entries in grouped.items():
        if len(entries) == 1:
            diagram_path, meta = entries[0]
            title = format_title(meta)
            lines.append(f"- [{diagram_path.stem} — {title}](#{diagram_path.stem})")
            continue

        anchor_path, anchor_meta = _preferred_view_anchor(entries)
        title = format_title(anchor_meta)
        variants = ", ".join(
            _view_variant_label(meta, diagram_path.stem)
            for diagram_path, meta in entries
        )
        lines.append(
            f"- [{family_key} — {title}](#{anchor_path.stem})"
            f" — {len(entries)} views: {variants}"
        )

    lines.append("")
    return lines


def resolve_bundle_image_markdown(
    collection_dir: Path, stem: str, output_md: Path
) -> str:
    svg_file = collection_dir / "svg" / f"{stem}.svg"
    png_file = collection_dir / "png" / f"{stem}.png"
    svg_rel = Path(os.path.relpath(svg_file, output_md.parent)).as_posix()
    png_rel = Path(os.path.relpath(png_file, output_md.parent)).as_posix()

    if svg_file.exists():
        return f"![{stem}]({svg_rel})\n"
    if png_file.exists():
        return f"![{stem}]({png_rel})\n"
    return f"*SVG/PNG не найдены: `{svg_rel}`, `{png_rel}`*\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Markdown bundles for diagram collections."
    )
    parser.add_argument(
        "--collection",
        action="append",
        choices=COLLECTION_KEYS,
        help=(
            "Only generate the selected collection. May be passed multiple times. "
            "Defaults to all collections."
        ),
    )
    return parser.parse_args(argv)


def _bundle_header_lines(bundle_title: str, diagram_count: int) -> list[str]:
    return [
        f"# {bundle_title}\n",
        f"- Generated: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        f"- Diagram count: {diagram_count}\n",
    ]


def _append_page_break(lines: list[str]) -> None:
    lines.append("\\newpage")
    lines.append("")
    lines.append('<div style="page-break-before: always;"></div>')
    lines.append("")


def _build_metadata_block(meta: dict[str, object]) -> list[str]:
    meta_items: list[str] = []
    if "type" in meta:
        meta_items.append(f"- Тип: `{meta['type']}`")
    if "level" in meta:
        meta_items.append(f"- Уровень: `{meta['level']}`")
    if "date" in meta:
        meta_items.append(f"- Дата: `{meta['date']}`")
    if "view_type" in meta:
        meta_items.append(f"- Представление: `{meta['view_type']}`")
    nodes_meta = meta.get("nodes_meta", "")
    if nodes_meta:
        meta_items.append(f"- Узлы (metadata): `{nodes_meta}`")
    if meta.get("adr"):
        meta_items.append(f"- ADR: `{meta['adr']}`")
    if not meta_items:
        return []
    return ["### Метаданные", *meta_items, ""]


def _build_diagram_entry_lines(
    diagram_path: Path,
    meta: dict[str, object],
    collection_dir: Path,
    output_md: Path,
    collection_key: str,
    *,
    include_page_break: bool,
) -> list[str]:
    stem = diagram_path.stem
    title = format_title(meta)
    lines: list[str] = []
    if include_page_break:
        _append_page_break(lines)

    lines.append(f"## {stem}\n")
    lines.append(f"**{title}**\n")
    lines.append(resolve_bundle_image_markdown(collection_dir, stem, output_md))
    lines.append("### Описание")
    lines.append(build_description(meta, collection_key))
    lines.append("")
    lines.extend(_build_metadata_block(meta))
    return lines


def generate_bundle(
    collection_dir: Path,
    file_ext: str,
    output_name: str,
    bundle_title: str,
    collection_key: str,
) -> int:
    """Generate a single diagram bundle."""
    diagram_files = sorted(collection_dir.glob(f"*{file_ext}"))
    if not diagram_files:
        print(f"[ERROR] No {file_ext} files in {collection_dir.name}/")
        return 0

    output_md = bundle_markdown_path(collection_key)
    parsed_diagrams = [
        (diagram_path, parse_mermaid(diagram_path)) for diagram_path in diagram_files
    ]

    lines = _bundle_header_lines(bundle_title, len(diagram_files))
    lines.extend(build_toc_lines(parsed_diagrams, collection_key))
    _append_page_break(lines)

    first = True
    for diagram_path, meta in parsed_diagrams:
        lines.extend(
            _build_diagram_entry_lines(
                diagram_path,
                meta,
                collection_dir,
                output_md,
                collection_key,
                include_page_break=not first,
            )
        )
        first = False

    output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] {output_name}.md: {len(diagram_files)} diagrams")
    return len(diagram_files)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    selected = set(args.collection or COLLECTION_KEYS)
    total = 0
    for dir_name, ext, output_name, title in COLLECTIONS:
        if dir_name not in selected:
            continue
        collection_dir = MMD_BASE / dir_name
        if not collection_dir.exists():
            print(f"[SKIP] {dir_name}/ not found")
            continue
        total += generate_bundle(collection_dir, ext, output_name, title, dir_name)

    print(f"[INFO] Total diagrams processed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
