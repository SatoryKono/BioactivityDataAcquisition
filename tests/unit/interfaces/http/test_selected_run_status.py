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
    handle_selected_run_status,
    load_selected_run_status,
)

pytestmark = pytest.mark.unit


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


def persist(tmp_path, value=None, store=None):
    return write_pipeline_run_report(
        value or report(), root=tmp_path, store=store or FileRunReportStoreAdapter()
    )


def read(tmp_path, run_id="run-a"):
    return load_selected_run_status(
        pipeline="chembl_activity", run_id=run_id, root=tmp_path
    )


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
def test_active_and_unfinalized_run_do_not_expire(monkeypatch, event, expected):
    from types import SimpleNamespace
    from bioetl.interfaces.http._selected_run_live import active_run_diagnostics

    host = MagicMock()
    host._run_manifest_port.get_by_run_id.return_value = SimpleNamespace(
        pipeline_name="chembl_activity",
        manifest_id="m",
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
        host, "chembl_activity", "00000000-0000-0000-0000-000000000001"
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


async def test_late_previous_request_keeps_its_own_identity(tmp_path, monkeypatch):
    import threading

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
