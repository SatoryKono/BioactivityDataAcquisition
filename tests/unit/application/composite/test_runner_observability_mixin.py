# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for CompositeRunnerObservabilityMixin."""

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


class _RunnerHarness(CompositeRunnerObservabilityMixin):
    """Minimal harness that provides mixin host attributes."""

    def __init__(self) -> None:
        self._config = SimpleNamespace(
            name="publication",
            merge=SimpleNamespace(
                output_silver_path="silver/composite/publication",
                output_gold_path="gold/composite/publication",
            ),
            dq=SimpleNamespace(
                soft_fail_threshold=0.10,
                hard_fail_threshold=0.30,
            ),
        )
        self._logger = MagicMock()
        self._run_id_str = "run-test-1"
        self._run_id = deterministic_uuid_from_callsite(
            "test_runner_observability_mixin"
        )
        self._runtime = SimpleNamespace(cached_bronze_date=None)
        self._started_at = datetime(2026, 4, 9, 12, 30, 0, tzinfo=UTC)
        self._dq_report_service = None
        self._quarantine_port = None
        self._metrics = None
        self._run_ledger_service = None

    def _record_with_ledger_service(self, recorder) -> None:
        if self._run_ledger_service is None:
            return
        recorder(self._run_ledger_service)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_skips_when_service_missing() -> None:
    runner = _RunnerHarness()
    merge_result = MergeResult(records_from_seed=3)

    await runner._generate_dq_reports(merge_result)

    runner._logger.debug.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_success_logs_info_and_calls_service() -> None:
    runner = _RunnerHarness()
    runner._dq_report_service = MagicMock()
    runner._dq_report_service.generate_reports = AsyncMock(return_value=None)
    merge_result = MergeResult(records_from_seed=7)

    await runner._generate_dq_reports(merge_result)

    runner._dq_report_service.generate_reports.assert_awaited_once()
    context = runner._dq_report_service.generate_reports.await_args.args[0]
    assert context.timestamp == runner._started_at
    runner._logger.info.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_prefers_cached_bronze_date_for_timestamp() -> None:
    runner = _RunnerHarness()
    runner._runtime.cached_bronze_date = "2026-04-10"
    runner._dq_report_service = MagicMock()
    runner._dq_report_service.generate_reports = AsyncMock(return_value=None)

    await runner._generate_dq_reports(MergeResult(records_from_seed=7))

    context = runner._dq_report_service.generate_reports.await_args.args[0]
    assert context.timestamp == datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_non_fatal_error_logs_warning() -> None:
    runner = _RunnerHarness()
    runner._dq_report_service = MagicMock()
    runner._dq_report_service.generate_reports = AsyncMock(
        side_effect=RuntimeError("report generation failed")
    )
    merge_result = MergeResult(records_from_seed=5)

    await runner._generate_dq_reports(merge_result)

    runner._logger.warning.assert_called_once()
    assert "dq_reports_failed" in str(runner._logger.warning.call_args.args[0])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_generate_dq_reports_bioetl_error_includes_reason_code() -> None:
    runner = _RunnerHarness()
    runner._dq_report_service = MagicMock()
    runner._dq_report_service.generate_reports = AsyncMock(
        side_effect=BioETLError("dq failure")
    )
    merge_result = MergeResult(records_from_seed=5)

    await runner._generate_dq_reports(merge_result)

    runner._logger.warning.assert_called_once()
    kwargs = runner._logger.warning.call_args.kwargs
    assert kwargs.get("reason_code") == "unexpected_bioetl_error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_skips_when_port_missing_or_payload_empty() -> None:
    runner = _RunnerHarness()

    await runner._write_cv_quarantine(MergeResult(quarantine_payloads=()))
    runner._logger.info.assert_not_called()

    runner._quarantine_port = MagicMock()
    runner._quarantine_port.write = AsyncMock(return_value=None)
    await runner._write_cv_quarantine(MergeResult(quarantine_payloads=()))
    runner._quarantine_port.write.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_writes_records_and_emits_metric() -> None:
    runner = _RunnerHarness()
    runner._quarantine_port = MagicMock()
    runner._quarantine_port.write = AsyncMock(return_value=None)
    runner._metrics = MagicMock()
    runner._run_ledger_service = MagicMock()
    payloads = (
        {"record_id": "a", "reason": "mismatch"},
        {"record_id": "b", "reason": "mismatch"},
    )

    await runner._write_cv_quarantine(MergeResult(quarantine_payloads=payloads))

    assert runner._quarantine_port.write.await_count == 2
    first_write_kwargs = runner._quarantine_port.write.await_args_list[0].kwargs
    assert first_write_kwargs["ingestion_ts"] == runner._started_at
    assert first_write_kwargs["metadata"] == {
        "artifact_policy": "occurrence_only_diagnostic",
        "replay_contract": "excluded_from_exact_replay",
        "diagnostic_scope": "composite_cross_validation_quarantine",
        "violation_kind": "cross_validation_mismatch",
        "semantic_artifact": False,
    }
    runner._run_ledger_service.record_dq_policy_applied.assert_called_once_with(
        stage="cross_validation",
        status="quarantined",
        rule_id="composite.cross_validation.quarantine",
        disposition="quarantine",
        details={
            "config_path": "cross_validation",
            "quarantine_record_count": 2,
            "artifact_policy": "occurrence_only_diagnostic",
            "replay_contract": "excluded_from_exact_replay",
            "diagnostic_scope": "composite_cross_validation_quarantine",
            "violation_kind": "cross_validation_mismatch",
            "semantic_artifact": False,
        },
    )
    runner._logger.info.assert_called_once()
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_quarantine_records_total",
        2,
        {
            "pipeline": "composite:publication",
            "reason": "cross_validation",
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_record_flow_records_total",
        2,
        {
            "pipeline": "composite:publication",
            "run_type": "composite",
            "flow_stage": "quarantined",
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_dq_dispositions_total",
        2,
        {
            "pipeline": "composite:publication",
            "stage": "validation",
            "disposition": "quarantine",
            "terminal_status": "success",
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_stage_records_total",
        2,
        {
            "pipeline": "composite:publication",
            "run_type": "composite",
            "stage": "validation",
            "outcome": "quarantined",
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_stage_records_total",
        2,
        {
            "pipeline": "composite:publication",
            "run_type": "composite",
            "stage": "silver",
            "outcome": "quarantined",
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_handles_non_fatal_and_bioetl_errors() -> None:
    runner = _RunnerHarness()
    runner._quarantine_port = MagicMock()
    runner._quarantine_port.write = AsyncMock(
        side_effect=[
            StorageError("temporary storage failure"),
            BioETLError("domain storage failure"),
            None,
        ]
    )
    runner._metrics = MagicMock()
    runner._run_ledger_service = MagicMock()
    payloads = (
        {"record_id": "a", "reason": "mismatch"},
        {"record_id": "b", "reason": "mismatch"},
        {"record_id": "c", "reason": "mismatch"},
    )

    await runner._write_cv_quarantine(MergeResult(quarantine_payloads=payloads))

    assert runner._quarantine_port.write.await_count == 3
    assert runner._logger.warning.call_count == 2
    warning_kwargs = [call.kwargs for call in runner._logger.warning.call_args_list]
    assert any(
        item.get("reason_code") == "unexpected_bioetl_error" for item in warning_kwargs
    )
    runner._run_ledger_service.record_dq_policy_applied.assert_called_once_with(
        stage="cross_validation",
        status="quarantined",
        rule_id="composite.cross_validation.quarantine",
        disposition="quarantine",
        details={
            "config_path": "cross_validation",
            "quarantine_record_count": 1,
            "artifact_policy": "occurrence_only_diagnostic",
            "replay_contract": "excluded_from_exact_replay",
            "diagnostic_scope": "composite_cross_validation_quarantine",
            "violation_kind": "cross_validation_mismatch",
            "semantic_artifact": False,
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_quarantine_records_total",
        1,
        {
            "pipeline": "composite:publication",
            "reason": "cross_validation",
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_record_flow_records_total",
        1,
        {
            "pipeline": "composite:publication",
            "run_type": "composite",
            "flow_stage": "quarantined",
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_dq_dispositions_total",
        1,
        {
            "pipeline": "composite:publication",
            "stage": "validation",
            "disposition": "quarantine",
            "terminal_status": "success",
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_stage_records_total",
        1,
        {
            "pipeline": "composite:publication",
            "run_type": "composite",
            "stage": "validation",
            "outcome": "quarantined",
        },
    )
    runner._metrics.increment_counter.assert_any_call(
        "bioetl_stage_records_total",
        1,
        {
            "pipeline": "composite:publication",
            "run_type": "composite",
            "stage": "silver",
            "outcome": "quarantined",
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_cv_quarantine_prefers_cached_bronze_date_for_timestamp() -> None:
    runner = _RunnerHarness()
    runner._runtime.cached_bronze_date = "2026-04-10"
    runner._quarantine_port = MagicMock()
    runner._quarantine_port.write = AsyncMock(return_value=None)

    await runner._write_cv_quarantine(MergeResult(quarantine_payloads=({"id": "x"},)))

    assert runner._quarantine_port.write.await_args.kwargs["ingestion_ts"] == datetime(
        2026,
        4,
        10,
        0,
        0,
        0,
        tzinfo=UTC,
    )
