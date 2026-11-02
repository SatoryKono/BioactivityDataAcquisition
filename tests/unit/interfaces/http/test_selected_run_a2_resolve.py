"""Phase 3a §3.2 — A2 latest auto-select and empty-catalog «НЕТ ЗАПУСКОВ»."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.domain.control_plane import (
    RunManifest,
    WorkflowManifest,
    WorkflowManifestStep,
)
from bioetl.domain.types import RunID, RunType
from bioetl.interfaces.http._selected_run_a2_resolve import (
    CATALOG_UNAVAILABLE_REASON,
    NO_RUNS_REASON,
    is_unresolved_run_id,
    resolve_a2_latest_run_id,
)
from bioetl.interfaces.http.selected_run_status import handle_selected_run_status

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 8, 10, 8, 30, tzinfo=UTC)


def _run_id(index: int) -> RunID:
    return RunID(UUID(int=index))


def _manifest(
    index: int,
    *,
    pipeline: str = "chembl_assay",
    workflow: str | None = None,
    top_level_workflow: str | None = None,
) -> RunManifest:
    provider, entity = pipeline.split("_", 1)
    launch: dict[str, object] = {}
    if workflow is not None:
        launch["workflow_name"] = workflow
    return RunManifest(
        manifest_id=f"manifest-{index}",
        execution_fingerprint=f"fingerprint-{index}",
        schema_version="1.0",
        created_at=_NOW + timedelta(minutes=index),
        run_id=_run_id(index),
        run_type=RunType.INCREMENTAL,
        pipeline_name=pipeline,
        provider=provider,
        entity=entity,
        workflow_name=top_level_workflow,
        launch_context=launch,
        runtime_config={},
        resolved_config={},
    )


def _workflow(
    name: str, pipeline: str = "chembl_assay", index: int = 50
) -> WorkflowManifest:
    return WorkflowManifest(
        manifest_id=f"workflow-manifest-{index}",
        workflow_run_id=_run_id(index),
        execution_fingerprint=f"workflow-fingerprint-{index}",
        schema_version="1.0",
        created_at=_NOW,
        workflow_name=name,
        workflow_version="1",
        launch_context={},
        defaults={"run_type": "incremental"},
        selected_step_ids=(pipeline,),
        steps=(
            WorkflowManifestStep(
                step_id=pipeline,
                kind="pipeline",
                pipeline_name=pipeline,
                run_options={"run_type": "incremental"},
            ),
        ),
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, True),
        ("-", True),
        ("", True),
        ("All", True),
        ("$__all", True),
        ("11111111-1111-4111-8111-111111111111", False),
    ],
)
def test_unresolved_run_id_sentinels(value: str | None, expected: bool) -> None:
    assert is_unresolved_run_id(value) is expected


def test_resolve_latest_in_pipeline_scope() -> None:
    older = _manifest(1)
    newer = _manifest(2)
    other = _manifest(3, pipeline="chembl_activity")
    latest = resolve_a2_latest_run_id(
        manifests=(older, newer, other),
        ledger_port=None,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay"},
    )
    assert latest == str(newer.run_id)


def test_resolve_empty_scope_returns_none() -> None:
    latest = resolve_a2_latest_run_id(
        manifests=(_manifest(1, pipeline="chembl_activity"),),
        ledger_port=None,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay", "run_type": "backfill"},
    )
    assert latest is None


def _write_pipeline_report(
    root: Path,
    *,
    pipeline: str = "chembl_assay",
    run_id: str = "report-only-run",
    started_at: str = "2026-09-15T12:00:00+00:00",
    run_type: str = "incremental",
    workflow_id: str = "chembl_assay",
) -> None:
    import json

    path = root / "pipeline" / pipeline / run_id / "pipeline-run-report.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": "pipeline_run_report_v1",
                "identity": {
                    "pipeline_name": pipeline,
                    "run_id": run_id,
                    "workflow_id": workflow_id,
                    "run_type": run_type,
                    "started_at": started_at,
                    "status": "success",
                },
            }
        ),
        encoding="utf-8",
    )


def test_report_only_catalog_selects_saved_run(tmp_path: Path) -> None:
    _write_pipeline_report(tmp_path)
    latest = resolve_a2_latest_run_id(
        manifests=(),
        ledger_port=None,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay"},
        report_root=tmp_path,
    )
    assert latest == "report-only-run"


def test_newer_report_beats_older_manifest(tmp_path: Path) -> None:
    older = _manifest(1)
    _write_pipeline_report(
        tmp_path,
        run_id="report-newer",
        started_at="2026-09-15T18:00:00+00:00",
    )
    latest = resolve_a2_latest_run_id(
        manifests=(older,),
        ledger_port=None,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay"},
        report_root=tmp_path,
    )
    assert latest == "report-newer"


def test_filter_change_reselects_latest_in_new_scope() -> None:
    assay = _manifest(1, pipeline="chembl_assay")
    activity = _manifest(2, pipeline="chembl_activity")
    assert resolve_a2_latest_run_id(
        manifests=(assay, activity),
        ledger_port=None,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay"},
    ) == str(assay.run_id)
    assert resolve_a2_latest_run_id(
        manifests=(assay, activity),
        ledger_port=None,
        pipeline="chembl_activity",
        query={"pipeline": "chembl_activity"},
    ) == str(activity.run_id)


def test_declared_workflow_beats_pipeline_wide_aliases() -> None:
    """Newer chembl_core run must not win when workflow=chembl_assay is selected."""
    older_matching = _manifest(1, workflow="chembl_assay")
    newer_foreign = _manifest(2, workflow="chembl_core")
    workflows = (
        _workflow("chembl_assay", index=50),
        _workflow("chembl_core", index=51),
    )
    latest = resolve_a2_latest_run_id(
        manifests=(older_matching, newer_foreign),
        ledger_port=None,
        workflow_manifests=workflows,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay", "workflow": "chembl_assay"},
    )
    assert latest == str(older_matching.run_id)


def test_top_level_workflow_name_beats_pipeline_wide_aliases() -> None:
    """Declared membership may live on RunManifest.workflow_name, not nested ctx."""
    older_matching = _manifest(1, top_level_workflow="chembl_assay")
    newer_foreign = _manifest(2, top_level_workflow="chembl_core")
    assert older_matching.launch_context == {}
    assert newer_foreign.launch_context == {}
    workflows = (
        _workflow("chembl_assay", index=60),
        _workflow("chembl_core", index=61),
    )
    latest = resolve_a2_latest_run_id(
        manifests=(older_matching, newer_foreign),
        ledger_port=None,
        workflow_manifests=workflows,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay", "workflow": "chembl_assay"},
    )
    assert latest == str(older_matching.run_id)


def test_alias_fallback_when_run_has_no_declared_workflow() -> None:
    undeclared = _manifest(3)  # no launch_context / top-level workflow
    workflows = (_workflow("chembl_assay", index=52),)
    latest = resolve_a2_latest_run_id(
        manifests=(undeclared,),
        ledger_port=None,
        workflow_manifests=workflows,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay", "workflow": "chembl_assay"},
    )
    assert latest == str(undeclared.run_id)


def test_newer_alias_fallback_not_hidden_by_older_declared_match() -> None:
    """Declared hits and alias-fallback hits share one latest pool per workflow."""
    older_declared = _manifest(1, workflow="chembl_assay")
    newer_undeclared = _manifest(2)  # pipeline alias only
    workflows = (_workflow("chembl_assay", index=53),)
    latest = resolve_a2_latest_run_id(
        manifests=(older_declared, newer_undeclared),
        ledger_port=None,
        workflow_manifests=workflows,
        pipeline="chembl_assay",
        query={"pipeline": "chembl_assay", "workflow": "chembl_assay"},
    )
    assert latest == str(newer_undeclared.run_id)


def _host() -> MagicMock:
    import asyncio

    host = MagicMock()
    host._read_required_param.side_effect = lambda q, key: q[key]
    host._read_optional_param.side_effect = lambda q, key: q.get(key)
    host._forensic_endpoint_limiter = asyncio.Semaphore(2)
    host._run_manifest_port = MagicMock()
    host._run_ledger_port = None
    host._run_report_store = MagicMock()
    host._send_payload_response = AsyncMock()
    return host


async def test_handle_unresolved_run_id_auto_selects_latest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = str(_run_id(9))
    host = _host()
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.list_a2_catalog",
        lambda *_a, **_k: ((_manifest(9),), ()),
    )
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.resolve_a2_latest_run_id",
        lambda **_kwargs: selected,
    )

    def fake_load(**kwargs: Any) -> dict[str, object]:
        assert kwargs["run_id"] == selected
        return {
            "pipeline": "chembl_assay",
            "run_id": selected,
            "verdict": "OK",
            "execution_state": "SUCCESS",
            "reason": "checked",
        }

    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.load_selected_run_status",
        fake_load,
    )
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.scope_matches",
        lambda *_a, **_k: True,
    )
    await handle_selected_run_status(
        host, MagicMock(), {"pipeline": "chembl_assay", "run_id": "-"}
    )
    payload = host._send_payload_response.await_args.args[2]
    assert payload["run_id"] == selected
    assert payload["verdict"] == "OK"


async def test_handle_empty_catalog_emits_no_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = _host()
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.list_a2_catalog",
        lambda *_a, **_k: ((), ()),
    )
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.resolve_a2_latest_run_id",
        lambda **_kwargs: None,
    )
    await handle_selected_run_status(
        host, MagicMock(), {"pipeline": "chembl_assay", "run_id": "-"}
    )
    payload = host._send_payload_response.await_args.args[2]
    assert payload["verdict"] == "НЕТ ЗАПУСКОВ"
    assert payload["reason"] == NO_RUNS_REASON
    assert payload["presentation_summary"][0]["execution_state"] == "НЕТ ЗАПУСКОВ"


async def test_handle_missing_manifest_port_is_query_error() -> None:
    host = _host()
    host._run_manifest_port = None
    await handle_selected_run_status(
        host, MagicMock(), {"pipeline": "chembl_assay", "run_id": "-"}
    )
    payload = host._send_payload_response.await_args.args[2]
    assert payload["verdict"] == "QUERY ERROR"
    assert payload["reason"] == CATALOG_UNAVAILABLE_REASON
    assert payload["verdict"] != "НЕТ ЗАПУСКОВ"


async def test_handle_explicit_url_run_id_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    explicit = str(_run_id(42))
    host = _host()
    resolve = MagicMock(return_value=str(_run_id(1)))
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.resolve_a2_latest_run_id",
        resolve,
    )

    def fake_load(**kwargs: Any) -> dict[str, object]:
        assert kwargs["run_id"] == explicit
        return {
            "pipeline": "chembl_assay",
            "run_id": explicit,
            "verdict": "OK",
            "execution_state": "SUCCESS",
            "reason": "checked",
        }

    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.load_selected_run_status",
        fake_load,
    )
    monkeypatch.setattr(
        "bioetl.interfaces.http.selected_run_status.scope_matches",
        lambda *_a, **_k: True,
    )
    await handle_selected_run_status(
        host,
        MagicMock(),
        {"pipeline": "chembl_assay", "run_id": explicit},
    )
    resolve.assert_not_called()
    payload = host._send_payload_response.await_args.args[2]
    assert payload["run_id"] == explicit


def test_auto_selected_report_only_fills_selected_and_a2_via(tmp_path: Path) -> None:
    from bioetl.interfaces.http.control_plane_selector_context import (
        build_selector_context_payload,
    )
    from bioetl.interfaces.http._control_plane_selector_payloads import RESOLVED_VIA_A2

    _write_pipeline_report(tmp_path, run_id="report-uuid", started_at="2026-09-15T12:00:00+00:00")
    identity = {
        "pipeline_name": "chembl_assay",
        "run_id": "report-uuid",
        "workflow_id": "chembl_assay",
        "run_type": "incremental",
        "started_at": "2026-09-15T12:00:00+00:00",
        "status": "success",
    }
    payload = build_selector_context_payload(
        manifests=(),
        ledger_port=None,
        selected_pipelines=("chembl_assay",),
        auto_selected_run_id="report-uuid",
        report_selected=identity,
    )
    selected = payload["selected"]
    assert payload["resolved_via"] == RESOLVED_VIA_A2
    assert isinstance(selected, dict)
    assert selected["run_id"] == "report-uuid"
    assert selected["pipeline"] == "chembl_assay"


def test_auto_selected_manifest_keeps_a2_via_not_explicit() -> None:
    from bioetl.interfaces.http.control_plane_selector_context import (
        build_selector_context_payload,
    )
    from bioetl.interfaces.http._control_plane_selector_payloads import RESOLVED_VIA_A2

    newer = _manifest(2)
    payload = build_selector_context_payload(
        manifests=(newer,),
        ledger_port=None,
        selected_pipelines=("chembl_assay",),
        auto_selected_run_id=str(newer.run_id),
    )
    assert payload["resolved_via"] == RESOLVED_VIA_A2
    selected = payload["selected"]
    assert isinstance(selected, dict)
    assert selected["run_id"] == str(newer.run_id)


def test_explicit_selected_run_id_still_marks_selected_run_id() -> None:
    from bioetl.interfaces.http.control_plane_selector_context import (
        build_selector_context_payload,
    )

    newer = _manifest(2)
    payload = build_selector_context_payload(
        manifests=(newer,),
        ledger_port=None,
        selected_pipelines=("chembl_assay",),
        selected_run_id=str(newer.run_id),
    )
    assert payload["resolved_via"] == "selected_run_id"
    selected = payload["selected"]
    assert isinstance(selected, dict)
    assert selected["run_id"] == str(newer.run_id)


def test_a2_empty_scope_does_not_repick_via_pipeline_aliases() -> None:
    """When A2 returns None, keep empty selected — no legacy alias re-pick."""
    from bioetl.interfaces.http.control_plane_selector_context import (
        build_selector_context_payload,
    )
    from bioetl.interfaces.http._control_plane_selector_payloads import RUN_ID_NO_SELECTION

    foreign = _manifest(2, workflow="chembl_core")
    workflows = (
        _workflow("chembl_assay", index=50),
        _workflow("chembl_core", index=51),
    )
    assert (
        resolve_a2_latest_run_id(
            manifests=(foreign,),
            ledger_port=None,
            workflow_manifests=workflows,
            pipeline="chembl_assay",
            query={"pipeline": "chembl_assay", "workflow": "chembl_assay"},
        )
        is None
    )
    payload = build_selector_context_payload(
        manifests=(foreign,),
        ledger_port=None,
        workflow_manifests=workflows,
        selected_workflows=("chembl_assay",),
        selected_pipelines=("chembl_assay",),
        auto_selected_run_id=None,
        a2_consulted=True,
    )
    selected = payload["selected"]
    assert payload["resolved_via"] == "no_manifest_for_scope"
    assert isinstance(selected, dict)
    assert selected["run_id"] == RUN_ID_NO_SELECTION


def test_explicit_report_only_run_id_fills_selected_from_identity() -> None:
    from bioetl.interfaces.http.control_plane_selector_context import (
        build_selector_context_payload,
    )

    identity = {
        "pipeline_name": "chembl_assay",
        "run_id": "report-only-explicit",
        "workflow_id": "chembl_assay",
        "run_type": "incremental",
        "started_at": "2026-09-15T12:00:00+00:00",
        "status": "success",
    }
    payload = build_selector_context_payload(
        manifests=(),
        ledger_port=None,
        selected_pipelines=("chembl_assay",),
        selected_run_id="report-only-explicit",
        report_selected=identity,
    )
    selected = payload["selected"]
    assert payload["resolved_via"] == "selected_run_id"
    assert isinstance(selected, dict)
    assert selected["run_id"] == "report-only-explicit"
    assert selected["pipeline"] == "chembl_assay"


def test_a2_corrupt_report_identity_raises_for_query_error(tmp_path: Path) -> None:
    """Mismatched report identity must not look like an empty A2 catalog."""
    _write_pipeline_report(tmp_path)
    bad = (
        tmp_path
        / "pipeline"
        / "chembl_assay"
        / "report-only-run"
        / "pipeline-run-report.json"
    )
    bad.write_text(
        bad.read_text(encoding="utf-8").replace(
            '"pipeline_name": "chembl_assay"',
            '"pipeline_name": "chembl_activity"',
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="selector report"):
        resolve_a2_latest_run_id(
            manifests=(),
            ledger_port=None,
            pipeline="chembl_assay",
            query={"pipeline": "chembl_assay"},
            report_root=tmp_path,
        )


def test_a2_pipeline_all_selected_has_concrete_pipeline() -> None:
    from bioetl.interfaces.http.control_plane_selector_context import (
        build_selector_context_payload,
    )
    from bioetl.interfaces.http._control_plane_selector_payloads import RESOLVED_VIA_A2

    newer = _manifest(2, pipeline="chembl_assay")
    payload = build_selector_context_payload(
        manifests=(newer,),
        ledger_port=None,
        selected_pipelines=(),
        auto_selected_run_id=str(newer.run_id),
        a2_consulted=True,
    )
    selected = payload["selected"]
    assert payload["resolved_via"] == RESOLVED_VIA_A2
    assert isinstance(selected, dict)
    assert selected["run_id"] == str(newer.run_id)
    assert selected["pipeline"] == "chembl_assay"
