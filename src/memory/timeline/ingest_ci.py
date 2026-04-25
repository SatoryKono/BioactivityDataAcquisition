"""Project CI timeline seed events from workflow definitions."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from memory.graph.refs import (
    graph_refs_for_workflow,
    graph_refs_for_workflow_job,
    related_refs_for_workflow,
    related_refs_for_workflow_job,
)
from memory.timeline._common import (
    DEFAULT_EVENTS_DIR,
    dedupe_preserve_order,
    write_jsonl,
)

DEFAULT_WORKFLOWS_DIR = Path(".github/workflows")


def build_ci_events(root: Path) -> list[dict[str, Any]]:
    """Build deterministic CI events from workflow definitions."""
    workflows_dir = root / DEFAULT_WORKFLOWS_DIR
    events: list[dict[str, Any]] = []
    if not workflows_dir.exists():
        return events

    for workflow_path in sorted(workflows_dir.glob("*.y*ml")):
        payload = yaml.safe_load(workflow_path.read_text(encoding="utf-8")) or {}
        rel = workflow_path.relative_to(root).as_posix()
        workflow_name = payload.get("name") or workflow_path.stem
        events.append(
            {
                "id": f"ci-workflow::{workflow_path.stem}",
                "event_type": "ci.workflow_defined",
                "event_family": "ci",
                "severity": "info",
                "occurred_at": None,
                "source_refs": [rel],
                "graph_node_refs": graph_refs_for_workflow(rel, workflow_name),
                "related_refs": related_refs_for_workflow(rel, workflow_name),
                "confidence": "derived",
                "payload": {
                    "workflow_name": workflow_name,
                    "path": rel,
                    "job_count": len((payload.get("jobs") or {}).keys()),
                },
            }
        )
        for job_name in sorted((payload.get("jobs") or {}).keys()):
            events.append(
                {
                    "id": f"ci-job::{workflow_path.stem}::{job_name}",
                    "event_type": "ci.job_defined",
                    "event_family": "ci",
                    "severity": "info",
                    "occurred_at": None,
                    "source_refs": [rel],
                    "graph_node_refs": graph_refs_for_workflow_job(
                        rel, workflow_name, job_name
                    ),
                    "related_refs": dedupe_preserve_order(
                        related_refs_for_workflow_job(rel, workflow_name, job_name)
                    ),
                    "confidence": "derived",
                    "payload": {
                        "workflow_name": workflow_name,
                        "workflow_path": rel,
                        "job_name": job_name,
                    },
                }
            )
    return events


def write_ci_events(root: Path, output_path: Path | None = None) -> Path:
    """Write projected CI events as JSONL."""
    path = output_path or (DEFAULT_EVENTS_DIR / "ci.jsonl")
    return write_jsonl(path, build_ci_events(root))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project CI timeline events.")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_EVENTS_DIR / "ci.jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    write_ci_events(args.root.resolve(), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
