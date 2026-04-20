"""Project run timeline events from control-plane manifests and ledgers."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from memory.timeline._common import DEFAULT_EVENTS_DIR, read_json, read_jsonl, write_jsonl

DEFAULT_RUN_MANIFEST_DIR = Path("data/output/control/run_manifest")
DEFAULT_RUN_LEDGER_DIR = Path("data/output/control/run_ledger")


def _manifest_event(manifest_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"run-manifest::{payload['manifest_id']}",
        "event_type": "run.manifest_registered",
        "occurred_at": payload.get("created_at"),
        "source_refs": [manifest_path.as_posix()],
        "confidence": "derived",
        "payload": {
            "manifest_id": payload.get("manifest_id"),
            "run_id": payload.get("run_id"),
            "pipeline_name": payload.get("pipeline_name"),
            "provider": payload.get("provider"),
            "entity": payload.get("entity"),
            "run_type": payload.get("run_type"),
            "replay_capability": payload.get("replay_capability"),
        },
    }


def build_run_events(root: Path) -> list[dict[str, Any]]:
    """Build deterministic timeline events from run manifests and ledgers."""
    manifest_dir = root / DEFAULT_RUN_MANIFEST_DIR
    ledger_dir = root / DEFAULT_RUN_LEDGER_DIR
    events: list[dict[str, Any]] = []

    if manifest_dir.exists():
        for manifest_path in sorted(manifest_dir.glob("*.json")):
            manifest = read_json(manifest_path)
            events.append(_manifest_event(manifest_path.relative_to(root), manifest))

    if ledger_dir.exists():
        for ledger_path in sorted(ledger_dir.glob("*.jsonl")):
            for entry in read_jsonl(ledger_path):
                events.append(
                    {
                        "id": f"run-ledger::{entry.get('entry_id')}",
                        "event_type": f"run.{entry.get('event_type', 'unknown')}",
                        "occurred_at": entry.get("occurred_at"),
                        "source_refs": [ledger_path.relative_to(root).as_posix()],
                        "confidence": "derived",
                        "payload": {
                            "entry_id": entry.get("entry_id"),
                            "manifest_id": entry.get("manifest_id"),
                            "run_id": entry.get("run_id"),
                            "event_family": entry.get("event_family"),
                            "stage": entry.get("stage"),
                            "status": entry.get("status"),
                            "error_type": entry.get("error_type"),
                        },
                    }
                )
    return events


def write_run_events(root: Path, output_path: Path | None = None) -> Path:
    """Write projected run timeline events as JSONL."""
    path = output_path or (DEFAULT_EVENTS_DIR / "runs.jsonl")
    return write_jsonl(path, build_run_events(root))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project run timeline events.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, default=DEFAULT_EVENTS_DIR / "runs.jsonl")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    output = write_run_events(args.root.resolve(), args.output)
    print(f"Wrote run timeline events to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
