#!/usr/bin/env python3
"""Generate architecture-diagrams-with-descriptions.md bundle from architecture/ mmd files."""

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
ARCH_DIR = REPO_ROOT / "docs" / "02-architecture" / "mmd-diagrams" / "architecture"
PNG_DIR = ARCH_DIR / "png"
OUTPUT_MD = (
    REPO_ROOT
    / "docs"
    / "02-architecture"
    / "mmd-diagrams"
    / "architecture-diagrams-with-descriptions.md"
)


def extract_metadata(mmd_path: Path) -> dict[str, str]:
    """Extract metadata from mmd file comments."""
    meta: dict[str, str] = {}
    text = mmd_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("%%"):
            if line.strip():
                break
            continue
        stripped = line.lstrip("% ").strip()
        # First line often is the title comment
        if "title" not in meta and not stripped.startswith("@") and not stripped.startswith("Legend"):
            if "—" in stripped:
                meta["title"] = stripped.split("—", 1)[1].strip()
            elif ":" not in stripped and len(stripped) > 5:
                meta["title"] = stripped
        if m := re.match(r"@type\s+(.+)", stripped):
            meta["type"] = m.group(1).strip()
        elif m := re.match(r"@date\s+(.+)", stripped):
            meta["date"] = m.group(1).strip()
        elif m := re.match(r"@level\s+(.+)", stripped):
            meta["level"] = m.group(1).strip()
        elif m := re.match(r"@nodes\s+(.+)", stripped):
            meta["nodes"] = m.group(1).strip()
        elif m := re.match(r"@reference\s+(.+)", stripped):
            meta["reference"] = m.group(1).strip()
        elif m := re.match(r"Shows\s+(.+)", stripped):
            meta["covers"] = m.group(1).strip()
    # Detect diagram type from content
    if "type" not in meta:
        for line in text.splitlines()[:30]:
            ls = line.strip().lower()
            if ls.startswith("flowchart"):
                meta["type"] = "flowchart"
                break
            elif ls.startswith("sequencediagram"):
                meta["type"] = "sequenceDiagram"
                break
            elif ls.startswith("classdiagram"):
                meta["type"] = "classDiagram"
                break
            elif ls.startswith("statediagram"):
                meta["type"] = "stateDiagram"
                break
            elif ls.startswith("erdiagram"):
                meta["type"] = "erDiagram"
                break
    return meta


def build_description(stem: str, meta: dict[str, str]) -> str:
    """Build description text for an architecture diagram."""
    title = meta.get("title", stem.replace("-", " ").title())
    diagram_type = meta.get("type", "unknown")
    level = meta.get("level", "")
    covers = meta.get("covers", "")
    reference = meta.get("reference", "")
    nodes = meta.get("nodes", "")

    parts = [
        f"Архитектурная диаграмма «{title}» из набора architecture представлена "
        f"в формате {diagram_type}.",
    ]
    if level:
        parts.append(f"Уровень детализации: {level}.")
    if covers:
        parts.append(f"Показывает: {covers}.")
    if nodes:
        parts.append(f"Количество узлов: {nodes}.")
    if reference:
        parts.append(f"Примечание: {reference}.")
    return " ".join(parts)


def main() -> int:
    mmd_files = sorted(ARCH_DIR.glob("*.mmd"))
    if not mmd_files:
        print("[ERROR] No .mmd files found in architecture/")
        return 1

    lines: list[str] = []
    lines.append("# BioETL Architecture Diagrams With Descriptions\n")
    lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}")
    lines.append(f"- Diagram count: {len(mmd_files)}\n")

    # TOC
    lines.append("## Table of Contents\n")
    for mf in mmd_files:
        stem = mf.stem
        lines.append(f"- [{stem}](#{stem})")
    lines.append("\n---\n")

    # Entries
    for mf in mmd_files:
        stem = mf.stem
        png_file = PNG_DIR / f"{stem}.png"
        meta = extract_metadata(mf)

        lines.append(f"## {stem}\n")
        if png_file.exists():
            lines.append(f"![{stem}](architecture/png/{stem}.png)\n")
        else:
            lines.append(f"*PNG не найден: `architecture/png/{stem}.png`*\n")

        lines.append(f"- Исходная диаграмма: `mmd-diagrams/architecture/{mf.name}`\n")

        lines.append("## Описание")
        lines.append(build_description(stem, meta))
        lines.append("")

        # Metadata
        meta_lines = []
        if "type" in meta:
            meta_lines.append(f"- Тип: `{meta['type']}`")
        if "level" in meta:
            meta_lines.append(f"- Уровень: `{meta['level']}`")
        if "date" in meta:
            meta_lines.append(f"- Дата метаданных: `{meta['date']}`")
        if "nodes" in meta:
            meta_lines.append(f"- Узлы: `{meta['nodes']}`")
        if meta_lines:
            lines.append("## Метаданные")
            lines.extend(meta_lines)
            lines.append("")

        lines.append('<div style="page-break-after: always;"></div>\n')

    OUTPUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] Generated: {OUTPUT_MD}")
    print(f"[INFO] Diagrams included: {len(mmd_files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
