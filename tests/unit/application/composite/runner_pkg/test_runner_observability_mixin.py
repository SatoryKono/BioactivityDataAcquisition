"""Unit tests for CompositeRunnerObservabilityMixin (runner_pkg sub-directory mirror).

The primary observability mixin tests live in
``tests/unit/application/composite/test_runner_observability_mixin.py``.
This module focuses on additional edge cases and the ``_metrics`` integration
path not covered elsewhere.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.composite.runner_pkg.runner_observability_mixin import (
    CompositeRunnerObservabilityMixin,
)
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.exceptions import BioETLError, StorageError


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class _ObservabilityHarness(CompositeRunnerObservabilityMixin):
    """Minimal harness providing all required mixin attributes."""

    def __init__(self) -> None:
        self._config = SimpleNamespace(
            name="test_composite",
            merge=SimpleNamespace(
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
            ),
            dq=SimpleNamespace(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
        )
        self._logger = MagicMock()
        self._run_id_str = "run-obs-test"
        self._run_id = deterministic_uuid_from_callsite(
            "test_runner_observability_mixin"
        )
        self._runtime = SimpleNamespace(cached_bronze_date=None)
        self._started_at = datetime(2026, 4, 9, 12, 30, 0, tzinfo=UTC)
        self._dq_report_service = None
        self._quarantine_port = None
        self._metrics = None


# ---------------------------------------------------------------------------
# _generate_dq_reports
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_when_service_absent_then_logs_debug_and_returns() -> (
    None
):
    harness = _ObservabilityHarness()

    await harness._generate_dq_reports(MergeResult(records_from_seed=0))

    harness._logger.debug.assert_called_once()
    harness._logger.info.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_when_service_present_then_generates_and_logs() -> (
    None
):
    harness = _ObservabilityHarness()
    harness._dq_report_service = MagicMock()
    harness._dq_report_service.generate_reports = AsyncMock(return_value=None)
    merge_result = MergeResult(records_from_seed=50)

    await harness._generate_dq_reports(merge_result)

    harness._dq_report_service.generate_reports.assert_awaited_once()
    context = harness._dq_report_service.generate_reports.await_args.args[0]
    assert context.timestamp == harness._started_at
    harness._logger.info.assert_called_once()
    info_args = harness._logger.info.call_args.args[0]
    assert "generated" in info_args


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_when_runtime_error_then_logs_warning_only() -> None:
    harness = _ObservabilityHarness()
    harness._dq_report_service = MagicMock()
    harness._dq_report_service.generate_reports = AsyncMock(
        side_effect=RuntimeError("report failure")
    )

    await harness._generate_dq_reports(MergeResult(records_from_seed=1))

    harness._logger.warning.assert_called_once()
    harness._logger.error.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_when_bioetl_error_then_includes_reason_code() -> (
    None
):
    harness = _ObservabilityHarness()
    harness._dq_report_service = MagicMock()
    harness._dq_report_service.generate_reports = AsyncMock(
        side_effect=BioETLError("domain error")
    )

    await harness._generate_dq_reports(MergeResult(records_from_seed=1))

    harness._logger.warning.assert_called_once()
    kwargs = harness._logger.warning.call_args.kwargs
    assert kwargs.get("reason_code") == "unexpected_bioetl_error"


# ---------------------------------------------------------------------------
# _write_cv_quarantine
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_when_port_absent_then_does_nothing() -> None:
    harness = _ObservabilityHarness()
    harness._quarantine_port = None

    await harness._write_cv_quarantine(MergeResult(quarantine_payloads=({"id": "x"},)))

    harness._logger.info.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_when_empty_payloads_then_does_nothing() -> None:
    harness = _ObservabilityHarness()
    harness._quarantine_port = MagicMock()
    harness._quarantine_port.write = AsyncMock()

    await harness._write_cv_quarantine(MergeResult(quarantine_payloads=()))

    harness._quarantine_port.write.assert_not_awaited()
    harness._logger.info.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_when_payloads_written_then_logs_and_emits_metric() -> (
    None
):
    harness = _ObservabilityHarness()
    harness._quarantine_port = MagicMock()
    harness._quarantine_port.write = AsyncMock(return_value=None)
    harness._metrics = MagicMock()
    payloads = ({"record_id": "r1"}, {"record_id": "r2"})

    await harness._write_cv_quarantine(MergeResult(quarantine_payloads=payloads))

    assert harness._quarantine_port.write.await_count == 2
    assert (
        harness._quarantine_port.write.await_args_list[0].kwargs["ingestion_ts"]
        == harness._started_at
    )
    harness._logger.info.assert_called_once()
    harness._metrics.increment_counter.assert_any_call(
        "bioetl_quarantine_records_total",
        2,
        {
            "pipeline": "composite:test_composite",
            "reason": "cross_validation",
        },
    )
    harness._metrics.increment_counter.assert_any_call(
        "bioetl_record_flow_records_total",
        2,
        {
            "pipeline": "composite:test_composite",
            "run_type": "composite",
            "flow_stage": "quarantined",
        },
    )
    harness._metrics.increment_counter.assert_any_call(
        "bioetl_dq_dispositions_total",
        2,
        {
            "pipeline": "composite:test_composite",
            "stage": "validation",
            "disposition": "quarantine",
            "terminal_status": "success",
        },
    )
    harness._metrics.increment_counter.assert_any_call(
        "bioetl_stage_records_total",
        2,
        {
            "pipeline": "composite:test_composite",
            "run_type": "composite",
            "stage": "validation",
            "outcome": "quarantined",
        },
    )
    harness._metrics.increment_counter.assert_any_call(
        "bioetl_stage_records_total",
        2,
        {
            "pipeline": "composite:test_composite",
            "run_type": "composite",
            "stage": "silver",
            "outcome": "quarantined",
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_when_all_writes_fail_then_no_metric_emitted() -> (
    None
):
    harness = _ObservabilityHarness()
    harness._quarantine_port = MagicMock()
    harness._quarantine_port.write = AsyncMock(
        side_effect=StorageError("storage failure")
    )
    harness._metrics = MagicMock()

    await harness._write_cv_quarantine(
        MergeResult(quarantine_payloads=({"id": "a"}, {"id": "b"}))
    )

    assert harness._logger.warning.call_count == 2
    harness._metrics.increment_counter.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_when_no_metrics_port_then_skips_metric_call() -> (
    None
):
    harness = _ObservabilityHarness()
    harness._quarantine_port = MagicMock()
    harness._quarantine_port.write = AsyncMock(return_value=None)
    harness._metrics = None

    # Must not raise even without metrics
    await harness._write_cv_quarantine(MergeResult(quarantine_payloads=({"id": "x"},)))

    assert (
        harness._quarantine_port.write.await_args.kwargs["ingestion_ts"]
        == harness._started_at
    )
    harness._logger.info.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_observability_mixin__date_for_timestamp__2e494f6b() -> None:
    harness = _ObservabilityHarness()
    harness._runtime.cached_bronze_date = "2026-04-10"
    harness._quarantine_port = MagicMock()
    harness._quarantine_port.write = AsyncMock(return_value=None)

    await harness._write_cv_quarantine(MergeResult(quarantine_payloads=({"id": "x"},)))

    assert harness._quarantine_port.write.await_args.kwargs["ingestion_ts"] == datetime(
        2026,
        4,
        10,
        0,
        0,
        0,
        tzinfo=UTC,
    )
