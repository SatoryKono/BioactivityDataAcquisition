"""Archive a curated note that should no longer remain active memory."""

from __future__ import annotations

import argparse
from pathlib import Path

from memory.notes import parse_markdown_note, utc_now_iso, write_markdown_note
from memory.resources import discover_memory_root, load_yaml_resource


def _archive_root() -> Path:
    memory_root = discover_memory_root()
    policy = load_yaml_resource(memory_root / "policy" / "promotion.yaml")
    archive_dir = str(
        policy.get("archive", {}).get("archive_dir") or "src/memory/curated/archive"
    )
    normalized = archive_dir.removeprefix("src/memory/")
    return memory_root / normalized


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Archive an active curated memory note."
    )
    parser.add_argument(
        "--source", type=Path, required=True, help="Curated note to archive."
    )
    parser.add_argument(
        "--reason", required=True, help="Short reason why the note is being archived."
    )
    parser.add_argument("--output", type=Path, help="Optional explicit archive path.")
    parser.add_argument(
        "--move",
        action="store_true",
        help="Delete the active source note after archiving.",
    )
    return parser


def archive_note(
    source: Path,
    *,
    reason: str,
    output_path: Path | None = None,
    move: bool = True,
) -> Path:
    """Archive one curated note under src/memory/curated/archive."""
    if not reason.strip():
        raise ValueError("archive reason must be non-empty")
    note = parse_markdown_note(source)
    metadata = dict(note.metadata)
    metadata["archived_at"] = utc_now_iso()
    metadata["archived_reason"] = reason.strip()
    metadata["archived_from"] = source.as_posix()

    parent_name = source.parent.name
    target = output_path or (_archive_root() / parent_name / source.name)
    write_markdown_note(target, metadata, note.body)
    if move:
        source.unlink()
    return target


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    path = archive_note(
        args.source.resolve(),
        reason=args.reason,
        output_path=args.output,
        move=args.move,
    )
    print(f"Archived memory note: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
