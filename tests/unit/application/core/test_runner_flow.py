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
"""Focused tests for run-ledger projection helpers in runner_flow."""

from __future__ import annotations

import pytest

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.application.core import runner_flow


pytestmark = pytest.mark.unit


class _Host:
    def __init__(
        self,
        *,
        diagnostics: dict[str, object] | None,
        execution_metrics: dict[str, int] | None = None,
    ) -> None:
        self._config = SimpleNamespace(pipeline_name="chembl_activity")
        self._runtime = SimpleNamespace(run_type=SimpleNamespace(value="incremental"))
        self._context = SimpleNamespace(
            started_at=datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
        )
        self._executor = SimpleNamespace()
        self._checkpoint_manager = SimpleNamespace()
        self._services = SimpleNamespace(metrics=MagicMock())
        self._logger = MagicMock()
        self._run_ledger_service = MagicMock()
        self._execution_metrics = execution_metrics or {"records_gold": 3}
        self._execution_diagnostics = diagnostics or {}

    @property
    def execution_metrics(self) -> dict[str, int]:
        return self._execution_metrics

    @property
    def execution_diagnostics(self) -> dict[str, object]:
        return self._execution_diagnostics


def test_record_run_finished_includes_execution_diagnostics() -> None:
    host = _Host(
        diagnostics={
            "adaptive_memory": {
                "decision_count": 2,
                "min_batch_size_used": 50,
                "decision_trace": [
                    {
                        "decision_index": 1,
                        "stage": "pressure_check",
                        "old_batch_size": 1000,
                        "new_batch_size": 500,
                        "pressure_state": True,
                        "monitor_mode": "psutil",
                        "reason": "monitor_recommended_reduction",
                    }
                ],
            }
        }
    )

    runner_flow.record_run_finished(host)

    host._run_ledger_service.record_run_finished.assert_called_once_with(
        metrics_snapshot={"records_gold": 3},
        details={
            "adaptive_memory": {
                "decision_count": 2,
                "min_batch_size_used": 50,
                "decision_trace": [
                    {
                        "decision_index": 1,
                        "stage": "pressure_check",
                        "old_batch_size": 1000,
                        "new_batch_size": 500,
                        "pressure_state": True,
                        "monitor_mode": "psutil",
                        "reason": "monitor_recommended_reduction",
                    }
                ],
            }
        },
    )
    invariant_calls = [
        call
        for call in host._services.metrics.increment_counter.call_args_list
        if call.args[0] == "bioetl_record_flow_invariants_total"
    ]
    assert invariant_calls[0].args == (
        "bioetl_record_flow_invariants_total",
        1,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "invariant": "fetched_equals_bronze",
            "status": "unknown",
        },
    )
    assert invariant_calls[1].args == (
        "bioetl_record_flow_invariants_total",
        1,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "invariant": "bronze_partitioned",
            "status": "unknown",
        },
    )
    assert invariant_calls[2].args == (
        "bioetl_record_flow_invariants_total",
        1,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "invariant": "silver_gold_monotonic",
            "status": "violated",
        },
    )
    backlog_gauge_calls = [
        call
        for call in host._services.metrics.set_gauge.call_args_list
        if call.args[0] == "bioetl_stage_backlog_records"
    ]
    assert backlog_gauge_calls[0].args == (
        "bioetl_stage_backlog_records",
        0.0,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "ingestion",
        },
    )
    assert backlog_gauge_calls[1].args == (
        "bioetl_stage_backlog_records",
        0.0,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "validation",
        },
    )
    assert backlog_gauge_calls[2].args == (
        "bioetl_stage_backlog_records",
        0.0,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "output",
        },
    )
    lag_gauge_calls = [
        call
        for call in host._services.metrics.set_gauge.call_args_list
        if call.args[0] == "bioetl_stage_lag_seconds"
    ]
    assert lag_gauge_calls[0].args == (
        "bioetl_stage_lag_seconds",
        0.0,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "ingestion",
        },
    )
    assert lag_gauge_calls[1].args == (
        "bioetl_stage_lag_seconds",
        0.0,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "validation",
        },
    )
    assert lag_gauge_calls[2].args == (
        "bioetl_stage_lag_seconds",
        0.0,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "stage": "output",
        },
    )


def test_record_run_failed_omits_empty_execution_diagnostics() -> None:
    host = _Host(diagnostics=None)
    exc = RuntimeError("boom")

    runner_flow.record_run_failed(host, exc)

    host._run_ledger_service.record_run_exception.assert_called_once_with(
        error=exc,
        metrics_snapshot={"records_gold": 3},
        details=None,
    )


def test_record_run_finished_emits_passed_record_flow_invariants(
    monkeypatch,
) -> None:
    host = _Host(
        diagnostics=None,
        execution_metrics={
            "records_fetched": 10,
            "records_bronze": 10,
            "records_silver": 7,
            "records_gold": 6,
            "records_quarantined": 2,
            "records_filtered_out": 1,
        },
    )
    monkeypatch.setattr(
        runner_flow,
        "current_utc_time",
        lambda: datetime(2026, 4, 29, 12, 0, 30, tzinfo=UTC),
    )

    runner_flow.record_run_finished(host)

    invariant_statuses = [
        call.args[2]["status"]
        for call in host._services.metrics.increment_counter.call_args_list
        if call.args[0] == "bioetl_record_flow_invariants_total"
    ]
    assert invariant_statuses == ["passed", "passed", "passed", "passed"]
    backlog_values = [
        (call.args[2]["stage"], call.args[1])
        for call in host._services.metrics.set_gauge.call_args_list
        if call.args[0] == "bioetl_stage_backlog_records"
    ]
    assert backlog_values == [
        ("ingestion", 0.0),
        ("validation", 2.0),
        ("output", 1.0),
    ]
    lag_values = [
        (call.args[2]["stage"], call.args[1])
        for call in host._services.metrics.set_gauge.call_args_list
        if call.args[0] == "bioetl_stage_lag_seconds"
    ]
    assert lag_values[0] == ("ingestion", 0.0)
    assert lag_values[1] == ("validation", 30.0)
    assert lag_values[2] == ("output", 30.0)


def test_record_run_finished_emits_violated_record_flow_invariants_for_silent_loss(
    monkeypatch,
) -> None:
    host = _Host(
        diagnostics=None,
        execution_metrics={
            "records_fetched": 10,
            "records_bronze": 8,
            "records_silver": 7,
            "records_gold": 9,
            "records_quarantined": 0,
            "records_filtered_out": 0,
        },
    )
    monkeypatch.setattr(
        runner_flow,
        "current_utc_time",
        lambda: datetime(2026, 4, 29, 12, 0, 30, tzinfo=UTC),
    )

    runner_flow.record_run_finished(host)

    invariant_statuses = [
        (call.args[2]["invariant"], call.args[2]["status"])
        for call in host._services.metrics.increment_counter.call_args_list
        if call.args[0] == "bioetl_record_flow_invariants_total"
    ]
    assert invariant_statuses == [
        ("fetched_equals_bronze", "violated"),
        ("bronze_partitioned", "violated"),
        ("silver_gold_monotonic", "violated"),
        ("silver_gold_terminal_accounted", "violated"),
    ]
    backlog_values = [
        (call.args[2]["stage"], call.args[1])
        for call in host._services.metrics.set_gauge.call_args_list
        if call.args[0] == "bioetl_stage_backlog_records"
    ]
    assert backlog_values == [
        ("ingestion", 2.0),
        ("validation", 0.0),
        ("output", 0.0),
    ]


def test_record_run_finished_treats_gold_contract_exclusions_as_terminal(
    monkeypatch,
) -> None:
    host = _Host(
        diagnostics=None,
        execution_metrics={
            "records_fetched": 10_000,
            "records_bronze": 10_000,
            "records_silver": 10_000,
            "records_gold": 0,
            "records_gold_excluded_by_contract": 10_000,
            "records_quarantined": 0,
            "records_filtered_out": 0,
        },
    )
    monkeypatch.setattr(
        runner_flow,
        "current_utc_time",
        lambda: datetime(2026, 4, 29, 12, 0, 30, tzinfo=UTC),
    )

    runner_flow.record_run_finished(host)

    invariant_statuses = [
        (call.args[2]["invariant"], call.args[2]["status"])
        for call in host._services.metrics.increment_counter.call_args_list
        if call.args[0] == "bioetl_record_flow_invariants_total"
    ]
    assert invariant_statuses == [
        ("fetched_equals_bronze", "passed"),
        ("bronze_partitioned", "passed"),
        ("silver_gold_monotonic", "passed"),
        ("silver_gold_terminal_accounted", "passed"),
    ]
    backlog_values = [
        (call.args[2]["stage"], call.args[1])
        for call in host._services.metrics.set_gauge.call_args_list
        if call.args[0] == "bioetl_stage_backlog_records"
    ]
    assert backlog_values == [
        ("ingestion", 0.0),
        ("validation", 0.0),
        ("output", 0.0),
    ]
