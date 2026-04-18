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
from datetime import datetime
from pathlib import Path

try:
    from .diagram_paths import DIAGRAM_ROOT, bundle_markdown_path
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import DIAGRAM_ROOT, bundle_markdown_path


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


def parse_mermaid(path: Path) -> dict[str, object]:
    """Parse a mermaid file and extract rich metadata."""
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    meta: dict[str, object] = {
        "stem": path.stem,
        "filename": path.name,
    }

    # ── Extract comment metadata ──
    for line in lines:
        s = line.strip()
        if not s.startswith("%%"):
            if s and not s.startswith("%%"):
                # Stop at first non-comment, non-blank line (except init blocks)
                if not s.startswith("%%{"):
                    break
            continue
        stripped = s.lstrip("% ").strip()

        if m := re.match(r"Title:\s*(.+)", stripped):
            meta["title"] = m.group(1).strip()
        elif m := re.match(r"Covers:\s*(.+)", stripped):
            meta["covers"] = m.group(1).strip()
        elif m := re.match(r"Components:\s*(.+)", stripped):
            meta["components"] = m.group(1).strip()
        elif m := re.match(r"@type\s+(.+)", stripped):
            meta["type"] = m.group(1).strip()
        elif m := re.match(r"@date\s+(.+)", stripped):
            meta["date"] = m.group(1).strip()
        elif m := re.match(r"@level\s+(.+)", stripped):
            meta["level"] = m.group(1).strip()
        elif m := re.match(r"@nodes\s+(.+)", stripped):
            meta["nodes_meta"] = m.group(1).strip()
        elif m := re.match(r"@reference\s+(.+)", stripped):
            meta["reference"] = m.group(1).strip()
        elif m := re.match(r"@adr\s+(.+)", stripped):
            meta["adr"] = m.group(1).strip()
        elif m := re.match(r"View:\s*(.+?)(?:\s*\|\s*Parent:\s*(.+))?$", stripped):
            meta["view_type"] = m.group(1).strip()
            if m.group(2):
                meta["parent"] = m.group(2).strip()
        elif m := re.match(r"Parent source:\s*(.+)", stripped):
            meta["parent_source"] = m.group(1).strip()
        elif m := re.match(r"Shows\s+(.+)", stripped):
            if "covers" not in meta:
                meta["covers"] = m.group(1).strip()
        # First non-@, non-keyword line as fallback title / covers
        if not stripped.startswith("@"):
            if "title" not in meta:
                # "BioETL — Something" pattern
                if "—" in stripped:
                    meta["title"] = stripped.split("—", 1)[1].strip()
            elif "covers" not in meta and len(stripped) > 10:
                # Second comment line as fallback covers (e.g. class-diagrams)
                meta["covers"] = stripped

    # ── Detect diagram type from content ──
    if "type" not in meta:
        for line in lines[:30]:
            ls = line.strip().lower()
            for prefix in (
                "flowchart",
                "sequencediagram",
                "classdiagram",
                "statediagram-v2",
                "statediagram",
                "erdiagram",
                "mindmap",
                "graph",
            ):
                if ls.startswith(prefix):
                    meta["type"] = prefix
                    break
            if "type" in meta:
                break

    # ── Count nodes (named elements) ──
    node_names: list[str] = []
    is_class_diagram = str(meta.get("type", "")).lower() == "classdiagram"

    if is_class_diagram:
        # classDiagram: class ClassName { ... }
        class_pattern = re.compile(r"^\s+class\s+(\w+)\s*[\{:]?")
        for line in lines:
            m = class_pattern.match(line)
            if m:
                name = m.group(1)
                if name and len(name) < 80:
                    node_names.append(name)
    else:
        # flowchart / graph / other: N1["Label"] or N1[Label]
        node_pattern = re.compile(
            r'^\s+(\w+)\["([^"]+)"\]'  # N1["Label"]
            r'|^\s+(\w+)\["([^"]+)"'  # N1["Label"
            r"|^\s+(\w+)\[([^\]]+)\]"  # N1[Label]
        )
        for line in lines:
            m = node_pattern.match(line)
            if m:
                label = m.group(2) or m.group(4) or m.group(6) or ""
                label = re.sub(r"<br\s*/?>", " ", label)
                label = re.sub(r"<[^>]+>", "", label).strip()
                if label and len(label) < 80:
                    node_names.append(label)

    # ── Count edges ──
    if is_class_diagram:
        # classDiagram edges: <|--, *--, o--, -->, ..|>, ..>
        class_edge_pattern = re.compile(
            r"<\|--|--\*|--o|-->|<--|\.\.>|\.\.\|>|\*--(?!>)|o--(?!>)"
        )
        edge_count = sum(len(class_edge_pattern.findall(line)) for line in lines)
    else:
        edge_pattern = re.compile(r"(?:-->|==>|-.->|--(?:>|o)|<--|~~~)")
        edge_count = sum(len(edge_pattern.findall(line)) for line in lines)

    # ── Extract subgraph / namespace names ──
    subgraph_names: list[str] = []
    subgraph_pattern = re.compile(
        r'(?:subgraph\s+\w+\["([^"]+)"\]|subgraph\s+(\w+)\s*$)'
    )
    namespace_pattern = re.compile(r"^\s+namespace\s+(\w+)\s*\{?\s*$")
    for line in lines:
        m = subgraph_pattern.search(line)
        if m:
            name = m.group(1) or m.group(2) or ""
            if name and name != "direction":
                subgraph_names.append(name)
        m2 = namespace_pattern.match(line)
        if m2:
            name = m2.group(1).replace("_", " ")
            subgraph_names.append(name)

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


def build_description(meta: dict[str, object], collection: str) -> str:
    """Build a rich description matching class-diagrams quality."""
    title = format_title(meta)
    stem = str(meta["stem"])
    diagram_type = str(meta.get("type", "flowchart"))
    type_label = TYPE_LABELS.get(diagram_type.lower(), diagram_type)
    level = str(meta.get("level", ""))
    covers = str(meta.get("covers", ""))
    components = str(meta.get("components", ""))
    reference = str(meta.get("reference", ""))
    view_type = str(meta.get("view_type", ""))
    parent = str(meta.get("parent", ""))
    adr = str(meta.get("adr", ""))
    node_count = int(meta.get("node_count", 0))  # type: ignore[arg-type]
    edge_count = int(meta.get("edge_count", 0))  # type: ignore[arg-type]
    node_names: list[str] = meta.get("node_names", [])  # type: ignore[assignment]
    subgraph_names: list[str] = meta.get("subgraph_names", [])  # type: ignore[assignment]
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
    if level:
        parts.append(f" и служит ориентиром на уровне детализации «{level}»")
    parts.append(".")

    # View-specific context
    if view_type:
        parts.append(f" Тип представления: {view_type}.")
    if parent:
        parts.append(f" Родительская диаграмма: `{parent}`.")

    # Focus
    if covers:
        parts.append(
            f" В комментариях исходника зафиксирован фокус диаграммы: {covers}."
        )
    elif components:
        parts.append(f" Основные компоненты: {components}.")

    # Density
    if display_nodes != "0":
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

    # Key subgraphs
    if subgraph_names:
        display_subgraphs = subgraph_names[:6]
        parts.append(f" Ключевые блоки/подграфы: {', '.join(display_subgraphs)}.")

    # Key nodes
    if node_names:
        display_nodes_list = node_names[:6]
        parts.append(
            f" Показательные узлы для быстрого чтения: {', '.join(display_nodes_list)}."
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

    lines: list[str] = []
    lines.append(f"# {bundle_title}\n")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append(f"- Diagram count: {len(diagram_files)}\n")

    # ── Table of Contents ──
    lines.extend(build_toc_lines(parsed_diagrams, collection_key))

    # ── Page break after TOC ──
    lines.append("\\newpage")
    lines.append("")
    lines.append('<div style="page-break-before: always;"></div>')
    lines.append("")

    # ── Diagram entries ──
    first = True
    for df, meta in parsed_diagrams:
        stem = df.stem
        title = format_title(meta)
        # Page break between diagrams
        if not first:
            lines.append("\\newpage")
            lines.append("")
            lines.append('<div style="page-break-before: always;"></div>')
            lines.append("")
        first = False

        # Use Markdown heading IDs so MkDocs can validate self-links in bundle TOCs.
        lines.append(f"## {stem}\n")
        lines.append(f"**{title}**\n")
        lines.append(resolve_bundle_image_markdown(collection_dir, stem, output_md))

        lines.append("### Описание")
        lines.append(build_description(meta, collection_key))
        lines.append("")

        # ── Metadata block ──
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
        if meta_items:
            lines.append("### Метаданные")
            lines.extend(meta_items)
            lines.append("")

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
