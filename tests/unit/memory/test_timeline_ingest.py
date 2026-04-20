"""Tests for timeline memory projection helpers."""

from __future__ import annotations

import json
from pathlib import Path

from memory.timeline.ingest_ci import build_ci_events, write_ci_events
from memory.timeline.ingest_incidents import build_incident_events
from memory.timeline.ingest_runs import build_run_events, write_run_events


def test_build_run_events_projects_manifest_and_ledger(tmp_path: Path) -> None:
    manifest_dir = tmp_path / "data/output/control/run_manifest"
    ledger_dir = tmp_path / "data/output/control/run_ledger"
    manifest_dir.mkdir(parents=True)
    ledger_dir.mkdir(parents=True)

    (manifest_dir / "m1.json").write_text(
        json.dumps(
            {
                "manifest_id": "m1",
                "run_id": "r1",
                "pipeline_name": "chembl_activity",
                "provider": "chembl",
                "entity": "activity",
                "run_type": "incremental",
                "replay_capability": "rebuild_only",
                "created_at": "2026-04-20T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (ledger_dir / "m1.jsonl").write_text(
        json.dumps(
            {
                "entry_id": "e1",
                "event_type": "run_started",
                "occurred_at": "2026-04-20T00:00:01Z",
                "manifest_id": "m1",
                "run_id": "r1",
                "event_family": "lifecycle",
                "status": "started",
                "stage": "init",
                "error_type": None,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    events = build_run_events(tmp_path)
    assert {event["event_type"] for event in events} == {
        "run.manifest_registered",
        "run.run_started",
    }


def test_build_ci_events_projects_workflows_and_jobs(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github/workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "tests.yml").write_text(
        """
name: Tests
jobs:
  lint:
    runs-on: ubuntu-latest
  unit:
    runs-on: ubuntu-latest
""".strip(),
        encoding="utf-8",
    )

    events = build_ci_events(tmp_path)
    assert any(event["event_type"] == "ci.workflow_defined" for event in events)
    assert any(event["event_type"] == "ci.job_defined" for event in events)


def test_build_incident_events_projects_incident_runbooks(tmp_path: Path) -> None:
    runbooks_dir = tmp_path / "docs/05-operations/runbooks"
    runbooks_dir.mkdir(parents=True)
    (runbooks_dir / "incident-response.md").write_text(
        "# Incident Response\n\n## Triage\nFollow steps.\n",
        encoding="utf-8",
    )
    (runbooks_dir / "normal-guide.md").write_text(
        "# Normal Guide\n",
        encoding="utf-8",
    )

    events = build_incident_events(tmp_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "incident.runbook_defined"


def test_write_timeline_outputs(tmp_path: Path) -> None:
    workflows_dir = tmp_path / ".github/workflows"
    workflows_dir.mkdir(parents=True)
    (workflows_dir / "tests.yml").write_text(
        "name: Tests\njobs:\n  lint:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )

    output = write_ci_events(tmp_path, tmp_path / "ci.jsonl")
    assert output.exists()
    assert "ci.workflow_defined" in output.read_text(encoding="utf-8")

    output = write_run_events(tmp_path, tmp_path / "runs.jsonl")
    assert output.exists()
