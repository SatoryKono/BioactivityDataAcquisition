"""Bounded operator queries retain failure correlation and both catalogs."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.interfaces.http import selected_run_status as status
from bioetl.interfaces.http import (
    _health_server_control_plane_evidence_routing as evidence,
)
from bioetl.interfaces.http import _selected_run_report_assessment as assessment
from bioetl.interfaces.http._forensic_request_budget import ForensicEndpointUnavailable

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_selected_status_timeout_retains_request_id_for_investigation(
    monkeypatch,
):
    host = SimpleNamespace(
        _read_required_param=lambda query, name: "chembl_assay",
        _read_optional_param=lambda query, name: "run",
        _forensic_endpoint_limiter=Mock(),
        _send_payload_response=AsyncMock(),
    )
    monkeypatch.setattr(
        status,
        "run_bounded_forensic_operation",
        AsyncMock(
            side_effect=ForensicEndpointUnavailable(
                reason="deadline_exceeded", status_code=504, request_id="correlation"
            )
        ),
    )
    writer = object()
    await status.handle_selected_run_status(host, writer, {})
    args = host._send_payload_response.await_args.args
    assert args[0] is writer and args[1] == 200
    assert args[2]["request_id"] == "correlation"
    assert args[2]["reason"] == "deadline_exceeded"


@pytest.mark.asyncio
async def test_latest_complete_read_includes_workflow_and_pipeline_catalogs(
    monkeypatch,
):

    manifest, workflow = object(), object()
    host = SimpleNamespace(
        _read_required_param=lambda query, name: "chembl_assay",
        _read_scope_csv_param=lambda query, name: (
            ("incremental",) if name == "run_type" else ("workflow",)
        ),
        _read_optional_param=lambda query, name: "-",
        _is_all_scope_token=lambda value: False,
        _run_manifest_port=SimpleNamespace(list_all=Mock(return_value=(manifest,))),
        _workflow_manifest_port=SimpleNamespace(
            list_all=Mock(return_value=(workflow,))
        ),
        _control_plane_evidence_service=object(),
    )
    monkeypatch.setattr(evidence, "read_selected_run_id", lambda host, query: "-")
    build = Mock(return_value={"selected": "run"})
    monkeypatch.setattr(evidence, "build_latest_complete_run_payload", build)
    assert await evidence._latest_complete_payload(host, {}) == {"selected": "run"}
    assert build.call_args.kwargs["manifests"] == (manifest,)
    assert build.call_args.kwargs["workflow_manifests"] == (workflow,)


def test_saved_accounting_conflict_remains_visible_through_compatibility_reader():
    conflicts = assessment._accounting_conflicts(
        {"gold_vs_silver_status": "FAILING", "gold_delta": 3}, "ERROR"
    )
    assert len(conflicts) == 1
    assert "gold_vs_silver_status=FAILING" in conflicts[0] and "delta=3" in conflicts[0]
