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
    manifest_event = next(
        event for event in events if event["event_type"] == "run.manifest_registered"
    )
    assert manifest_event["event_family"] == "run"
    assert "runtime_evidence_surface:run_manifest" in manifest_event["graph_node_refs"]
    assert "pipeline_surface:chembl_activity" in manifest_event["graph_node_refs"]
    assert "pipeline::chembl_activity" in manifest_event["related_refs"]
    assert "provider::chembl" in manifest_event["related_refs"]
    assert "entity::chembl.activity" in manifest_event["related_refs"]
    assert "run-id::r1" in manifest_event["related_refs"]
    ledger_event = next(
        event for event in events if event["event_type"] == "run.run_started"
    )
    assert "run-manifest::m1" in ledger_event["related_refs"]
    assert "runtime-evidence::run_ledger" in ledger_event["related_refs"]


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
    job_event = next(
        event for event in events if event["event_type"] == "ci.job_defined"
    )
    assert "workflow_job_surface:Tests::lint" in job_event["graph_node_refs"]
    assert "workflow::Tests" in job_event["related_refs"]
    assert "workflow-job::Tests::lint" in job_event["related_refs"]
    assert "workflow-path::.github/workflows/tests.yml" in job_event["related_refs"]


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
    assert events[0]["event_family"] == "incident"
    assert (
        "doc_artifact:docs/05-operations/runbooks/incident-response.md"
        in events[0]["graph_node_refs"]
    )
    assert (
        "runbook::docs/05-operations/runbooks/incident-response.md"
        in events[0]["related_refs"]
    )
    assert "incident::incident-response" in events[0]["related_refs"]


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
