"""Recent launch ordering and evidence semantics across pipeline scopes."""

from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
from unittest.mock import Mock
from uuid import UUID
from urllib.parse import parse_qs, urlsplit

import pytest

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.http.recent_pipeline_runs import list_recent_pipeline_runs

pytestmark = pytest.mark.unit
NOW = datetime(2026, 9, 13, tzinfo=UTC)


@pytest.fixture(autouse=True)
def healthy_report_root(monkeypatch):
    monkeypatch.setattr(
        "bioetl.interfaces.http.run_report_ops.report_root_readiness_check",
        lambda **kw: {"layout_status": "healthy", "source_identity_state": "aligned"},
    )


def _report(root: Path, pipeline: str, index: int, *, started: str | None, mtime: int):
    run_id = str(UUID(int=index))
    path = root / "pipeline" / pipeline / run_id / "pipeline-run-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "pipeline_run_report_v1",
                "identity": {
                    "run_id": run_id,
                    "pipeline_name": pipeline,
                    "started_at": started,
                    "run_type": "backfill",
                    "workflow_id": "daily",
                    "status": "success",
                },
            }
        ),
        encoding="utf-8",
    )
    os.utime(path, (mtime, mtime))
    return run_id


def _manifest(index: int, pipeline="chembl_assay"):
    return RunManifest(
        manifest_id=f"manifest-{index}",
        execution_fingerprint=f"fingerprint-{index}",
        schema_version="1.0",
        created_at=NOW + timedelta(minutes=index),
        run_id=RunID(UUID(int=index)),
        run_type=RunType.BACKFILL,
        pipeline_name=pipeline,
        provider="chembl",
        entity=pipeline.split("_", 1)[1],
        launch_context={"workflow_name": "daily"},
        runtime_config={},
        resolved_config={},
    )


def _list(root, **kwargs):
    empty_catalog = Mock()
    empty_catalog.list_all.return_value = ()
    return list_recent_pipeline_runs(
        **{
            "root": root,
            "pipeline": ".*",
            "workflow": ".*",
            "run_type": ".*",
            "selected_run_id": None,
            "limit": 10,
            "manifest_port": empty_catalog,
            "ledger_port": None,
            **kwargs,
        }
    )


@pytest.mark.parametrize("all_value", [".*", "All", "$__all", "*", None])
def test_all_ranks_start_time_before_global_limit_not_mtime(tmp_path, all_value):
    old = _report(
        tmp_path, "chembl_assay", 1, started="2026-09-10T23:00:00Z", mtime=900
    )
    new = _report(
        tmp_path, "chembl_target", 2, started="2026-09-13T00:00:00Z", mtime=100
    )
    _report(tmp_path, "chembl_assay", 3, started=None, mtime=1000)
    payload = _list(tmp_path, pipeline=all_value, limit=1)
    assert [r["run_id"] for r in payload["items"]] == [new]
    assert old != new
    assert payload["order_by"] == "started_at_desc"


def test_scope_and_selection_bind_to_row(tmp_path):
    first = _report(tmp_path, "chembl_assay", 1, started=NOW.isoformat(), mtime=1)
    _report(tmp_path, "chembl_target", 2, started=NOW.isoformat(), mtime=2)
    rows = _list(tmp_path, pipeline="chembl_assay", selected_run_id=first)["items"]
    assert len(rows) == 1
    assert rows[0]["selected"] == 1
    assert rows[0]["workflow_scope"] == "daily"
    assert _list(tmp_path, workflow="different")["items"] == []
    assert _list(tmp_path, run_type="incremental")["items"] == []


def test_started_run_without_report_and_no_false_completion(tmp_path):
    _report(tmp_path, "chembl_target", 1, started=NOW.isoformat(), mtime=900)
    manifest = _manifest(2)
    manifests, ledger = Mock(), Mock()
    manifests.list_all.return_value = (manifest,)
    ledger.list_entries_by_run_id.return_value = [
        RunLedgerEntry(
            entry_id="started",
            manifest_id=manifest.manifest_id,
            run_id=manifest.run_id,
            event_type="run_started",
            occurred_at=NOW + timedelta(hours=1),
        )
    ]
    row = _list(tmp_path, manifest_port=manifests, ledger_port=ledger)["items"][0]
    assert row["run_id"] == str(manifest.run_id)
    assert row["status"] == "running"
    assert row["completed_at"] is None
    assert row["report_state"] == "REPORT MISSING"
    assert row["started_at_source"] == "run_ledger_started_event"


def test_manifest_fallback_does_not_claim_running_or_duplicate_report(tmp_path):
    manifest = _manifest(2)
    _report(tmp_path, manifest.pipeline_name, 2, started=None, mtime=1)
    manifests = Mock()
    manifests.list_all.return_value = (manifest, _manifest(3))
    rows = _list(tmp_path, manifest_port=manifests)["items"]
    assert len(rows) == 2
    assert rows[0]["status"] == "unknown"
    assert rows[0]["completed_at"] is None
    assert rows[1]["status"] == "success"
    assert rows[1]["report_state"] == "AVAILABLE"
    assert rows[1]["started_at_source"] == "manifest_created_at_fallback"


def test_catalog_failure_is_not_valid_empty(tmp_path):
    _report(tmp_path, "chembl_assay", 1, started=NOW.isoformat(), mtime=1)
    manifests = Mock()
    manifests.list_all.side_effect = RuntimeError("catalog unavailable")
    with pytest.raises(RuntimeError, match="catalog unavailable"):
        _list(tmp_path, manifest_port=manifests)


def test_broken_report_bind_preserves_diagnostic_state(tmp_path):
    payload = _list(tmp_path)
    assert payload["index_state"] == "tree_missing"
    assert payload["items"][0]["status"] == "TREE_MISSING"


def test_terminal_catalog_event_keeps_failure_without_report(tmp_path):
    _report(tmp_path, "chembl_target", 1, started=NOW.isoformat(), mtime=1)
    manifest = _manifest(2)
    manifests, ledger = Mock(), Mock()
    manifests.list_all.return_value = (manifest,)
    ledger.list_entries_by_run_id.return_value = [
        RunLedgerEntry(
            entry_id="failed",
            manifest_id=manifest.manifest_id,
            run_id=manifest.run_id,
            event_type="run_failed",
            occurred_at=NOW + timedelta(hours=1),
            status="failed",
        )
    ]
    row = _list(tmp_path, manifest_port=manifests, ledger_port=ledger)["items"][0]
    assert row["status"] == "failed"
    assert row["completed_at"] == (NOW + timedelta(hours=1)).isoformat()
    assert row["report_state"] == "REPORT MISSING"


def test_absent_or_unreadable_catalog_is_an_error(tmp_path):
    _report(tmp_path, "chembl_assay", 1, started=NOW.isoformat(), mtime=1)
    with pytest.raises(RuntimeError, match="not configured"):
        _list(tmp_path, manifest_port=None)
    manifests = Mock()
    manifests.list_all.side_effect = OSError("unreadable")
    with pytest.raises(RuntimeError, match="could not be read"):
        _list(tmp_path, manifest_port=manifests)


def test_start_sort_normalizes_timezones_and_is_deterministic(tmp_path):
    older = _report(
        tmp_path, "chembl_assay", 1, started="2026-09-13T02:00:00+03:00", mtime=9
    )
    newer = _report(
        tmp_path, "chembl_target", 2, started="2026-09-13T00:00:00", mtime=1
    )
    rows = _list(tmp_path)["items"]
    assert [row["run_id"] for row in rows] == [newer, older]


def test_report_start_wins_over_manifest_fallback_and_missing_workflow_is_explicit(
    tmp_path,
):
    from dataclasses import replace

    manifest = replace(_manifest(2), launch_context={})
    run_id = _report(tmp_path, "chembl_assay", 2, started=NOW.isoformat(), mtime=1)
    manifests = Mock()
    manifests.list_all.return_value = (
        manifest,
        replace(_manifest(3), launch_context={}),
    )
    rows = _list(tmp_path, manifest_port=manifests)["items"]
    assert rows[0]["workflow_id"] == "—"
    assert rows[0]["workflow_scope"] == "$__all"
    report = next(row for row in rows if row["run_id"] == run_id)
    assert report["started_at"] == NOW.isoformat()
    assert report["started_at_source"] == "report_identity"


def test_completed_report_does_not_rescan_its_ledger(tmp_path):
    manifest = _manifest(2)
    _report(tmp_path, "chembl_assay", 2, started=NOW.isoformat(), mtime=1)
    manifests, ledger = Mock(), Mock()
    manifests.list_all.return_value = (manifest,)
    row = _list(tmp_path, manifest_port=manifests, ledger_port=ledger)["items"][0]
    ledger.list_entries_by_run_id.assert_not_called()
    assert row["status"] == "success"
    assert row["started_at"] == NOW.isoformat()


@pytest.mark.asyncio
async def test_http_recent_view_passes_scope_and_bounded_limit(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from bioetl.interfaces.http import _health_server_observability_routing as routing

    catalog = Mock(return_value={"items": []})
    monkeypatch.setattr(routing, "list_recent_pipeline_runs", catalog)
    host = SimpleNamespace(
        _read_optional_param=lambda query, key: query.get(key),
        _run_manifest_port=Mock(),
        _run_ledger_port=Mock(),
        _send_payload_response=AsyncMock(),
    )
    await routing.handle_pipeline_run_reports_list(
        host,
        None,
        {
            "view": "recent",
            "pipeline": ".*",
            "workflow": "daily",
            "run_type": "backfill",
            "run_id": "-",
            "limit": "1000",
        },
    )
    assert catalog.call_args.kwargs["limit"] == 100
    assert catalog.call_args.kwargs["workflow"] == "daily"
    assert catalog.call_args.kwargs["pipeline"] == ".*"
    assert catalog.call_args.kwargs["manifest_port"] is host._run_manifest_port
    host._send_payload_response.assert_awaited_once_with(None, 200, {"items": []})


def test_malformed_report_index_is_an_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "bioetl.interfaces.http.recent_pipeline_runs.list_pipeline_run_report_payloads",
        lambda **kw: {"index_state": "ok", "items": None},
    )
    with pytest.raises(RuntimeError, match="invalid items"):
        _list(tmp_path)


@pytest.mark.parametrize("markdown", [True, False])
def test_report_link_opens_exact_row_and_prefers_existing_markdown(tmp_path, markdown):
    from bioetl.interfaces.http.run_report_ops import load_pipeline_run_report_artifact

    run_id = _report(tmp_path, "chembl_target", 1, started=NOW.isoformat(), mtime=1)
    md_path = (
        tmp_path / "pipeline" / "chembl_target" / run_id / "pipeline-run-report.md"
    )
    if markdown:
        md_path.write_text(f"# Run {run_id}", encoding="utf-8")
    row = _list(tmp_path, selected_run_id=str(UUID(int=99)))["items"][0]
    parsed = urlsplit(row["report_url"])
    assert parsed.netloc == ""
    assert (
        parsed.path
        == "/api/datasources/proxy/uid/bioetl-ops-http/ops/observability/pipeline-run-report-artifact"
    )
    params = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    assert params["pipeline"] == "chembl_target"
    assert params["run_id"] == run_id
    assert params["format"] == (
        "pipeline_run_report_md" if markdown else "pipeline_run_report_json"
    )
    assert row["report_format"] == params["format"]
    assert row["report_label"] == "Open report"
    assert run_id in load_pipeline_run_report_artifact(
        pipeline=params["pipeline"],
        run_id=params["run_id"],
        artifact_format=params["format"],
        root=tmp_path,
    )
    (md_path if markdown else md_path.with_suffix(".json")).unlink()
    assert (
        load_pipeline_run_report_artifact(
            pipeline=params["pipeline"],
            run_id=params["run_id"],
            artifact_format=params["format"],
            root=tmp_path,
        )
        is None
    )


def test_report_link_rechecks_disappeared_file_and_rejects_unsafe_identity(tmp_path):
    from bioetl.interfaces.http.recent_pipeline_runs import _report_link

    run_id = _report(tmp_path, "chembl_target", 1, started=NOW.isoformat(), mtime=1)
    row = _list(tmp_path)["items"][0]
    Path(row["json_path"]).unlink()
    assert _report_link(row, tmp_path)["report_state"] == "REPORT MISSING"
    assert _report_link({**row, "pipeline": "../outside"}, tmp_path)["report_url"] == ""
    missing = _report_link({**row, "json_path": None}, tmp_path)
    assert run_id in missing["report_url"]
    assert missing["report_format"] is None
    assert missing["report_label"] == "REPORT MISSING"


def test_exact_lookup_precedes_recent_limit_and_respects_scope(tmp_path):
    for index in range(1, 13):
        _report(
            tmp_path,
            "chembl_target",
            index,
            started=(NOW + timedelta(minutes=index)).isoformat(),
            mtime=index,
        )
    oldest = str(UUID(int=1))
    assert oldest not in [row["run_id"] for row in _list(tmp_path)["items"]]
    found = _list(tmp_path, lookup_run_id=f" {oldest} ")["items"]
    assert [row["run_id"] for row in found] == [oldest]
    assert _list(tmp_path, lookup_run_id=oldest, workflow="other")["items"] == []
    assert len(_list(tmp_path, lookup_run_id=" ")["items"]) == 10


def test_elapsed_fields_use_event_evidence_only():
    from bioetl.interfaces.http.recent_pipeline_runs import _timing_fields

    row = {
        "status": "running",
        "started_at": (NOW - timedelta(seconds=60)).isoformat(),
        "last_event_at": (NOW - timedelta(seconds=10)).isoformat(),
    }
    assert _timing_fields(row, NOW) == {
        "duration_seconds": None,
        "last_event_age_seconds": 10,
    }
    row.update(status="success", completed_at=NOW.isoformat())
    assert _timing_fields(row, NOW) == {
        "duration_seconds": 60,
        "last_event_age_seconds": None,
    }
    row.update(
        status="running",
        completed_at="invalid",
        last_event_at=(NOW + timedelta(seconds=1)).isoformat(),
    )
    assert _timing_fields(row, NOW) == {
        "duration_seconds": None,
        "last_event_age_seconds": None,
    }
