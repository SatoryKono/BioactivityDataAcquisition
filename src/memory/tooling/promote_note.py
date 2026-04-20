"""Promote episodic memory notes into curated long-term memory notes."""

from __future__ import annotations

import argparse
from pathlib import Path

from memory.notes import parse_markdown_note, utc_now_iso, write_markdown_note
from memory.resources import discover_memory_root


def _curated_targets() -> dict[str, Path]:
    memory_root = discover_memory_root()
    return {
        "decision": memory_root / "curated" / "decisions",
        "incident": memory_root / "curated" / "incidents",
        "lesson": memory_root / "curated" / "lessons",
        "domain_knowledge": memory_root / "curated" / "domain_knowledge",
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promote an episodic note into curated long-term memory."
    )
    parser.add_argument("--source", type=Path, required=True, help="Source episodic markdown note.")
    parser.add_argument(
        "--target-kind",
        choices=sorted(_curated_targets()),
        required=True,
        help="Curated target family.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional explicit output path. Defaults to the canonical curated subtree.",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Delete the source episodic note after successful promotion.",
    )
    return parser


def promote_note(
    source: Path,
    *,
    target_kind: str,
    output_path: Path | None = None,
    move: bool = False,
) -> Path:
    """Promote one episodic markdown note into curated memory."""
    note = parse_markdown_note(source)
    metadata = dict(note.metadata)
    title = str(metadata.get("title") or source.stem)
    note_id = str(metadata.get("id") or source.stem)

    metadata.pop("task_id", None)
    metadata.pop("ttl_days", None)
    metadata.pop("created_at", None)
    metadata.pop("confidence", None)
    metadata["id"] = note_id
    metadata["title"] = title
    metadata["kind"] = target_kind
    metadata["confidence"] = "curated"
    metadata["last_verified"] = utc_now_iso()
    metadata["promoted_from"] = source.as_posix()
    metadata["summary"] = metadata.get("summary") or "Promoted from episodic memory."

    output = output_path or (_curated_targets()[target_kind] / f"{note_id}.md")
    write_markdown_note(output, metadata, note.body)

    if move:
        source.unlink()

    return output


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    path = promote_note(
        args.source.resolve(),
        target_kind=args.target_kind,
        output_path=args.output,
        move=args.move,
    )
    print(f"Promoted memory note: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
