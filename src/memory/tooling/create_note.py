"""Create curated or episodic markdown notes from built-in templates."""

from __future__ import annotations

import argparse
from pathlib import Path

from memory.notes import slugify, utc_now_iso, write_markdown_note
from memory.resources import discover_memory_root


NOTE_KINDS: dict[str, dict[str, str]] = {
    "episodic-session": {
        "target_dir": "episodic/sessions",
        "kind": "session",
    },
    "episodic-summary": {
        "target_dir": "episodic/summaries",
        "kind": "summary",
    },
    "curated-decision": {
        "target_dir": "curated/decisions",
        "kind": "decision",
    },
    "curated-incident": {
        "target_dir": "curated/incidents",
        "kind": "incident",
    },
    "curated-lesson": {
        "target_dir": "curated/lessons",
        "kind": "lesson",
    },
    "curated-domain-knowledge": {
        "target_dir": "curated/domain_knowledge",
        "kind": "domain_knowledge",
    },
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a memory note from a built-in template.")
    parser.add_argument("--kind", required=True, choices=sorted(NOTE_KINDS))
    parser.add_argument("--title", required=True)
    parser.add_argument("--task-id", help="Required for episodic notes.")
    parser.add_argument(
        "--source-ref",
        action="append",
        default=[],
        help="Repeatable source reference to include in note metadata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional explicit output path. Defaults to the canonical memory subtree.",
    )
    return parser


def create_note(
    *,
    note_kind: str,
    title: str,
    task_id: str | None,
    source_refs: list[str],
    output_path: Path | None = None,
) -> Path:
    """Create a markdown note in the canonical memory subtree."""
    config = NOTE_KINDS[note_kind]
    slug = slugify(title)
    memory_root = discover_memory_root()
    output = output_path or (memory_root / config["target_dir"] / f"{slug}.md")
    timestamp = utc_now_iso()

    metadata = {
        "id": slug,
        "title": title,
        "source_refs": source_refs or ["<add-source-ref>"],
    }

    if note_kind.startswith("episodic-"):
        if not task_id:
            raise ValueError("--task-id is required for episodic notes")
        metadata.update(
            {
                "task_id": task_id,
                "created_at": timestamp,
                "ttl_days": 14,
                "confidence": "episodic",
                "summary": "Short-lived working context.",
            }
        )
        heading = "Session note" if note_kind == "episodic-session" else "Episodic summary"
        body = (
            f"# {heading}\n\n"
            "## Context\n\n"
            "- Replace with task-local context\n\n"
            "## Working notes\n\n"
            "- Replace with current findings\n"
        )
    else:
        metadata.update(
            {
                "kind": config["kind"],
                "confidence": "curated",
                "last_verified": timestamp,
                "summary": "Replace with a durable summary.",
            }
        )
        body = (
            f"# {title}\n\n"
            "## Context\n\n"
            "- Replace with durable context\n\n"
            "## Guidance\n\n"
            "- Replace with reusable guidance\n"
        )

    return write_markdown_note(output, metadata, body)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    path = create_note(
        note_kind=args.kind,
        title=args.title,
        task_id=args.task_id,
        source_refs=args.source_ref,
        output_path=args.output,
    )
    print(f"Created memory note: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
