"""Behavioral coverage for residual interface guard and adapter branches."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.interfaces.cli.commands.domains.health import failure_handling
from bioetl.interfaces.cli.commands.domains.health import server_integration
from bioetl.interfaces.cli.commands.domains.quarantine import server_backend
from bioetl.interfaces.cli.commands.domains.run import runtime_helpers
from bioetl.interfaces.http import _control_plane_selector_payloads as selector_payloads
from bioetl.interfaces.http import _health_server_checkpoint_freshness as freshness
from bioetl.interfaces.http import (
    _health_server_checkpoint_freshness_payloads as freshness_payloads,
)
from bioetl.interfaces.http import (
    _health_server_control_plane_metrics_refresh as metrics_refresh,
)
from bioetl.interfaces.http import _processed_records_http
from bioetl.interfaces.http.control_plane_identity import checkpoint
from bioetl.interfaces.http.control_plane_identity.types import AnchorSpec


pytestmark = pytest.mark.unit


def test_run_id_selector_skips_empty_values() -> None:
    now = datetime(2026, 9, 16, tzinfo=UTC)
    records = (
        SimpleNamespace(started_at=now, manifest_id="manifest-empty", run_id=""),
        SimpleNamespace(started_at=now, manifest_id="manifest-1", run_id="run-1"),
    )

    assert selector_payloads._started_at_ordered_values(
        records,
        lambda record: record.run_id,
    ) == ["run-1"]


@pytest.mark.parametrize(
    "raw_value",
    [object(), "not-a-number", float("inf"), float("nan")],
)
def test_checkpoint_timestamp_rejects_invalid_or_nonfinite_values(
    raw_value: object,
) -> None:
    assert (
        freshness_payloads.extract_checkpoint_saved_at_epoch_seconds(
            {"checkpoint_saved_at_epoch_seconds": raw_value}
        )
        is None
    )


def test_checkpoint_optional_text_normalizes_blank_value() -> None:
    assert freshness_payloads.optional_text("  ") is None


@pytest.mark.asyncio
async def test_checkpoint_context_rejects_untyped_identity_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    host = SimpleNamespace(
        _run_manifest_port=object(),
        _checkpoint_port=object(),
    )
    monkeypatch.setattr(
        freshness,
        "resolve_control_plane_identity_scope",
        lambda _host, _query: object(),
    )

    with pytest.raises(TypeError, match="expected _IdentityScope"):
        await freshness._load_checkpoint_freshness_context(
            host,
            object(),
            {"pipeline": "chembl_activity"},
        )


@pytest.mark.asyncio
async def test_control_plane_metrics_refresh_reports_success_and_typed_failure() -> (
    None
):
    successful = SimpleNamespace(refresh=lambda: "refreshed")

    def _fail() -> None:
        raise ValueError("invalid evidence")

    failing = SimpleNamespace(refresh=_fail)

    assert await metrics_refresh.refresh_control_plane_metrics(successful)
    assert not await metrics_refresh.refresh_control_plane_metrics(failing)


@pytest.mark.asyncio
async def test_control_plane_metrics_stop_handles_none_and_cancels_task() -> None:
    assert await metrics_refresh.stop_control_plane_metrics_refresh(None) is None
    task = asyncio.create_task(asyncio.sleep(60))

    await metrics_refresh.stop_control_plane_metrics_refresh(task)

    assert task.cancelled()


def test_processed_records_http_uses_short_lived_opener(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = object()
    opener = Mock()
    opener.open.return_value = response
    monkeypatch.setattr(_processed_records_http, "build_opener", lambda: opener)

    assert (
        _processed_records_http.open_url(
            "http://127.0.0.1:8000/metrics",
            timeout=0.5,
        )
        is response
    )
    opener.open.assert_called_once_with(
        "http://127.0.0.1:8000/metrics",
        timeout=0.5,
    )


def test_unknown_checkpoint_status_aggregates_to_partial() -> None:
    assert checkpoint._aggregate_checkpoint_status(["UNKNOWN"]) == "PARTIAL"


def test_anchor_spec_rejects_too_many_or_duplicate_positional_fields() -> None:
    with pytest.raises(TypeError, match="takes at most 10 positional"):
        AnchorSpec("P0", *range(10))
    with pytest.raises(TypeError, match="multiple values for argument 'name'"):
        AnchorSpec("P0", "manifest_id", name="duplicate")


def test_health_failure_unknown_reason_uses_unexpected_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = object()
    policy_builder = Mock(return_value=policy)
    failure_handler = Mock()
    monkeypatch.setattr(
        failure_handling,
        "build_target_cli_boundary_policy",
        policy_builder,
    )
    monkeypatch.setattr(
        failure_handling,
        "handle_boundary_cli_failure",
        failure_handler,
    )
    error = RuntimeError("boom")

    failure_handling.handle_health_failure(
        error,
        reason_code="HEALTH_CUSTOM",
        target="control-plane",
        domain_error_title="Domain error",
        unexpected_error_title="Unexpected error",
        interrupted_message="Interrupted",
    )

    failure_handler.assert_called_once_with(
        error,
        policy=policy,
        reason_suffix="UNEXPECTED_ERROR",
    )
    assert policy_builder.call_args.kwargs["reason_prefix"] == "HEALTH_CUSTOM"


def test_quarantine_backend_forwards_explicit_data_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runner = Mock()
    monkeypatch.setattr(
        server_integration,
        "run_long_lived_health_server_command",
        runner,
    )

    server_backend.run_long_lived_quarantine_backend_command(
        host="127.0.0.1",
        port=8001,
        data_root=tmp_path,
    )

    runner.assert_called_once_with(
        host="127.0.0.1",
        port=8001,
        start_metrics=False,
        data_root=tmp_path,
    )


def test_run_runtime_helper_resolves_lazy_pipeline_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = object()
    factory = Mock(return_value=service)
    monkeypatch.setattr(
        runtime_helpers,
        "import_module",
        lambda _name: SimpleNamespace(get_pipeline_runner_service=factory),
    )
    registry = object()

    assert runtime_helpers.get_pipeline_runner_service(registry=registry) is service
    factory.assert_called_once_with(registry=registry)
