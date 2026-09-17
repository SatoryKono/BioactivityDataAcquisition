"""Behavior coverage for remaining two-line interface residuals in #10469."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import click
import pytest

from bioetl.application.services.run_reports.query import ReportIndexEntry
from bioetl.interfaces.cli.commands import cleanup, run
from bioetl.interfaces.cli.commands import _run_manifest_historical_support as historical
from bioetl.interfaces.cli.commands.domains.maintenance import control_plane_lifecycle
from bioetl.interfaces.cli.commands.domains.shared._execution_failure_support import (
    render_failure_context,
)
from bioetl.interfaces.http import _health_server_observability_routing as observability
from bioetl.interfaces.http import _health_server_quarantine_routing as quarantine
from bioetl.interfaces.http import _report_selector_options as selector
from bioetl.interfaces.http.control_plane_identity.payload import (
    _identity_graph_status_text,
    _summary_overall_status,
)

pytestmark = pytest.mark.unit


def test_historical_helpers_reject_wrong_report_and_pack_shapes() -> None:
    assert historical._has_required_universal_exact_replay_claim(
        SimpleNamespace(governed_full_corpus_gate=())
    ) is False
    with pytest.raises(ValueError, match="JSON objects"):
        historical._coerce_universe_external_record([], pack_ref="pack.json")


@pytest.mark.asyncio
async def test_cleanup_validates_retention_and_delegates_preview(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(click.BadParameter, match="non-negative"):
        cleanup._validate_retention_days(MagicMock(), MagicMock(), True)
    expected = object()
    delegated = AsyncMock(return_value=expected)
    monkeypatch.setattr(cleanup, "preview_cleanup", delegated)
    assert await cleanup.preview_pipeline_cleanup("chembl_activity") is expected
    delegated.assert_awaited_once_with("chembl_activity")


def test_run_helpers_delegate_valid_options_and_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = object()
    service = SimpleNamespace(
        validate_start_offset=MagicMock(
            return_value=SimpleNamespace(is_valid=True, error_message=None)
        ),
        build_options=MagicMock(return_value=expected),
    )
    monkeypatch.setattr(run, "create_cli_run_orchestration_service", lambda: service)
    run.validate_options(None, "incremental", False)
    payload = MagicMock()
    assert run.build_run_options(payload) is expected


def test_control_plane_lifecycle_bootstrap_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bioetl.composition import control_plane_service_access

    expected = object()
    monkeypatch.setattr(
        control_plane_service_access,
        "bootstrap_control_plane_lifecycle_store",
        lambda: expected,
    )
    assert control_plane_lifecycle.bootstrap_control_plane_lifecycle_store() is expected


def test_failure_context_renders_empty_message_and_metadata_only() -> None:
    assert render_failure_context({"message": "plain"}) == "plain"
    assert render_failure_context({"message": "", "reason": "broken"}) == "reason=broken"


@pytest.mark.asyncio
async def test_observability_router_dispatches_selected_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    handler = AsyncMock()
    monkeypatch.setattr(observability, "handle_selected_run_status", handler)
    host = MagicMock()
    writer = MagicMock()
    await observability.dispatch_observability_request(
        host,
        writer=writer,
        path="/ops/observability/selected-run-status",
        query={"run_id": "run-1"},
    )
    handler.assert_awaited_once_with(host, writer, {"run_id": "run-1"})


@pytest.mark.asyncio
async def test_filtered_stats_maps_backend_failure_to_503() -> None:
    service = SimpleNamespace(
        get_filtered_stats=AsyncMock(side_effect=RuntimeError("offline"))
    )
    host = SimpleNamespace(
        _quarantine_service=service,
        _forensic_endpoint_limiter=asyncio.Semaphore(1),
        _read_required_param=lambda _query, _name: "chembl_activity",
        _read_optional_param=lambda _query, _name: None,
        _send_payload_response=AsyncMock(),
    )
    await quarantine.handle_filtered_stats(host, MagicMock(), {})
    args = host._send_payload_response.await_args.args
    assert args[1] == 503
    assert args[2]["reason"] == "backend_unavailable"


def test_report_selector_rejects_missing_identity_and_ignores_unknown_dimension(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    entry = ReportIndexEntry(
        kind="pipeline",
        owner="chembl_activity",
        run_id="run-1",
        json_path=tmp_path / "report.json",
        markdown_path=None,
        started_at=None,
        status=None,
        completed_at=None,
        mtime=0.0,
    )
    monkeypatch.setattr(selector, "load_pipeline_run_report_payload", lambda **_kw: {})
    with pytest.raises(ValueError, match="no identity"):
        selector._checked_identity(entry, tmp_path)
    payload = {"items": ["kept"]}
    assert selector.supplement_report_options(
        payload,
        dimension="unknown",
        response_shape="values",
        scopes={},
        root=tmp_path,
    ) is payload


def test_identity_summary_handles_diagnostic_only_gap_and_warn_status() -> None:
    assert _identity_graph_status_text([], 2, None) == "incomplete (2 gaps)"
    assert _summary_overall_status(
        [{"ui_status": "WARN"}], manifest=MagicMock()
    ) == "WARN"
