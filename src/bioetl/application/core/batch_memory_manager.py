"""Memory management for adaptive batch sizing.

Extracted from BatchExecutor to reduce class size. Handles memory pressure
detection, batch size adjustment, and recovery after processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.batch_memory_decision_policy import (
    config_budget_exceeded,
    decision_reason,
    estimate_from_config,
)
from bioetl.application.core.batch_memory_decision_policy import (
    monitor_mode as resolve_monitor_mode,
)
from bioetl.application.core.batch_memory_decision_policy import (
    monitor_pressure_state as resolve_monitor_pressure_state,
)
from bioetl.application.core.batch_memory_metrics import emit_decision_metrics
from bioetl.domain.ports import MemoryDecisionTraceEntry
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.ports import LoggerPort, MemoryMonitorPort, MetricsPort


class BatchMemoryManagerService:
    """Manages adaptive batch sizing based on memory pressure."""

    _MAX_DECISION_TRACE_ENTRIES = 128

    def __init__(
        self,
        initial_batch_size: int,
        *,
        memory_monitor: MemoryMonitorPort | None = None,
        memory_config: MemoryConfig | None = None,
        logger: LoggerPort | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str | None = None,
    ) -> None:
        self._memory_monitor = memory_monitor
        self._memory_config = memory_config
        self._initial_batch_size = initial_batch_size
        self._logger = logger
        self._metrics = metrics
        self._pipeline_name = pipeline_name or "unknown"
        self.enabled = memory_monitor is not None or (
            memory_config is not None and memory_config.enable_adaptive_sizing
        )
        self.batch_size_reductions = 0
        self.min_batch_size_used = initial_batch_size
        self._decision_index = 0
        self._decision_trace: list[MemoryDecisionTraceEntry] = []

    @property
    def decision_trace(self) -> tuple[MemoryDecisionTraceEntry, ...]:
        """Return bounded adaptive-memory decisions for replay diagnostics."""
        return tuple(self._decision_trace)

    def decision_trace_dicts(self) -> tuple[JsonDict, ...]:
        """Return JSON-serializable adaptive-memory decisions."""
        return tuple(entry.to_dict() for entry in self._decision_trace)

    def get_check_interval(self) -> int:
        """Get interval for memory pressure checks."""
        if self._memory_config:
            check_interval: int = self._memory_config.check_interval_records
            return check_interval
        return 100

    def check_pressure(
        self, current_size: int, check_interval: int, records_fetched: int
    ) -> int:
        """Check memory pressure and adjust batch size if needed."""
        if not self.enabled:
            self._record_decision(
                stage="pressure_check",
                old_size=current_size,
                new_size=current_size,
                record_index=records_fetched,
                pressure_state=None,
                monitor_mode="disabled",
                reason="adaptive_sizing_disabled",
            )
            return current_size
        if records_fetched % check_interval != 0:
            return current_size
        return self._adjust(current_size, record_index=records_fetched)

    def maybe_recover(self, current_size: int) -> int:
        """Try to recover batch size after processing."""
        if not self.enabled:
            self._record_decision(
                stage="recovery",
                old_size=current_size,
                new_size=current_size,
                record_index=None,
                pressure_state=None,
                monitor_mode="disabled",
                reason="adaptive_sizing_disabled",
            )
            return current_size
        return self._try_recover(current_size, record_index=None)

    def _adjust(self, current_size: int, *, record_index: int | None) -> int:
        """Adjust batch size based on memory pressure."""
        if self._memory_monitor:
            new_size = self._memory_monitor.get_recommended_batch_size(current_size)
            reason = decision_reason(old_size=current_size, new_size=new_size)
            pressure_state = resolve_monitor_pressure_state(self._memory_monitor)
            monitor_mode = resolve_monitor_mode(self._memory_monitor)
        elif self._memory_config:
            pressure_state = config_budget_exceeded(self._memory_config, current_size)
            new_size = estimate_from_config(self._memory_config, current_size)
            reason = (
                "config_budget_exceeded"
                if new_size < current_size
                else "config_budget_ok"
            )
            monitor_mode = "config_budget"
        else:
            return current_size
        if new_size < current_size:
            self.batch_size_reductions += 1
            self.min_batch_size_used = min(self.min_batch_size_used, new_size)
            if self._logger:
                self._logger.info(
                    "Reduced batch size due to memory pressure",
                    old_size=current_size,
                    new_size=new_size,
                    total_reductions=self.batch_size_reductions,
                )
        adjusted_size: int = new_size
        self._record_decision(
            stage="pressure_check",
            old_size=current_size,
            new_size=adjusted_size,
            record_index=record_index,
            pressure_state=pressure_state,
            monitor_mode=monitor_mode,
            reason=reason,
        )
        return adjusted_size

    def _estimate_from_config(self, current_size: int) -> int:
        return estimate_from_config(self._memory_config, current_size)

    def _try_recover(self, current_size: int, *, record_index: int | None) -> int:
        """Try to recover batch size after pressure is relieved."""
        if self._memory_monitor:
            recovered_size: int = self._memory_monitor.get_recommended_batch_size(
                current_size
            )
            self._record_decision(
                stage="recovery",
                old_size=current_size,
                new_size=recovered_size,
                record_index=record_index,
                pressure_state=resolve_monitor_pressure_state(self._memory_monitor),
                monitor_mode=resolve_monitor_mode(self._memory_monitor),
                reason=decision_reason(
                    old_size=current_size,
                    new_size=recovered_size,
                ),
            )
            return recovered_size
        if current_size < self._initial_batch_size:
            recovery_size = min(
                int(current_size * 1.1),
                self._initial_batch_size,
            )
            self._record_decision(
                stage="recovery",
                old_size=current_size,
                new_size=recovery_size,
                record_index=record_index,
                pressure_state=False,
                monitor_mode="config_budget",
                reason="config_recovery_toward_initial",
            )
            return recovery_size
        self._record_decision(
            stage="recovery",
            old_size=current_size,
            new_size=current_size,
            record_index=record_index,
            pressure_state=False,
            monitor_mode="config_budget",
            reason="already_at_initial_batch_size",
        )
        return current_size

    def _record_decision(
        self,
        *,
        stage: str,
        old_size: int,
        new_size: int,
        record_index: int | None,
        pressure_state: bool | None,
        monitor_mode: str,
        reason: str,
    ) -> None:
        self._decision_index += 1
        emit_decision_metrics(
            self._metrics,
            pipeline_name=self._pipeline_name,
            stage=stage,
            old_size=old_size,
            new_size=new_size,
            pressure_state=pressure_state,
            monitor_mode=monitor_mode,
            reason=reason,
        )
        self._decision_trace.append(
            MemoryDecisionTraceEntry(
                decision_index=self._decision_index,
                record_index=record_index,
                stage=stage,
                old_batch_size=old_size,
                new_batch_size=new_size,
                adaptive_sizing_enabled=self.enabled,
                monitor_available=self._memory_monitor is not None,
                config_available=self._memory_config is not None,
                pressure_state=pressure_state,
                monitor_mode=monitor_mode,
                reason=reason,
            )
        )
        if len(self._decision_trace) > self._MAX_DECISION_TRACE_ENTRIES:
            del self._decision_trace[
                : len(self._decision_trace) - self._MAX_DECISION_TRACE_ENTRIES
            ]


__all__ = ["BatchMemoryManagerService"]
