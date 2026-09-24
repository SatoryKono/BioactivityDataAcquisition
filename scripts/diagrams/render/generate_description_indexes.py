#!/usr/bin/env python3
"""Generate family-oriented indexes for diagram description cards."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT_IMPORT = SCRIPT_DIR.parents[2]
if str(REPO_ROOT_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_IMPORT))

try:
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT
except ImportError:  # pragma: no cover - direct script execution
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT


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
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when tracked indexes drift. Stamp text is normalized.",
    )
    return parser.parse_args(argv)


_STAMP_RE = re.compile(r"(_Автогенерация: )[^_\n]+(_)|(- Generated: )\S+")
_UTC_STAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00")
_STAMP_PAYLOAD_RE = re.compile(r"_Автогенерация: ([^_]+)_|- Generated: (\S+)")


def deterministic_stamp(source: Path) -> str:
    """UTC stamp from SOURCE_DATE_EPOCH or the newest commit touching source."""
    epoch = os.environ.get("SOURCE_DATE_EPOCH", "").strip()
    if epoch:
        moment = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
        return moment.isoformat(timespec="seconds")
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI", "--", source.as_posix()],
        cwd=REPO_ROOT_IMPORT,
        check=False,
        capture_output=True,
        text=True,
    )
    raw = result.stdout.strip()
    if result.returncode != 0 or not raw:
        return "1970-01-01T00:00:00+00:00"
    moment = datetime.fromisoformat(raw)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


def normalize_generated_stamp(text: str) -> str:
    """Replace generated stamp payloads so --check ignores clock drift."""

    def _replace(match: re.Match[str]) -> str:
        if match.group(1):
            return f"{match.group(1)}<stamp>{match.group(2)}"
        return f"{match.group(3)}<stamp>"

    return _STAMP_RE.sub(_replace, text.replace("\r\n", "\n"))


def generated_stamps_are_utc(text: str) -> bool:
    payloads = [left or right for left, right in _STAMP_PAYLOAD_RE.findall(text)]
    return bool(payloads) and all(_UTC_STAMP_RE.fullmatch(item) for item in payloads)


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(content, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def write_or_check(path: Path, content: str, *, check: bool) -> int:
    if not content.endswith("\n"):
        content = f"{content}\n"
    if not check:
        atomic_write_text(path, content)
        print(f"[OK] Generated: {path}")
        return 0
    if not path.is_file():
        print(f"[ERROR] Missing generated file: {path}")
        return 1
    existing = path.read_text(encoding="utf-8")
    if not generated_stamps_are_utc(existing):
        print(f"[ERROR] Generated stamp is not UTC: {path}")
        return 1
    if normalize_generated_stamp(existing) != normalize_generated_stamp(content):
        print(f"[ERROR] Generated content drift: {path}")
        return 1
    print(f"[OK] Checked: {path}")
    return 0


def _generated_at() -> str:
    return deterministic_stamp(DESCRIPTION_ROOT)


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
    atomic_write_text(path, content if content.endswith("\n") else f"{content}\n")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    targets = set(args.target or TARGETS)

    cards_by_family = {family: collect_cards(family) for family in FAMILY_DIR_LABELS}
    exit_code = 0

    if "root" in targets:
        exit_code |= write_or_check(
            ROOT_INDEX_PATH,
            build_root_index_markdown(cards_by_family),
            check=args.check,
        )

    if "class" in targets:
        exit_code |= write_or_check(
            CLASS_INDEX_PATH,
            build_class_index_markdown(cards_by_family["class"]),
            check=args.check,
        )

    generated_targets = ", ".join(sorted(targets))
    mode = "checked" if args.check else "updated"
    print(f"[INFO] Description index targets {mode}: {generated_targets}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
