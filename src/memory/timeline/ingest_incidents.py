"""Project incident timeline seed events from active incident/failure runbooks."""

from __future__ import annotations

import argparse
from pathlib import Path

from memory.graph.refs import graph_refs_for_source, related_refs_for_source
from memory.rag.chunking import split_markdown_sections
from memory.timeline._common import DEFAULT_EVENTS_DIR, dedupe_preserve_order, write_jsonl

DEFAULT_RUNBOOKS_DIR = Path("docs/05-operations/runbooks")
INCIDENT_KEYWORDS = ("incident", "failure")


def build_incident_events(root: Path) -> list[dict[str, object]]:
    """Build deterministic incident/runbook events from active runbooks."""
    runbooks_dir = root / DEFAULT_RUNBOOKS_DIR
    events: list[dict[str, object]] = []
    if not runbooks_dir.exists():
        return events

    for path in sorted(runbooks_dir.glob("*.md")):
        rel = path.relative_to(root).as_posix()
        if not any(keyword in path.stem for keyword in INCIDENT_KEYWORDS):
            continue
        text = path.read_text(encoding="utf-8")
        sections = split_markdown_sections(text)
        title = sections[0].title if sections else path.stem
        events.append(
            {
                "id": f"incident-runbook::{path.stem}",
                "event_type": "incident.runbook_defined",
                "event_family": "incident",
                "severity": "warning",
                "occurred_at": None,
                "source_refs": [rel],
                "graph_node_refs": graph_refs_for_source(rel, "runbook"),
                "related_refs": dedupe_preserve_order(related_refs_for_source(rel, "runbook")),
                "confidence": "derived",
                "payload": {
                    "title": title,
                    "path": rel,
                    "section_count": len(sections),
                },
            }
        )
    return events


def write_incident_events(root: Path, output_path: Path | None = None) -> Path:
    """Write projected incident events as JSONL."""
    path = output_path or (DEFAULT_EVENTS_DIR / "incidents.jsonl")
    return write_jsonl(path, build_incident_events(root))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project incident timeline events.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, default=DEFAULT_EVENTS_DIR / "incidents.jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    output = write_incident_events(args.root.resolve(), args.output)
    print(f"Wrote incident timeline events to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
