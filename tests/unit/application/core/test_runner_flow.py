"""Focused tests for run-ledger projection helpers in runner_flow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from bioetl.application.core import runner_flow


class _Host:
    def __init__(self, *, diagnostics: dict[str, object] | None) -> None:
        self._config = SimpleNamespace()
        self._runtime = SimpleNamespace()
        self._executor = SimpleNamespace()
        self._checkpoint_manager = SimpleNamespace()
        self._logger = MagicMock()
        self._run_ledger_service = MagicMock()
        self._execution_metrics = {"records_gold": 3}
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


def test_record_run_failed_omits_empty_execution_diagnostics() -> None:
    host = _Host(diagnostics=None)
    exc = RuntimeError("boom")

    runner_flow.record_run_failed(host, exc)

    host._run_ledger_service.record_run_exception.assert_called_once_with(
        error=exc,
        metrics_snapshot={"records_gold": 3},
        details=None,
    )
