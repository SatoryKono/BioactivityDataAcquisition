"""Promote episodic memory notes into curated long-term memory notes."""

from __future__ import annotations

import argparse
from pathlib import Path

from memory.notes import (
    normalize_text_key,
    parse_markdown_note,
    utc_now_iso,
    write_markdown_note,
)
from memory.resources import discover_memory_root, load_yaml_resource


def _curated_targets() -> dict[str, Path]:
    memory_root = discover_memory_root()
    return {
        "decision": memory_root / "curated" / "decisions",
        "incident": memory_root / "curated" / "incidents",
        "lesson": memory_root / "curated" / "lessons",
        "domain_knowledge": memory_root / "curated" / "domain_knowledge",
    }


def _promotion_policy() -> dict:
    memory_root = discover_memory_root()
    return load_yaml_resource(memory_root / "policy" / "promotion.yaml")


def _placeholder_markers() -> list[str]:
    policy = _promotion_policy()
    markers = policy.get("global", {}).get("placeholder_markers", [])
    return [str(marker).lower() for marker in markers if isinstance(marker, str)]


def _contains_placeholder(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _placeholder_markers())


def _existing_curated_notes(exclude: Path | None = None) -> list[Path]:
    notes: list[Path] = []
    for directory in _curated_targets().values():
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            if path.name == "README.md":
                continue
            if exclude is not None and path.resolve() == exclude.resolve():
                continue
            notes.append(path)
    return notes


def _detect_duplicates(note_id: str, title: str) -> list[str]:
    normalized_title = normalize_text_key(title)
    duplicates: list[str] = []
    for path in _existing_curated_notes():
        note = parse_markdown_note(path)
        metadata = note.metadata
        if str(metadata.get("id") or "") == note_id:
            duplicates.append(f"id:{path.as_posix()}")
            continue
        existing_title = str(metadata.get("title") or "")
        if existing_title and normalize_text_key(existing_title) == normalized_title:
            duplicates.append(f"title:{path.as_posix()}")
    return duplicates


def _build_curated_body(target_kind: str, source_path: Path, source_body: str) -> str:
    quoted_source = "\n".join(f"> {line}" if line else ">" for line in source_body.strip().splitlines())
    if target_kind == "decision":
        return (
            "# Decision\n\n"
            "## Context\n\n"
            f"{quoted_source}\n\n"
            "## Durable guidance\n\n"
            "- Preserve the cited decision unless the referenced sources change.\n\n"
            "## Follow-up\n\n"
            f"- Re-verify this note when {source_path.name} or its source refs change.\n"
        )
    if target_kind == "incident":
        return (
            "# Incident lesson\n\n"
            "## Trigger pattern\n\n"
            f"{quoted_source}\n\n"
            "## Response guidance\n\n"
            "- Start from the cited runbook or operational source before improvising a fix.\n\n"
            "## Durable lesson\n\n"
            "- Keep this note aligned with recurring failure patterns only.\n"
        )
    if target_kind == "domain_knowledge":
        return (
            "# Domain knowledge\n\n"
            "## Concept\n\n"
            f"{quoted_source}\n\n"
            "## Practical implications\n\n"
            "- Reuse this concept only when the cited source refs still describe the same domain rule.\n"
        )
    return (
        "# Lesson\n\n"
        "## Observation\n\n"
        f"{quoted_source}\n\n"
        "## Reuse guidance\n\n"
        "- Apply this lesson only when the same source-backed conditions are present again.\n"
    )


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
        "--summary",
        required=True,
        help="Durable summary explaining why this note is worth promotion.",
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
    parser.add_argument(
        "--force-duplicate",
        action="store_true",
        help="Allow promotion even if a duplicate curated note is detected.",
    )
    return parser


def promote_note(
    source: Path,
    *,
    target_kind: str,
    summary: str,
    output_path: Path | None = None,
    move: bool = False,
    force_duplicate: bool = False,
) -> Path:
    """Promote one episodic markdown note into curated memory."""
    note = parse_markdown_note(source)
    metadata = dict(note.metadata)
    title = str(metadata.get("title") or source.stem)
    note_id = str(metadata.get("id") or source.stem)
    source_refs = metadata.get("source_refs") or []
    if not isinstance(source_refs, list) or not source_refs:
        raise ValueError("source episodic note must contain non-empty source_refs before promotion")
    if any(_contains_placeholder(str(ref)) for ref in source_refs):
        raise ValueError("source episodic note still contains placeholder source_refs")
    if _contains_placeholder(summary):
        raise ValueError("promotion summary must be explicit and non-placeholder")

    duplicates = _detect_duplicates(note_id, title)
    if duplicates and not force_duplicate:
        raise ValueError(f"duplicate curated note detected: {', '.join(duplicates)}")

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
    metadata["summary"] = summary.strip()

    output = output_path or (_curated_targets()[target_kind] / f"{note_id}.md")
    body = _build_curated_body(target_kind, source, note.body)
    write_markdown_note(output, metadata, body)

    if move:
        source.unlink()

    return output


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    path = promote_note(
        args.source.resolve(),
        target_kind=args.target_kind,
        summary=args.summary,
        output_path=args.output,
        move=args.move,
        force_duplicate=args.force_duplicate,
    )
    print(f"Promoted memory note: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
