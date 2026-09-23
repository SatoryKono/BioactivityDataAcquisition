"""Selected-run status cannot change with wall time, query range or current health."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    record_run_observation,
    reset_run_observations,
    run_observations,
)
from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
from bioetl.domain.run_reports.selected_status import (
    DOMAINS,
    build_snapshot,
    verify_snapshot,
)
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)
from bioetl.interfaces.http.selected_run_status import (
    _saved_trust,
    handle_selected_run_status,
    load_selected_run_status,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "reasons,count", [("", 0), ("missing_archive\n\nmissing_lineage", 2)]
)
def test_saved_trust_reason_count_preserves_full_details(reasons, count):
    saved = {
        "observations": {
            "Control Plane": {"facts": {"checks": {"trust": {"reasons_text": reasons}}}}
        }
    }
    summary = dict.fromkeys(
        ("evaluation_at", "pipeline", "run_id", "rules_version", "revision"), "value"
    )
    summary["execution_state"] = "SUCCESS"
    result = _saved_trust(
        saved,
        summary,
        [{"domain": "Control Plane", "reason": "fallback", "verdict": "OK"}],
    )
    assert result["reasons_count"] == count
    assert result["reasons_text"] == reasons


def report(run_id="run-a", status="success"):
    draft = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_activity",
            "run_id": run_id,
            "status": status,
            "started_at": "2026-01-01T00:00:00+00:00",
            "completed_at": "2026-01-01T00:01:00+00:00",
        },
        metrics={},
    )
    return replace(
        draft,
        observations={
            name: {"verdict": "OK", "reason": "checked", "facts": {"count": 0}}
            for name in DOMAINS[1:]
        },
    )


def test_saved_accounting_conflict_is_visible_without_rewriting_snapshot(tmp_path):
    original = replace(
        report(),
        reconciliation={
            "silver_vs_bronze_status": "FAILING",
            "silver_delta": -154,
            "gold_vs_silver_status": "OK",
            "gold_delta": 0,
        },
    )
    persisted = persist(tmp_path, original)
    before = persisted.json_path.read_bytes()
    result = read(tmp_path)
    trust = result["trust"][0]
    assert trust["saved_trust_status"] == "OK"
    assert trust["trust_status"] == "ERROR"
    assert trust["accounting_integrity"] == "CONFLICT"
    assert "delta=-154" in trust["reasons_display"]
    assert "Saved Trust verdict: OK" in trust["reasons_display"]
    assert result["verdict"] == "OK"  # Frozen assessment remains historical evidence.
    control = next(row for row in result["domains"] if row["domain"] == "Control Plane")
    assert control["verdict"] == "OK"
    assert control["display_verdict"] == "ERROR"
    assert persisted.json_path.read_bytes() == before


def persist(tmp_path, value=None, store=None):
    return write_pipeline_run_report(
        value or report(), root=tmp_path, store=store or FileRunReportStoreAdapter()
    )


def read(tmp_path, run_id="run-a"):
    return load_selected_run_status(
        pipeline="chembl_activity", run_id=run_id, root=tmp_path
    )


def test_domain_detail_exposes_all_frozen_trust_reasons(tmp_path):
    original = report()
    reasons = "lineage_fragments_missing\nlineage_identity_not_observable"
    value = replace(
        original,
        observations={
            **original.observations,
            "Control Plane": {
                "verdict": "INCOMPLETE",
                "reason": "run_completion_trust_assessment",
                "facts": {"checks": {"trust": {"reasons_text": reasons}}},
            },
        },
    )
    persist(tmp_path, value)
    result = read(tmp_path)
    control = next(row for row in result["domains"] if row["domain"] == "Control Plane")
    assert control["reason"] == "run_completion_trust_assessment"
    assert control["reason_display"] == result["trust"][0]["reasons_display"]
    assert result["trust"][0]["reasons_text"] == reasons
    assert result["trust"][0]["reasons_count"] == 2


def test_late_assessment_time_is_separate_from_completion(tmp_path):
    from bioetl.application.services.run_reports.snapshots import publish_snapshot

    path = persist(tmp_path).json_path
    original = json.loads(path.read_text())
    original.pop("selected_run_snapshot")
    original["assessment_at"] = "2026-01-02T00:00:00+00:00"
    updated = publish_snapshot(original, path, store=FileRunReportStoreAdapter())
    path.write_text(json.dumps(updated))
    result = read(tmp_path)
    assert result["evaluation_at"] == original["assessment_at"]
    assert result["completed_at"] == "2026-01-01T00:01:00+00:00"


@pytest.mark.parametrize("age", [300, 899, 900, 901, 86400, 604800])
@pytest.mark.parametrize(
    "chart_range",
    [(0, 1), (1704067200000, 1704067201000), (0, 9999999999999), (None, None)],
)
async def test_http_ignores_time_and_range(tmp_path, monkeypatch, age, chart_range):
    persist(tmp_path)
    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops._effective_root", lambda root: tmp_path
    )
    # The wall-clock is controlled independently of the immutable observation time.
    current = datetime(2026, 1, 1, 0, 1, tzinfo=UTC) + timedelta(seconds=age)
    monkeypatch.setattr("time.time", lambda: current.timestamp())
    host = MagicMock()
    host._read_required_param.side_effect = lambda query, key: query[key]
    host._read_optional_param.side_effect = lambda query, key: query.get(key)
    host._forensic_endpoint_limiter = asyncio.Semaphore(2)
    host._send_payload_response = AsyncMock()
    query = {
        "pipeline": "chembl_activity",
        "run_id": "run-a",
        "from": str(chart_range[0]),
        "to": str(chart_range[1]),
    }
    await handle_selected_run_status(host, MagicMock(), query)
    payload = host._send_payload_response.call_args.args[2]
    assert payload == read(tmp_path)
    assert payload["verdict"] == "OK"
    assert payload["replay_readiness_now"] == "NOT EVALUATED"


@pytest.mark.parametrize(
    "status,expected",
    [
        ("success", "OK"),
        ("failed", "ERROR"),
        ("shutdown", "WARN"),
        ("cancelled", "WARN"),
        ("running", "RUNNING"),
    ],
)
def test_execution_and_checks_separate(tmp_path, status, expected):
    persist(tmp_path, report(status=status))
    result = read(tmp_path)
    assert result["verdict"] == expected
    assert result["execution_state"] == status.upper()
    assert result["evidence_availability"] == "AVAILABLE"


def test_finalization_idempotent_and_late_evidence_revision(tmp_path):
    paths = persist(tmp_path)
    first = read(tmp_path)
    persist(tmp_path)
    assert read(tmp_path) == first
    changed = report()
    changed.observations["Provider"]["verdict"] = "ERROR"
    persist(tmp_path, changed)
    second = read(tmp_path)
    assert second["verdict"] == "ERROR"
    assert first["revision"] != second["revision"]
    revisions = list((paths.json_path.parent / "status-revisions").glob("*.json"))
    assert len(revisions) == 2
    assert all(verify_snapshot(json.loads(path.read_text())) for path in revisions)


def test_interrupted_publication_preserves_previous_commit(tmp_path):
    persist(tmp_path)
    before = read(tmp_path)

    class InterruptedStore(FileRunReportStoreAdapter):
        def write_text(self, path, content):
            if path.endswith("pipeline-run-report.json"):
                raise OSError("interrupted")
            super().write_text(path, content)

    with pytest.raises(OSError):
        persist(tmp_path, report(status="failed"), InterruptedStore())
    assert read(tmp_path) == before


@pytest.mark.parametrize(
    "damage,verdict,reason",
    [
        ("report", "ERROR", "evidence_corrupt"),
        ("revision", "ERROR", "evidence_corrupt"),
        ("delete_revision", "INCOMPLETE", "revision_missing"),
        ("identity", "ERROR", "identity_mismatch"),
        ("rules", "ERROR", "evidence_corrupt"),
    ],
)
def test_loss_corruption_identity_and_rules_fail_closed(
    tmp_path, damage, verdict, reason
):
    paths = persist(tmp_path)
    assert read(tmp_path)["verdict"] == "OK"
    payload = json.loads(paths.json_path.read_text())
    revision = (
        paths.json_path.parent
        / "status-revisions"
        / f"{payload['selected_run_snapshot']['revision']}.json"
    )
    if damage == "report":
        paths.json_path.write_text("{")
    elif damage == "revision":
        revision.write_text("{")
    elif damage == "delete_revision":
        revision.unlink()
    else:
        if damage == "identity":
            payload["identity"]["run_id"] = "another-run"
        else:
            payload["selected_run_snapshot"]["assessment"]["rules_version"] = "future"
        paths.json_path.write_text(json.dumps(payload))
    result = read(tmp_path)
    assert (result["verdict"], result["reason"]) == (verdict, reason)


def test_neighbour_and_empty_selection(tmp_path):
    persist(tmp_path)
    persist(tmp_path, report(run_id="run-b", status="failed"))
    assert read(tmp_path)["verdict"] == "OK"
    assert read(tmp_path, "run-b")["verdict"] == "ERROR"
    assert read(tmp_path, "-")["verdict"] == "SELECT RUN"
    assert read(tmp_path, "absent")["reason"] == "run_not_found"


def test_legacy_never_invents_missing_observations(tmp_path):
    paths = persist(tmp_path)
    payload = report().to_dict()
    payload.pop("observations")
    paths.json_path.write_text(json.dumps(payload))
    result = read(tmp_path)
    assert result["verdict"] == "INCOMPLETE"
    assert result["evidence_availability"] == "legacy_no_snapshot"
    domains = {row["domain"]: row["verdict"] for row in result["domains"]}
    assert domains["Workflow"] == "N/A"
    assert domains["Provider"] == "INCOMPLETE"


async def test_concurrent_observations_are_isolated_and_failures_not_erased():
    async def observe(verdict):
        token = bind_run_observations()
        try:
            record_run_observation(
                "Provider", verdict=verdict, reason="probe", facts={}
            )
            await asyncio.sleep(0)
            record_run_observation("Provider", verdict="OK", reason="later", facts={})
            return run_observations()
        finally:
            reset_run_observations(token)

    failed, success = await asyncio.gather(observe("ERROR"), observe("OK"))
    assert failed["Provider"]["verdict"] == "ERROR"
    assert success["Provider"]["verdict"] == "OK"
    assert run_observations() == {}


def test_snapshot_tamper_invalidates_assessment():
    snapshot = build_snapshot(report().to_dict())
    snapshot["assessment"]["verdict"] = "N/A"
    assert not verify_snapshot(snapshot)


@pytest.mark.parametrize("reason", ["timeout", "queue_full"])
async def test_endpoint_timeout_is_query_error(monkeypatch, reason):
    from bioetl.interfaces.http._forensic_request_budget import (
        ForensicEndpointUnavailable,
    )

    async def fail(**kwargs):
        raise ForensicEndpointUnavailable(reason=reason, status_code=504)

    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.run_bounded_forensic_operation",
        fail,
    )
    host = MagicMock()
    host._read_required_param.return_value = "chembl_activity"
    host._read_optional_param.return_value = "run-a"
    host._send_payload_response = AsyncMock()
    await handle_selected_run_status(host, MagicMock(), {})
    payload = host._send_payload_response.call_args.args[2]
    assert payload["verdict"] == "QUERY ERROR"
    assert payload["reason"] == reason


def test_workflow_completion_creates_explicit_child_revision(tmp_path):
    from bioetl.application.services.run_reports.writer import write_workflow_run_report
    from bioetl.domain.run_reports.models import WorkflowExecutionRow, WorkflowRunReport

    child = report()
    child.identity["workflow_run_id"] = "workflow-a"
    child.observations.pop("Workflow")
    persist(tmp_path, child)
    before = read(tmp_path)
    workflow = WorkflowRunReport(
        identity={
            "workflow_name": "workflow",
            "workflow_run_id": "workflow-a",
            "status": "failed",
        },
        plan_steps=(),
        totals={},
        execution=(
            WorkflowExecutionRow(
                step_id="step-a",
                status="success",
                records_extracted=1,
                pipeline_name="chembl_activity",
                pipeline_run_id="run-a",
            ),
        ),
    )
    write_workflow_run_report(
        workflow, root=tmp_path, store=FileRunReportStoreAdapter()
    )
    after = read(tmp_path)
    assert before["verdict"] == "INCOMPLETE"
    assert after["verdict"] == "ERROR"
    assert before["revision"] != after["revision"]
    assert after["execution_state"] == "SUCCESS"


@pytest.mark.parametrize(
    "event,expected", [("run_started", "RUNNING"), ("run_finished", "INCOMPLETE")]
)
@pytest.mark.parametrize(
    "pipeline",
    ["chembl_activity", "{unknown,chembl_activity}", "unknown,chembl_activity"],
)
def test_active_and_unfinalized_run_do_not_expire(
    monkeypatch, event, expected, pipeline
):
    from types import SimpleNamespace
    from bioetl.interfaces.http._selected_run_live import active_run_diagnostics

    host = MagicMock()
    host._run_manifest_port.get_by_run_id.return_value = SimpleNamespace(
        pipeline_name="chembl_activity",
        manifest_id="m",
        workflow_name=None,
        run_type=SimpleNamespace(value="incremental"),
    )
    host._run_ledger_port.list_entries_by_run_id.return_value = [
        SimpleNamespace(
            manifest_id="m",
            event_type=event,
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]
    value = active_run_diagnostics(
        host, pipeline, "00000000-0000-0000-0000-000000000001"
    )
    assert value["verdict"] == expected
    assert value["heartbeat_now"] == "STALE"


@pytest.mark.parametrize(
    "current", ["healthy", "stale", "recovered", "publisher_restarted"]
)
async def test_current_telemetry_is_not_consulted(tmp_path, monkeypatch, current):
    persist(tmp_path)
    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops._effective_root", lambda root: tmp_path
    )
    host = MagicMock()
    host._read_required_param.side_effect = lambda q, key: q[key]
    host._read_optional_param.side_effect = lambda q, key: q.get(key)
    host._forensic_endpoint_limiter = asyncio.Semaphore(2)
    host._send_payload_response = AsyncMock()
    host._run_manifest_port.get_by_run_id.side_effect = AssertionError(current)
    host._run_ledger_port.list_entries_by_run_id.side_effect = AssertionError(current)
    await handle_selected_run_status(
        host, MagicMock(), {"pipeline": "chembl_activity", "run_id": "run-a"}
    )
    assert host._send_payload_response.call_args.args[2] == read(tmp_path)
    host._run_manifest_port.get_by_run_id.assert_not_called()
    host._run_ledger_port.list_entries_by_run_id.assert_not_called()


@pytest.mark.parametrize(
    "event", ["run_started", "run_finished", "run_failed", "run_shutdown"]
)
async def test_unfinalized_run_presentation_matches_ledger(
    tmp_path, monkeypatch, event
):
    """Grafana must see the same execution and heartbeat state as the API."""
    from types import SimpleNamespace

    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops._effective_root", lambda root: tmp_path
    )
    host = MagicMock()
    host._read_required_param.side_effect = lambda q, key: q[key]
    host._read_optional_param.side_effect = lambda q, key: q.get(key)
    host._forensic_endpoint_limiter = asyncio.Semaphore(2)
    host._send_payload_response = AsyncMock()
    host._run_manifest_port.get_by_run_id.return_value = SimpleNamespace(
        pipeline_name="chembl_activity",
        manifest_id="m",
        workflow_name=None,
        run_type=SimpleNamespace(value="incremental"),
    )
    host._run_ledger_port.list_entries_by_run_id.return_value = [
        SimpleNamespace(
            manifest_id="m",
            event_type=event,
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]
    await handle_selected_run_status(
        host,
        MagicMock(),
        {
            "pipeline": "chembl_activity",
            "run_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    payload = host._send_payload_response.call_args.args[2]
    execution = "RUNNING" if event == "run_started" else "TERMINAL"
    assert payload["execution_state"] == execution
    for field in ("summary", "presentation_summary", "domains", "presentation_domains"):
        for row in payload[field]:
            assert row["execution_state"] == execution
            assert row["heartbeat_now"] == "STALE"
            assert row["checks_verdict"] == "UNKNOWN"
            assert row["evidence_completeness"] == "INCOMPLETE"
            assert "presentation_summary" not in row
    for field in ("trust", "presentation_trust"):
        assert payload[field][0]["processing_status"] == execution


async def test_late_previous_request_keeps_its_own_identity(tmp_path, monkeypatch):
    if (
        Path("/proc/version").exists()
        and "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    ):
        pytest.skip(
            "WSL test runtime intentionally replaces asyncio.to_thread "
            "with inline execution to avoid lost executor callbacks"
        )
    import threading

    if asyncio.to_thread.__module__ != "asyncio.threads":
        pytest.skip(
            reason="requires real asyncio.to_thread worker offload; "
            "the WSL safeguard in tests/conftest.py runs it inline"
        )
    persist(tmp_path)
    persist(tmp_path, report(run_id="run-b", status="failed"))
    first_entered = threading.Event()
    release_first = threading.Event()
    real_load = load_selected_run_status

    def delayed_load(*, pipeline, run_id):
        if run_id == "run-a":
            first_entered.set()
            assert release_first.wait(5)
        return real_load(pipeline=pipeline, run_id=run_id, root=tmp_path)

    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.load_selected_run_status",
        delayed_load,
    )
    host = MagicMock()
    host._read_required_param.side_effect = lambda q, key: q[key]
    host._read_optional_param.side_effect = lambda q, key: q.get(key)
    host._forensic_endpoint_limiter = asyncio.Semaphore(2)
    host._send_payload_response = AsyncMock()
    first_writer, second_writer = MagicMock(), MagicMock()
    first = asyncio.create_task(
        handle_selected_run_status(
            host, first_writer, {"pipeline": "chembl_activity", "run_id": "run-a"}
        )
    )
    assert await asyncio.to_thread(first_entered.wait, 5)
    await handle_selected_run_status(
        host, second_writer, {"pipeline": "chembl_activity", "run_id": "run-b"}
    )
    release_first.set()
    await first
    responses = [
        (call.args[0], call.args[2])
        for call in host._send_payload_response.call_args_list
    ]
    assert responses[0][0] is second_writer and responses[0][1]["run_id"] == "run-b"
    assert responses[0][1]["verdict"] == "ERROR"
    assert responses[1][0] is first_writer and responses[1][1]["run_id"] == "run-a"
    assert responses[1][1]["verdict"] == "OK"


@pytest.mark.parametrize("missing", [True, False])
def test_control_plane_capture_binds_exact_identity_and_completion(tmp_path, missing):
    from types import SimpleNamespace
    from uuid import UUID
    from bioetl.application.services.run_reports.control_plane_snapshot import (
        CaptureControlPlaneSnapshot,
    )
    from bioetl.composition.bootstrap.runtime.run_status import (
        create_run_status_capture,
    )

    composed = create_run_status_capture(tmp_path)
    assert isinstance(composed, CaptureControlPlaneSnapshot)
    manifests, evidence = MagicMock(), MagicMock()
    manifests.get_by_run_id.return_value = (
        None if missing else SimpleNamespace(pipeline_name="chembl_activity")
    )
    evidence.trust_summary.return_value = {
        "trust_status": "ERROR",
        "rows": [{"reason": "lineage_gap"}],
    }
    capture = CaptureControlPlaneSnapshot(manifests, evidence)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    run_id = "11111111-1111-4111-8111-111111111111"
    token = bind_run_observations()
    try:
        capture("chembl_activity", run_id, now)
        observation = run_observations()["Control Plane"]
        assert observation["verdict"] == ("INCOMPLETE" if missing else "ERROR")
        manifests.get_by_run_id.assert_called_once_with(UUID(run_id))
        if not missing:
            assert evidence.trust_summary.call_args.kwargs["now"] == now
            assert (
                evidence.trust_summary.call_args.kwargs["scope"].selected_run_id
                == run_id
            )
            assert observation["facts"]["checks"]["rows"][0]["reason"] == "lineage_gap"
    finally:
        reset_run_observations(token)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        ("missing", None),
        ("legacy", None),
        ("json_list", "workflow_child_report_corrupt"),
        ("snapshot", "workflow_child_snapshot_corrupt"),
        ("identity", "workflow_child_identity_mismatch"),
        ("manifest", "workflow_child_identity_mismatch"),
    ],
)
def test_workflow_rejects_unbound_child_evidence(tmp_path, mutation, reason):
    from bioetl.application.services.run_reports.workflow_observations import (
        _verified_child,
    )
    from bioetl.domain.run_reports.models import WorkflowExecutionRow

    child = report()
    child.identity["workflow_run_id"] = "workflow-a"
    path = persist(tmp_path, child).json_path
    payload = json.loads(path.read_text())
    if mutation == "missing":
        path.unlink()
    elif mutation == "legacy":
        payload.pop("selected_run_snapshot")
        path.write_text(json.dumps(payload))
    elif mutation == "json_list":
        path.write_text("[]")
    elif mutation == "snapshot":
        payload["selected_run_snapshot"]["revision"] = "corrupt"
        path.write_text(json.dumps(payload))
    row = WorkflowExecutionRow(
        step_id="step-a",
        status="success",
        records_extracted=1,
        pipeline_name="chembl_activity",
        pipeline_run_id="run-a",
        pipeline_manifest_id="foreign-manifest" if mutation == "manifest" else None,
    )
    store = FileRunReportStoreAdapter()
    if reason:
        with pytest.raises(ValueError, match=reason):
            _verified_child(
                path,
                row,
                "different" if mutation == "identity" else "workflow-a",
                store,
            )
    else:
        assert _verified_child(path, row, "workflow-a", store) is None


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("no_port", None),
        ("not_found", None),
        ("wrong_pipeline", "identity_mismatch"),
        ("no_ledger", "ledger_missing"),
    ],
)
def test_active_run_requires_manifest_and_matching_ledger(scenario, expected):
    from types import SimpleNamespace
    from bioetl.interfaces.http._selected_run_live import active_run_diagnostics

    host = MagicMock()
    manifest = SimpleNamespace(
        pipeline_name="wrong" if scenario == "wrong_pipeline" else "chembl_activity",
        manifest_id="manifest-a",
    )
    if scenario == "no_port":
        host._run_manifest_port = None
    else:
        host._run_manifest_port.get_by_run_id.return_value = (
            None if scenario == "not_found" else manifest
        )
    host._run_ledger_port = None
    result = active_run_diagnostics(
        host, "chembl_activity", "3432761e-d4eb-511e-a62c-b186b301c758"
    )
    assert result is None if expected is None else result["reason"] == expected


@pytest.mark.parametrize(
    "kind", ["bad_schema", "bad_json", "read_error", "revision_corrupt"]
)
def test_report_read_failures_never_become_success(tmp_path, monkeypatch, kind):
    path = persist(tmp_path).json_path
    if kind == "bad_schema":
        path.write_text('{"schema_version":"future"}')
    elif kind == "bad_json":
        path.write_text("{")
    elif kind == "revision_corrupt":
        revision = next((path.parent / "status-revisions").glob("*.json"))
        revision.write_text("{}")
    else:
        original = Path.read_text

        def guarded_read(candidate, *args, **kwargs):
            if candidate == path:
                raise OSError("unavailable storage")
            return original(candidate, *args, **kwargs)

        monkeypatch.setattr(Path, "read_text", guarded_read)
    result = read(tmp_path)
    assert result["verdict"] == ("QUERY ERROR" if kind == "read_error" else "ERROR")


@pytest.mark.parametrize(
    "fault,reason",
    [
        ("report_list", "archive_report_corrupt"),
        ("identity", "archive_report_identity_mismatch"),
        ("snapshot", "archive_report_snapshot_corrupt"),
        ("evidence", "archive_report_evidence_mismatch"),
        ("missing_revision", "archive_report_revision_missing"),
        ("revision", "archive_report_revision_mismatch"),
        ("old_revision", "archive_report_revision_corrupt"),
    ],
)
def test_archive_refuses_corrupt_selected_evidence(tmp_path, fault, reason):
    from types import SimpleNamespace
    from bioetl.infrastructure.control_plane.archive_run_reports import (
        selected_report_sources,
    )

    path = persist(tmp_path).json_path
    payload = json.loads(path.read_text())
    revisions = path.parent / "status-revisions"
    revision = next(revisions.glob("*.json"))
    if fault == "report_list":
        payload = []
    elif fault == "identity":
        payload["identity"]["run_id"] = "other"
    elif fault == "snapshot":
        payload["selected_run_snapshot"]["revision"] = "bad"
    elif fault == "evidence":
        payload["identity"]["status"] = "failed"
    elif fault == "missing_revision":
        revision.unlink()
    elif fault == "revision":
        revision.write_text("{}")
    else:
        (revisions / "unbound.json").write_text("{}")
    path.write_text(json.dumps(payload))
    manifest = SimpleNamespace(run_id="run-a", pipeline_name="chembl_activity")
    with pytest.raises(ValueError, match=reason):
        selected_report_sources(tmp_path, manifest)


@pytest.mark.parametrize(
    "status,verdict", [("healthy", "OK"), ("degraded", "WARN"), ("unhealthy", "ERROR")]
)
def test_preflight_observations_retain_actual_probe_status(status, verdict):
    from bioetl.application.services.run_reports.observations import (
        observed_health_report,
        record_gold_observation,
    )
    from bioetl.domain.types import ComponentHealthResult, HealthStatus

    token = bind_run_observations()
    try:
        observed = datetime(2026, 1, 1, tzinfo=UTC)
        result = observed_health_report(
            [
                ComponentHealthResult(
                    component="storage", status=HealthStatus.HEALTHY, duration_seconds=0
                ),
                ComponentHealthResult(
                    component="data_source",
                    status=HealthStatus[status.upper()],
                    duration_seconds=0,
                ),
            ],
            observed,
        )
        record_gold_observation(False, 0)
        assert result.checked_at == observed
        saved = run_observations()
        assert saved["Provider"]["verdict"] == verdict
        assert saved["Provider"]["facts"]["observed_at"] == observed.isoformat()
        assert saved["Data Validation"]["facts"] == {"valid": False, "records": 0}
    finally:
        reset_run_observations(token)


@pytest.mark.parametrize(
    "pipeline",
    [
        ".*",
        "All",
        "$__all",
        "*",
        "{unknown,chembl_activity}",
        "unknown,chembl_activity",
    ],
)
def test_all_pipeline_selector_resolves_exact_saved_run(tmp_path, pipeline):
    persist(tmp_path)
    result = load_selected_run_status(pipeline=pipeline, run_id="run-a", root=tmp_path)
    assert result["pipeline"] == "chembl_activity"
    assert result["verdict"] == "OK"
    assert {row["pipeline"] for row in result["domains"]} == {"chembl_activity"}


def test_all_pipeline_selector_rejects_ambiguous_identity(tmp_path):
    persist(tmp_path)
    other = report()
    other.identity["pipeline_name"] = "pubmed_publication"
    persist(tmp_path, other)
    result = load_selected_run_status(pipeline=".*", run_id="run-a", root=tmp_path)
    assert result["reason"] == "run_id_ambiguous"
    assert result["verdict"] == "ERROR"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), object(), None])
def test_snapshot_verifier_returns_false_for_malformed_evidence(bad):
    snapshot = build_snapshot(report().to_dict())
    snapshot["evidence"] = bad
    assert verify_snapshot(snapshot) is False
    snapshot["evidence"] = {"nested": bad}
    assert verify_snapshot(snapshot) is False


def test_skip_gold_is_versioned_without_invalidating_old_rules():
    from bioetl.domain.run_reports.selected_status import assess_report, evidence_digest

    payload = report().to_dict()
    payload["io"] = {"skip_gold": True}
    payload["observations"].pop("Data Validation")
    legacy = {
        "schema_version": "selected_run_snapshot_v1",
        "evidence": payload,
        "assessment": assess_report(payload, rules_version="selected-run-v1"),
    }
    legacy["revision"] = evidence_digest(legacy)
    current = build_snapshot(payload)
    assert verify_snapshot(legacy) and verify_snapshot(current)
    assert legacy["assessment"]["domains"][-1]["verdict"] == "INCOMPLETE"
    assert current["assessment"]["domains"][-1]["verdict"] == "N/A"
    assert current["assessment"]["rules_version"] == "selected-run-v2"
    assert current["revision"] != legacy["revision"]


async def test_active_workflow_in_all_scope_retains_exact_context(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    run_id = "00000000-0000-0000-0000-000000000001"
    host = MagicMock()
    host._read_required_param.side_effect = lambda q, key: q[key]
    host._read_optional_param.side_effect = lambda q, key: q.get(key)
    host._forensic_endpoint_limiter = asyncio.Semaphore(2)
    host._send_payload_response = AsyncMock()
    host._run_manifest_port.get_by_run_id.return_value = SimpleNamespace(
        pipeline_name="chembl_activity",
        manifest_id="m",
        workflow_name="workflow-a",
        run_type=SimpleNamespace(value="incremental"),
    )
    host._run_ledger_port.list_entries_by_run_id.return_value = [
        SimpleNamespace(
            manifest_id="m",
            event_type="run_started",
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    ]
    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops._effective_root", lambda root: tmp_path
    )
    query = {"pipeline": ".*", "run_id": run_id, "workflow": "workflow-a"}
    await handle_selected_run_status(host, MagicMock(), query)
    result = host._send_payload_response.call_args.args[2]
    assert result["execution_state"] == "RUNNING"
    assert result["workflow_id"] == "workflow-a"
    assert result["pipeline"] == "chembl_activity"
    assert "trust" not in result["summary"][0]
    assert all(row["pipeline"] == "chembl_activity" for row in result["domains"])


def test_unavailable_response_keeps_status_dimensions(tmp_path):
    value = read(tmp_path)
    assert value["execution_state"] == "UNKNOWN"
    assert value["checks_verdict"] == "UNKNOWN"
    assert value["evidence_completeness"] == "INCOMPLETE"
    assert value["evidence_availability"] == "run_not_found"
    assert value["replay_readiness_now"] == "NOT EVALUATED"


def test_archive_rejects_valid_revision_from_a_neighbour(tmp_path):
    from types import SimpleNamespace
    from bioetl.infrastructure.control_plane.archive_run_reports import (
        selected_report_sources,
    )

    path = persist(tmp_path).json_path
    other = build_snapshot(report("other-run").to_dict())
    revision = path.parent / "status-revisions" / (other["revision"] + ".json")
    revision.write_text(json.dumps(other))
    manifest = SimpleNamespace(run_id="run-a", pipeline_name="chembl_activity")
    with pytest.raises(ValueError, match="archive_revision_identity_mismatch"):
        selected_report_sources(tmp_path, manifest)


def test_workflow_parent_is_not_committed_before_invalid_child_is_repaired(tmp_path):
    from bioetl.application.services.run_reports.writer import write_workflow_run_report
    from bioetl.domain.run_reports.models import WorkflowRunReport, WorkflowExecutionRow

    child = report()
    child.identity["workflow_run_id"] = "workflow-a"
    path = persist(tmp_path, child).json_path
    path.write_text("[]")
    workflow = WorkflowRunReport(
        identity={
            "workflow_name": "wf",
            "workflow_run_id": "workflow-a",
            "status": "success",
        },
        plan_steps=(),
        totals={},
        execution=(
            WorkflowExecutionRow(
                step_id="s",
                status="success",
                records_extracted=1,
                pipeline_name="chembl_activity",
                pipeline_run_id="run-a",
            ),
        ),
    )
    store = FileRunReportStoreAdapter()
    with pytest.raises(ValueError, match="workflow_child_report_corrupt"):
        write_workflow_run_report(workflow, root=tmp_path, store=store)
    assert not list((tmp_path / "workflow").rglob("workflow-run-report.json"))
    persist(tmp_path, child)
    first = write_workflow_run_report(workflow, root=tmp_path, store=store)
    committed = first.json_path.read_bytes()
    write_workflow_run_report(workflow, root=tmp_path, store=store)
    assert first.json_path.read_bytes() == committed
    assert read(tmp_path)["domains"][2]["verdict"] == "OK"


def test_active_run_rejects_naive_ledger_timestamp():
    from types import SimpleNamespace
    from bioetl.interfaces.http._selected_run_live import active_run_diagnostics

    host = MagicMock()
    host._run_manifest_port.get_by_run_id.return_value = SimpleNamespace(
        pipeline_name="chembl_activity", manifest_id="m"
    )
    host._run_ledger_port.list_entries_by_run_id.return_value = [
        SimpleNamespace(manifest_id="m", occurred_at=datetime(2026, 1, 1)),
        SimpleNamespace(manifest_id="m", occurred_at=datetime(2026, 1, 1, tzinfo=UTC)),
    ]
    with pytest.raises(ValueError, match="ledger_timestamp_timezone_missing"):
        active_run_diagnostics(
            host, "chembl_activity", "00000000-0000-0000-0000-000000000001"
        )


@pytest.mark.parametrize("failure,expected", [("schema", "ERROR"), ("io", None)])
async def test_delegated_gold_rejection_distinguishes_storage_failure(
    failure, expected
):
    from bioetl.application.services.run_reports.observations import (
        bind_run_observations,
        reset_run_observations,
        run_observations,
        observe_gold_write,
    )
    from bioetl.domain.types.gold_contracts_rejects import (
        GoldContractValidationError,
        build_gold_contract_reject_reason,
    )

    async def write():
        if failure == "schema":
            raise GoldContractValidationError(
                build_gold_contract_reject_reason(
                    reason_code="gold_contract_schema_failure",
                    message="schema rejected",
                )
            )
        raise OSError("disk unavailable")

    token = bind_run_observations()
    try:
        with pytest.raises((GoldContractValidationError, OSError)):
            await observe_gold_write(write(), 1)
        observation = run_observations().get("Data Validation")
        assert (observation["verdict"] if observation else None) == expected
    finally:
        reset_run_observations(token)


@pytest.mark.parametrize(
    "pipeline", ["{unknown,pubmed_publication}", "unknown,pubmed_publication"]
)
def test_pipeline_list_does_not_retain_foreign_run(tmp_path, pipeline):
    persist(tmp_path)
    result = load_selected_run_status(pipeline=pipeline, run_id="run-a", root=tmp_path)
    assert result["reason"] == "run_not_found"


def test_pipeline_list_rejects_ambiguous_run(tmp_path):
    persist(tmp_path)
    other = report()
    other.identity["pipeline_name"] = "pubmed_publication"
    persist(tmp_path, other)
    result = load_selected_run_status(
        pipeline="{chembl_activity,pubmed_publication}", run_id="run-a", root=tmp_path
    )
    assert result["reason"] == "run_id_ambiguous"


@pytest.mark.parametrize("location", ["report", "revision"])
def test_archive_rejects_replay_evidence_from_previous_manifest(tmp_path, location):
    from types import SimpleNamespace
    from bioetl.infrastructure.control_plane.archive_run_reports import (
        selected_report_sources,
    )

    current = report()
    current.identity["manifest_id"] = "current-manifest"
    path = persist(tmp_path, current).json_path
    manifest = SimpleNamespace(
        run_id="run-a", pipeline_name="chembl_activity", manifest_id="current-manifest"
    )
    assert selected_report_sources(tmp_path, manifest)
    previous = report()
    previous.identity["manifest_id"] = "previous-manifest"
    if location == "report":
        persist(tmp_path, previous)
    else:
        old = build_snapshot(previous.to_dict())
        (path.parent / "status-revisions" / (old["revision"] + ".json")).write_text(
            json.dumps(old), encoding="utf-8"
        )
    with pytest.raises(ValueError, match="archive_.*identity_mismatch"):
        selected_report_sources(tmp_path, manifest)


@pytest.mark.parametrize("reason", [None, "status_downgrade", "exception"])
def test_provider_observation_preserves_probe_fallback(reason):
    from bioetl.application.services.run_reports.observations import (
        observed_health_report,
    )
    from bioetl.domain.types import ComponentHealthResult, HealthStatus

    token = bind_run_observations()
    try:
        observed_health_report(
            [
                ComponentHealthResult(
                    component="data_source",
                    status=HealthStatus.DEGRADED,
                    duration_seconds=0,
                    probe_fallback_reason=reason,
                )
            ],
            datetime(2026, 1, 1, tzinfo=UTC),
        )
        provider = run_observations()["Provider"]
        assert provider["verdict"] == "WARN"
        assert provider["facts"]["probe_fallback_reason"] == reason
    finally:
        reset_run_observations(token)


def test_completion_capture_failure_is_recorded() -> None:
    from types import SimpleNamespace

    from bioetl.application.services.run_reports.control_plane_snapshot import (
        capture_run_completion,
    )

    def fail(*_args):
        raise RuntimeError("control plane unavailable")

    token = bind_run_observations()
    try:
        capture_run_completion(
            fail,
            SimpleNamespace(
                pipeline_name="chembl_activity",
                run_id="run-a",
                completed_at=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            None,
        )
        assert run_observations()["Control Plane"]["reason"] == (
            "completion_assessment_failed"
        )
    finally:
        reset_run_observations(token)


def test_dq_observation_returns_original_result() -> None:
    from types import SimpleNamespace

    from bioetl.application.services.run_reports.observations import (
        record_dq_observation,
    )

    result = SimpleNamespace(
        status=SimpleNamespace(value="warning"),
        error_rate=0.25,
        has_critical=False,
        rule_outcomes_count=2,
    )
    token = bind_run_observations()
    try:
        assert record_dq_observation(result) is result
        assert run_observations()["Data Quality"]["verdict"] == "WARN"
    finally:
        reset_run_observations(token)


def test_publish_snapshot_rejects_revision_content_conflict(tmp_path: Path) -> None:
    from bioetl.application.services.run_reports.snapshots import publish_snapshot

    store = FileRunReportStoreAdapter()
    path = tmp_path / "pipeline-run-report.json"
    payload = publish_snapshot(report().to_dict(), path, store=store)
    revision = payload["selected_run_snapshot"]["revision"]
    revision_path = path.parent / "status-revisions" / f"{revision}.json"
    revision_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="revision conflict"):
        publish_snapshot(report().to_dict(), path, store=store)


def test_workflow_child_validation_rejects_path_and_corrupt_observations(
    tmp_path: Path,
) -> None:
    from bioetl.application.services.run_reports.workflow_observations import (
        _child_path,
        finalize_workflow_children,
    )
    from bioetl.domain.run_reports.models import WorkflowExecutionRow, WorkflowRunReport

    invalid = WorkflowExecutionRow(
        step_id="invalid",
        status="success",
        records_extracted=0,
        pipeline_name="../escape",
        pipeline_run_id="run-a",
    )
    with pytest.raises(ValueError, match="workflow_child_identity_invalid"):
        _child_path(tmp_path, invalid)

    child = report()
    child.identity["workflow_run_id"] = "workflow-a"
    persisted = persist(tmp_path, child)
    payload = json.loads(persisted.json_path.read_text(encoding="utf-8"))
    payload.pop("selected_run_snapshot")
    payload["observations"] = []
    snapshot = build_snapshot(payload)
    payload["selected_run_snapshot"] = snapshot
    revision_path = (
        persisted.json_path.parent / "status-revisions" / f"{snapshot['revision']}.json"
    )
    revision_path.write_text(json.dumps(snapshot), encoding="utf-8")
    persisted.json_path.write_text(json.dumps(payload), encoding="utf-8")
    row = WorkflowExecutionRow(
        step_id="step-a",
        status="success",
        records_extracted=1,
        pipeline_name="chembl_activity",
        pipeline_run_id="run-a",
    )
    workflow = WorkflowRunReport(
        identity={"workflow_run_id": "workflow-a", "status": "success"},
        plan_steps=(),
        totals={},
        execution=(row,),
    )
    with pytest.raises(ValueError, match="workflow_child_observations_corrupt"):
        finalize_workflow_children(
            workflow, root=tmp_path, store=FileRunReportStoreAdapter()
        )

    missing = replace(row, pipeline_run_id="missing")
    finalize_workflow_children(
        replace(workflow, execution=(missing,)),
        root=tmp_path,
        store=FileRunReportStoreAdapter(),
    )


def test_selected_status_rejects_invalid_observation_and_rules() -> None:
    from bioetl.domain.run_reports.selected_status import assess_report

    value = report().to_dict()
    value["observations"]["Provider"]["verdict"] = "SURPRISE"
    assessed = assess_report(value)
    provider = next(row for row in assessed["domains"] if row["domain"] == "Provider")
    assert provider["verdict"] == "UNKNOWN"
    with pytest.raises(ValueError, match="assessment_rules_unsupported"):
        assess_report(value, rules_version="future")


def test_archive_report_source_empty_legacy_missing_and_containment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from bioetl.infrastructure.control_plane.archive_run_reports import (
        selected_report_sources,
    )

    manifest = SimpleNamespace(run_id="run-a", pipeline_name="chembl_activity")
    assert selected_report_sources(tmp_path, manifest) == {}

    path = persist(tmp_path).json_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("selected_run_snapshot")
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert list(selected_report_sources(tmp_path, manifest).values()) == [path]

    original_is_symlink = Path.is_symlink
    monkeypatch.setattr(
        Path,
        "is_symlink",
        lambda candidate: candidate == path or original_is_symlink(candidate),
    )
    with pytest.raises(ValueError, match="archive_report_symlink_rejected"):
        selected_report_sources(tmp_path, manifest)

    escaped = SimpleNamespace(run_id="run-a", pipeline_name="../..")
    with pytest.raises(ValueError, match="archive_report_outside_root"):
        selected_report_sources(tmp_path, escaped)


def test_scope_mismatch_and_selected_status_defensive_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bioetl.interfaces.http._selected_run_live import scope_matches
    from bioetl.interfaces.http import selected_run_status as selected

    assert not scope_matches(
        {"run_type": "backfill", "workflow_id": "wf-a"},
        {"run_type": "incremental", "workflow": "wf-a"},
    )
    monkeypatch.setattr(
        selected.run_report_ops, "_safe_segment", lambda _value: "other"
    )
    with pytest.raises(ValueError, match="invalid_run_id"):
        selected._selected_pipeline(".*", "../bad", tmp_path)
    monkeypatch.undo()

    path = persist(tmp_path).json_path
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("selected_run_snapshot")
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert read(tmp_path)["verdict"] == "INCOMPLETE"

    persist(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["identity"]["status"] = "failed"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert read(tmp_path)["evidence_availability"] == "evidence_corrupt"

    persist(tmp_path)
    original_resolve = Path.resolve

    def escaped_revision(candidate: Path, *args, **kwargs):
        if candidate.parent.name == "status-revisions":
            return tmp_path.parent / candidate.name
        return original_resolve(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", escaped_revision)
    assert read(tmp_path)["evidence_availability"] == "evidence_corrupt"


async def test_selected_status_handler_covers_selector_and_request_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bioetl.interfaces.http import selected_run_status as selected

    persist(tmp_path)
    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops._effective_root", lambda root: tmp_path
    )
    host = MagicMock()
    host._read_required_param.side_effect = lambda query, key: query[key]
    host._read_optional_param.side_effect = lambda query, key: query.get(key)
    host._forensic_endpoint_limiter = asyncio.Semaphore(1)
    host._send_payload_response = AsyncMock()
    monkeypatch.setattr(selected, "scope_matches", lambda *_args: False)
    await handle_selected_run_status(
        host,
        MagicMock(),
        {"pipeline": "chembl_activity", "run_id": "run-a"},
    )
    assert host._send_payload_response.call_args.args[2]["reason"] == (
        "selector_context_mismatch"
    )

    async def fail(**_kwargs):
        raise ValueError("broken")

    monkeypatch.setattr(selected, "run_bounded_forensic_operation", fail)
    await handle_selected_run_status(
        host,
        MagicMock(),
        {"pipeline": "chembl_activity", "run_id": "run-a"},
    )
    assert host._send_payload_response.call_args.args[2]["reason"] == "request_failed"


def test_selection_presentation_keeps_canonical_domains_and_one_action():
    from bioetl.interfaces.http.selected_run_status import unavailable_status

    payload = unavailable_status(".*", "-", "SELECT RUN", "selection_required")
    assert len(payload["domains"]) == 6
    rows = payload["presentation_domains"]
    assert len(rows) == 1
    assert rows[0]["verdict"] == "SELECT RUN"
    assert (
        rows[0]["action_path"] == "d/bioetl-run-explorer-v1/0-run-explorer?var-run_id=-"
    )


def test_error_presentation_never_collapses_into_selection_or_healthy_empty():
    from bioetl.interfaces.http.selected_run_status import unavailable_status

    payload = unavailable_status(
        "chembl_activity", "run-1", "QUERY ERROR", "evidence_read_failed"
    )
    assert len(payload["presentation_domains"]) == 6
    assert all(
        row["verdict"] == "QUERY ERROR" for row in payload["presentation_domains"]
    )
    assert all(
        "pipeline=chembl_activity" in row["action_path"]
        for row in payload["presentation_domains"]
    )


def test_selection_presentation_does_not_imply_failed_execution():
    from bioetl.interfaces.http.selected_run_status import unavailable_status

    payload = unavailable_status(".*", "-", "SELECT RUN", "selection_required")
    assert payload["summary"][0]["execution_state"] == "UNKNOWN"
    assert payload["presentation_summary"][0]["execution_state"] == "SELECT RUN"
    assert payload["presentation_summary"][0]["pipeline"] == "No run selected"
    assert payload["presentation_trust"][0]["processing_status"] == "SELECT RUN"


def test_selection_presentation_retains_summary_mirror_fields():
    from bioetl.interfaces.http import selected_run_status

    payload = selected_run_status.unavailable_status(
        ".*", "-", "SELECT RUN", "run_not_selected"
    )
    row = payload["presentation_domains"][0]
    assert row["execution_state"] == "SELECT RUN"
    assert row["run_verdict"] == "SELECT RUN"
    assert row["evidence_completeness"] == "SELECT RUN"
    assert row["rules_version"]
