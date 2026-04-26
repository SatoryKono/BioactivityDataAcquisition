#!/usr/bin/env python3
"""Generate family-oriented indexes for diagram description cards."""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path

try:
    from .diagram_paths import DIAGRAM_ROOT
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import DIAGRAM_ROOT


DESCRIPTION_ROOT = DIAGRAM_ROOT / "descriptions"
INDEX_FILENAME = "INDEX.md"
ROOT_INDEX_PATH = DESCRIPTION_ROOT / INDEX_FILENAME
CLASS_INDEX_PATH = DESCRIPTION_ROOT / "class" / INDEX_FILENAME
CLASS_INDEX_LINK = f"./class/{INDEX_FILENAME}"
ROOT_INDEX_LINK = f"../{INDEX_FILENAME}"
TARGETS = ("root", "class")
VIEW_SUFFIX_ORDER = ("-full", "-overview", "-dataflow", "-domain", "-infra")
FAMILY_DIR_LABELS = {
    "architecture": "Architecture",
    "class": "Class Diagrams",
    "foundation": "Foundation",
    "views": "Views",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate family-oriented indexes for diagram descriptions."
    )
    parser.add_argument(
        "--target",
        action="append",
        choices=TARGETS,
        help=(
            "Only generate the selected target. May be passed multiple times. "
            "Defaults to all supported targets."
        ),
    )
    return parser.parse_args(argv)


def _generated_at() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def collect_cards(family: str) -> list[Path]:
    family_dir = DESCRIPTION_ROOT / family
    return sorted(
        path for path in family_dir.glob("*.md") if path.name != INDEX_FILENAME
    )


def _link_from(index_path: Path, target_path: Path) -> str:
    return Path(os.path.relpath(target_path, index_path.parent)).as_posix()


def _view_family_key(stem: str) -> str:
    for suffix in VIEW_SUFFIX_ORDER:
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def _view_variant_label(stem: str) -> str:
    for suffix in VIEW_SUFFIX_ORDER:
        if stem.endswith(suffix):
            return suffix.removeprefix("-")
    return "variant"


def _preferred_view_card(paths: list[Path]) -> Path:
    for suffix in VIEW_SUFFIX_ORDER:
        for path in paths:
            if path.stem.endswith(suffix):
                return path
    return paths[0]


def build_grouped_view_lines(paths: list[Path], index_path: Path) -> list[str]:
    grouped: dict[str, list[Path]] = {}
    for path in paths:
        grouped.setdefault(_view_family_key(path.stem), []).append(path)

    lines: list[str] = []
    for family_key, family_paths in grouped.items():
        if len(family_paths) == 1:
            path = family_paths[0]
            lines.append(f"- [{path.stem}]({_link_from(index_path, path)})")
            continue

        anchor = _preferred_view_card(family_paths)
        variants = ", ".join(_view_variant_label(path.stem) for path in family_paths)
        lines.append(
            f"- [{family_key}]({_link_from(index_path, anchor)}) - "
            f"{len(family_paths)} cards: {variants}"
        )
    return lines


def build_root_index_markdown(cards_by_family: dict[str, list[Path]]) -> str:
    total_cards = sum(len(paths) for paths in cards_by_family.values())
    view_family_count = len(
        {_view_family_key(path.stem) for path in cards_by_family["views"]}
    )

    lines: list[str] = []
    lines.append("# Diagram Descriptions Index")
    lines.append("")
    lines.append(f"_Автогенерация: {_generated_at()}_")
    lines.append("")
    lines.append(f"- Карточек описаний: **{total_cards}**")
    lines.append(
        "- Формат публикации: family-oriented index для derived description cards."
    )
    lines.append(
        "- Source of truth: individual description cards под `descriptions/<family>/`."
    )
    lines.append("")
    lines.append("## Related Indexes")
    lines.append("")
    lines.append(f"- [Class descriptions family index]({CLASS_INDEX_LINK})")
    lines.append("- [MMD diagram descriptions map](./class-summary.md)")
    lines.append(
        "- [Architecture bundle with descriptions](../bundles/architecture.bundle.md)"
    )
    lines.append("- [Class bundle with descriptions](../bundles/class.bundle.md)")
    lines.append(
        "- [Foundation bundle with descriptions](../bundles/foundation.bundle.md)"
    )
    lines.append("- [Views bundle with descriptions](../bundles/views.bundle.md)")
    lines.append("")
    lines.append("## Family Overview")
    lines.append("")
    lines.append(f"- Architecture cards: **{len(cards_by_family['architecture'])}**")
    lines.append(f"- Class cards: **{len(cards_by_family['class'])}**")
    lines.append(f"- Foundation cards: **{len(cards_by_family['foundation'])}**")
    lines.append(
        f"- View cards: **{len(cards_by_family['views'])}** across "
        f"**{view_family_count}** parent families"
    )
    lines.append("")
    lines.append("## Architecture Cards")
    lines.append("")
    for path in cards_by_family["architecture"]:
        lines.append(f"- [{path.stem}]({_link_from(ROOT_INDEX_PATH, path)})")
    lines.append("")
    lines.append("## Class Diagram Cards")
    lines.append("")
    lines.append(
        f"- Dedicated family index: [class/{INDEX_FILENAME}]({CLASS_INDEX_LINK})"
    )
    lines.append(
        "- Narrative map for class-diagram families: [class-summary.md](./class-summary.md)"
    )
    lines.append("")
    lines.append("## Foundation Cards")
    lines.append("")
    for path in cards_by_family["foundation"]:
        lines.append(f"- [{path.stem}]({_link_from(ROOT_INDEX_PATH, path)})")
    lines.append("")
    lines.append("## View Families")
    lines.append("")
    lines.extend(build_grouped_view_lines(cards_by_family["views"], ROOT_INDEX_PATH))
    lines.append("")
    return "\n".join(lines)


def build_class_index_markdown(class_cards: list[Path]) -> str:
    lines: list[str] = []
    lines.append("# Class Diagrams - Descriptions Index")
    lines.append("")
    lines.append(f"_Автогенерация: {_generated_at()}_")
    lines.append("")
    lines.append(f"- Карточек описаний: **{len(class_cards)}**")
    lines.append(
        "- Scope: class-diagram description cards for canonical class families."
    )
    lines.append("")
    lines.append("## Related Indexes")
    lines.append("")
    lines.append(f"- [Diagram descriptions root index]({ROOT_INDEX_LINK})")
    lines.append("- [MMD diagram descriptions map](../class-summary.md)")
    lines.append("- [Class bundle with descriptions](../../bundles/class.bundle.md)")
    lines.append("")
    lines.append("## Cards")
    lines.append("")
    for path in class_cards:
        lines.append(f"- [{path.stem}]({_link_from(CLASS_INDEX_PATH, path)})")
    lines.append("")
    return "\n".join(lines)


def write_index(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets = set(args.target or TARGETS)

    cards_by_family = {family: collect_cards(family) for family in FAMILY_DIR_LABELS}

    if "root" in targets:
        write_index(ROOT_INDEX_PATH, build_root_index_markdown(cards_by_family))
        print(f"[OK] Generated: {ROOT_INDEX_PATH}")

    if "class" in targets:
        write_index(
            CLASS_INDEX_PATH,
            build_class_index_markdown(cards_by_family["class"]),
        )
        print(f"[OK] Generated: {CLASS_INDEX_PATH}")

    generated_targets = ", ".join(sorted(targets))
    print(f"[INFO] Description index targets updated: {generated_targets}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
