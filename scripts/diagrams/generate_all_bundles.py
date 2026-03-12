#!/usr/bin/env python3
"""Generate *-with-descriptions.md bundles for all diagram collections.

Produces class-diagrams-quality descriptions by parsing mermaid metadata:
- Title and focus from comments
- Node/edge counts
- Key subgraph names
- Key node labels
- Diagram type and level
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


def _resolve_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[0]


REPO_ROOT = _resolve_repo_root()
MMD_BASE = REPO_ROOT / "docs" / "02-architecture" / "mmd-diagrams"

# Collection definitions: (dir_name, file_ext, output_name, collection_title)
COLLECTIONS = [
    ("foundation", ".mmd", "foundation-diagrams-with-descriptions", "BioETL Foundation Diagrams With Descriptions"),
    ("architecture", ".mmd", "architecture-diagrams-with-descriptions", "BioETL Architecture Diagrams With Descriptions"),
    ("views", ".mermaid", "views-diagrams-with-descriptions", "BioETL Views Diagrams With Descriptions"),
]

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
}


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
        # First non-@, non-keyword line as fallback title
        if "title" not in meta and not stripped.startswith("@"):
            # "BioETL — Something" pattern
            if "—" in stripped:
                meta["title"] = stripped.split("—", 1)[1].strip()

    # ── Detect diagram type from content ──
    if "type" not in meta:
        for line in lines[:30]:
            ls = line.strip().lower()
            for prefix in ("flowchart", "sequencediagram", "classdiagram",
                           "statediagram-v2", "statediagram", "erdiagram",
                           "mindmap", "graph"):
                if ls.startswith(prefix):
                    meta["type"] = prefix
                    break
            if "type" in meta:
                break

    # ── Count nodes (named elements) ──
    node_names: list[str] = []
    node_pattern = re.compile(
        r'^\s+(\w+)\["([^"]+)"\]'  # N1["Label"]
        r'|^\s+(\w+)\["([^"]+)"'   # N1["Label"
        r'|^\s+(\w+)\[([^\]]+)\]'  # N1[Label]
    )
    for line in lines:
        m = node_pattern.match(line)
        if m:
            # Get the label (second capture group that matched)
            label = m.group(2) or m.group(4) or m.group(6) or ""
            # Clean HTML tags
            label = re.sub(r"<br\s*/?>", " ", label)
            label = re.sub(r"<[^>]+>", "", label).strip()
            if label and len(label) < 80:
                node_names.append(label)

    # ── Count edges ──
    edge_pattern = re.compile(r"-->|==>|-.->|--[>o]|<--|~~~")
    edge_count = sum(len(edge_pattern.findall(line)) for line in lines)

    # ── Extract subgraph names ──
    subgraph_names: list[str] = []
    subgraph_pattern = re.compile(r'subgraph\s+\w+\["([^"]+)"\]|subgraph\s+(\w+)\s*$')
    for line in lines:
        m = subgraph_pattern.search(line)
        if m:
            name = m.group(1) or m.group(2) or ""
            if name and name != "direction":
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
    display_nodes = nodes_meta if nodes_meta and nodes_meta != "n/a" else str(node_count)

    phrase = COLLECTION_PHRASES.get(collection, "фиксирует паттерн проекта BioETL")

    parts: list[str] = []

    # Opening sentence
    parts.append(
        f"Диаграмма «{title}» {phrase}. "
        f"Она представлена в формате {type_label}"
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
        density_parts = [f"На схеме отражено примерно {display_nodes} узлов"]
        if edge_count > 0:
            density_parts.append(f" и {edge_count} связей")
        density_parts.append(
            ", поэтому её удобно использовать для проверки влияния изменений, "
            "согласования интерфейсов и подготовки рефакторинга."
        )
        parts.append(" " + "".join(density_parts))

    # Key subgraphs
    if subgraph_names:
        display_subgraphs = subgraph_names[:6]
        parts.append(
            f" Ключевые блоки/подграфы: {', '.join(display_subgraphs)}."
        )

    # Key nodes
    if node_names:
        display_nodes_list = node_names[:6]
        parts.append(
            f" Показательные узлы для быстрого чтения: "
            f"{', '.join(display_nodes_list)}."
        )

    # Reference / decomposition note
    if reference:
        parts.append(f" Примечание: {reference}.")

    # ADR reference
    if adr:
        parts.append(f" Связанный ADR: {adr}.")

    return "".join(parts)


def generate_bundle(
    collection_dir: Path,
    file_ext: str,
    output_name: str,
    bundle_title: str,
    collection_key: str,
) -> int:
    """Generate a single *-with-descriptions.md bundle."""
    diagram_files = sorted(collection_dir.glob(f"*{file_ext}"))
    if not diagram_files:
        print(f"[ERROR] No {file_ext} files in {collection_dir.name}/")
        return 0

    png_dir = collection_dir / "png"
    rel_prefix = collection_dir.name  # e.g. "foundation", "architecture", "views"
    output_md = MMD_BASE / f"{output_name}.md"

    lines: list[str] = []
    lines.append(f"# {bundle_title}\n")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append(f"- Diagram count: {len(diagram_files)}\n")

    # ── Table of Contents ──
    lines.append("## Table of Contents\n")
    for df in diagram_files:
        meta = parse_mermaid(df)
        title = format_title(meta)
        lines.append(f"- [{df.stem} — {title}](#{df.stem})")
    lines.append("")

    # ── Page break after TOC ──
    lines.append("\\newpage")
    lines.append("")
    lines.append('<div style="page-break-before: always;"></div>')
    lines.append("")

    # ── Diagram entries ──
    first = True
    for df in diagram_files:
        meta = parse_mermaid(df)
        stem = df.stem
        title = format_title(meta)
        png_file = png_dir / f"{stem}.png"

        # Page break between diagrams
        if not first:
            lines.append("\\newpage")
            lines.append("")
            lines.append('<div style="page-break-before: always;"></div>')
            lines.append("")
        first = False

        lines.append(f"## {stem} — {title}\n")

        if png_file.exists():
            lines.append(f"![{stem}]({rel_prefix}/png/{stem}.png)\n")
        else:
            lines.append(f"*PNG не найден: `{rel_prefix}/png/{stem}.png`*\n")

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


def main() -> int:
    total = 0
    for dir_name, ext, output_name, title in COLLECTIONS:
        collection_dir = MMD_BASE / dir_name
        if not collection_dir.exists():
            print(f"[SKIP] {dir_name}/ not found")
            continue
        total += generate_bundle(collection_dir, ext, output_name, title, dir_name)

    print(f"[INFO] Total diagrams processed: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
