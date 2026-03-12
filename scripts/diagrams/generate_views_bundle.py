#!/usr/bin/env python3
"""Generate views-diagrams-with-descriptions.md bundle from views/ mermaid files."""

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
VIEWS_DIR = REPO_ROOT / "docs" / "02-architecture" / "mmd-diagrams" / "views"
PNG_DIR = VIEWS_DIR / "png"
OUTPUT_MD = REPO_ROOT / "docs" / "02-architecture" / "mmd-diagrams" / "views-diagrams-with-descriptions.md"


def extract_metadata(mermaid_path: Path) -> dict[str, str]:
    """Extract metadata from mermaid file comments."""
    meta: dict[str, str] = {}
    text = mermaid_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("%%"):
            if line.strip() and not line.startswith("%%"):
                break
            continue
        stripped = line.lstrip("% ").strip()
        if m := re.match(r"View:\s*(.+?)(?:\s*\|\s*Parent:\s*(.+))?$", stripped):
            meta["view"] = m.group(1).strip()
            if m.group(2):
                meta["parent"] = m.group(2).strip()
        elif m := re.match(r"Title:\s*(.+)", stripped):
            meta["title"] = m.group(1).strip()
        elif m := re.match(r"@type\s+(.+)", stripped):
            meta["type"] = m.group(1).strip()
        elif m := re.match(r"@date\s+(.+)", stripped):
            meta["date"] = m.group(1).strip()
        elif m := re.match(r"@level\s+(.+)", stripped):
            meta["level"] = m.group(1).strip()
        elif m := re.match(r"@nodes\s+(.+)", stripped):
            meta["nodes"] = m.group(1).strip()
        elif m := re.match(r"Covers:\s*(.+)", stripped):
            meta["covers"] = m.group(1).strip()
    # Detect diagram type from content
    if "type" not in meta:
        for line in text.splitlines()[:20]:
            line_stripped = line.strip().lower()
            if line_stripped.startswith("flowchart"):
                meta["type"] = "flowchart"
                break
            elif line_stripped.startswith("sequencediagram"):
                meta["type"] = "sequenceDiagram"
                break
            elif line_stripped.startswith("classdiagram"):
                meta["type"] = "classDiagram"
                break
            elif line_stripped.startswith("statediagram"):
                meta["type"] = "stateDiagram"
                break
            elif line_stripped.startswith("erdiagram"):
                meta["type"] = "erDiagram"
                break
    return meta


def build_description(stem: str, meta: dict[str, str]) -> str:
    """Build description text for a view diagram."""
    view_type = meta.get("view", "Unknown")
    title = meta.get("title", stem.replace("-", " ").title())
    diagram_type = meta.get("type", "unknown")
    parent = meta.get("parent", "")
    covers = meta.get("covers", "")

    parts = [
        f"Views-диаграмма «{title}» (уровень: {view_type}) представлена "
        f"в формате {diagram_type}.",
    ]
    if parent:
        parts.append(f"Родительская диаграмма: `{parent}`.")
    if covers:
        parts.append(f"Покрывает: {covers}.")
    nodes = meta.get("nodes", "")
    if nodes:
        parts.append(f"Количество узлов: {nodes}.")
    return " ".join(parts)


def main() -> int:
    mermaid_files = sorted(VIEWS_DIR.glob("*.mermaid"))
    if not mermaid_files:
        print("[ERROR] No .mermaid files found in views/")
        return 1

    # Group by base diagram name (strip view suffix)
    lines: list[str] = []
    lines.append("# BioETL Views Diagrams With Descriptions\n")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append(f"- Diagram count: {len(mermaid_files)}\n")

    # TOC
    lines.append("## Table of Contents\n")
    for mf in mermaid_files:
        stem = mf.stem
        lines.append(f"- [{stem}](#{stem})")
    lines.append("\n---\n")
    lines.append("\\newpage")
    lines.append("")
    lines.append('<div style="page-break-before: always;"></div>')
    lines.append("")

    # Entries
    first = True
    for mf in mermaid_files:
        stem = mf.stem
        png_file = PNG_DIR / f"{stem}.png"
        meta = extract_metadata(mf)

        # Page break before each diagram section (except first)
        if not first:
            lines.append("\\newpage")
            lines.append("")
            lines.append('<div style="page-break-before: always;"></div>')
            lines.append("")
        first = False

        lines.append(f"## {stem}\n")
        if png_file.exists():
            lines.append(f"![{stem}](views/png/{stem}.png)\n")
        else:
            lines.append(f"*PNG не найден: `views/png/{stem}.png`*\n")

        lines.append(f"- Исходная диаграмма: `mmd-diagrams/views/{mf.name}`\n")

        lines.append("### Описание")
        lines.append(build_description(stem, meta))
        lines.append("")

        # Metadata section
        meta_lines = []
        if "type" in meta:
            meta_lines.append(f"- Тип: `{meta['type']}`")
        if "level" in meta:
            meta_lines.append(f"- Уровень: `{meta['level']}`")
        if "date" in meta:
            meta_lines.append(f"- Дата метаданных: `{meta['date']}`")
        if "view" in meta:
            meta_lines.append(f"- Вид: `{meta['view']}`")
        if meta_lines:
            lines.append("### Метаданные")
            lines.extend(meta_lines)
            lines.append("")

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Generated: {OUTPUT_MD}")
    print(f"[INFO] Diagrams included: {len(mermaid_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
