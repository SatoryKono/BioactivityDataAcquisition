"""Create curated or episodic markdown notes from built-in templates."""

from __future__ import annotations

import argparse
from pathlib import Path

from memory.notes import parse_markdown_note, slugify, utc_now_iso, write_markdown_note
from memory.resources import discover_memory_root


NOTE_KINDS: dict[str, dict[str, str]] = {
    "episodic-session": {
        "target_dir": "episodic/sessions",
        "kind": "session",
        "template": "episodic/templates/session.md",
    },
    "episodic-summary": {
        "target_dir": "episodic/summaries",
        "kind": "summary",
        "template": "episodic/templates/summary.md",
    },
    "curated-decision": {
        "target_dir": "curated/decisions",
        "kind": "decision",
        "template": "curated/templates/decision.md",
    },
    "curated-incident": {
        "target_dir": "curated/incidents",
        "kind": "incident",
        "template": "curated/templates/incident.md",
    },
    "curated-lesson": {
        "target_dir": "curated/lessons",
        "kind": "lesson",
        "template": "curated/templates/lesson.md",
    },
    "curated-domain-knowledge": {
        "target_dir": "curated/domain_knowledge",
        "kind": "domain_knowledge",
        "template": "curated/templates/domain_knowledge.md",
    },
}


def _template_note(memory_root: Path, template_rel_path: str):
    return parse_markdown_note(memory_root / template_rel_path)


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
    template = _template_note(memory_root, config["template"])

    metadata = {
        **template.metadata,
        "id": slug,
        "title": title,
        "source_refs": source_refs or ["<add-source-ref>"],
    }

    if note_kind.startswith("episodic-"):
        if not task_id:
            raise ValueError("--task-id is required for episodic notes")
        metadata.update(
            {
                "kind": config["kind"],
                "task_id": task_id,
                "created_at": timestamp,
                "ttl_days": 14,
                "confidence": "episodic",
                "summary": "Short-lived working context.",
            }
        )
        body = template.body
    else:
        metadata.update(
            {
                "kind": config["kind"],
                "confidence": "curated",
                "last_verified": timestamp,
                "summary": "Replace with a durable summary.",
            }
        )
        body = template.body

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
