"""Pipeline debug service for interactive step-through execution.

Integrates with PipelineRunner lifecycle to capture snapshots
at each stage and handle breakpoints via the PipelineDebugPort.
"""

from __future__ import annotations

__all__ = ["PipelineDebugService"]

from copy import deepcopy
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from bioetl.domain.ports import (
    BreakpointHit,
    DebugAction,
    PipelineSnapshot,
    StageBreakpoint,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, PipelineDebugPort


class DebugAbortError(Exception):
    """Raised when user aborts pipeline from a debug breakpoint."""


def _retain_opaque(value: object, memo: dict[int, object], seen: set[int]) -> None:
    """Keep non-container objects by reference when copying supported containers."""
    if id(value) in seen:
        return
    seen.add(id(value))
    if type(value) is dict and isinstance(value, dict):
        for key, item in value.items():
            _retain_opaque(key, memo, seen)
            _retain_opaque(item, memo, seen)
    elif type(value) is list and isinstance(value, list):
        for item in value:
            _retain_opaque(item, memo, seen)
    else:
        memo[id(value)] = value


def _copy_snapshot(snapshot: PipelineSnapshot) -> PipelineSnapshot:
    memo: dict[int, object] = {}
    seen: set[int] = set()
    for value in (snapshot.dq_issues, snapshot.sample_records, snapshot.metadata):
        _retain_opaque(value, memo, seen)
    return replace(
        snapshot,
        dq_issues=deepcopy(snapshot.dq_issues, memo),
        sample_records=deepcopy(snapshot.sample_records, memo),
        metadata=deepcopy(snapshot.metadata, memo),
    )


@dataclass
class PipelineDebugService:
    """Application service coordinating pipeline debugging.

    Sits between the PipelineRunner and PipelineDebugPort to:
    - Capture snapshots at each lifecycle stage
    - Check breakpoints and delegate action to the port
    - Maintain a history of snapshots for post-mortem inspection

    Attributes:
        debug_port: Injected debug port (NoOpDebug in production).
        logger: Structured logger.
    """

    debug_port: PipelineDebugPort
    logger: LoggerPort
    _snapshots: list[PipelineSnapshot] = field(default_factory=list)

    def capture_snapshot(
        self,
        stage: str,
        *,
        records_fetched: int = 0,
        records_bronze: int = 0,
        records_silver: int = 0,
        records_gold: int = 0,
        records_quarantined: int = 0,
        dq_issues: dict[str, int] | None = None,
        sample_records: list[dict[str, object]] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> PipelineSnapshot:
        """Capture and store a pipeline state snapshot.

        Args:
            stage: Current lifecycle stage name.
            records_fetched: Total records fetched so far.
            records_bronze: Records in bronze layer.
            records_silver: Records in silver layer.
            records_gold: Records in gold layer.
            records_quarantined: Records quarantined.
            dq_issues: Data quality issue counts by category.
            sample_records: Sample records from current batch.
            metadata: Additional stage-specific metadata.

        Returns:
            The captured PipelineSnapshot.
        """
        snapshot = PipelineSnapshot(
            stage=stage,
            records_fetched=records_fetched,
            records_bronze=records_bronze,
            records_silver=records_silver,
            records_gold=records_gold,
            records_quarantined=records_quarantined,
            dq_issues=dq_issues or {},
            sample_records=sample_records or [],
            metadata=metadata or {},
        )
        self._snapshots.append(_copy_snapshot(snapshot))
        self.debug_port.on_snapshot(snapshot)
        return snapshot

    def check_breakpoint(
        self,
        breakpoint: StageBreakpoint,
        snapshot: PipelineSnapshot,
        message: str = "",
    ) -> DebugAction:
        """Check if a breakpoint should trigger and handle the action.

        Args:
            breakpoint: The stage breakpoint to check.
            snapshot: Current pipeline state.
            message: Optional human-readable context.

        Returns:
            The action taken (CONTINUE in production).

        Raises:
            DebugAbortError: If user chose to abort at the breakpoint.
        """
        if not self.debug_port.is_breakpoint_enabled(breakpoint):
            return DebugAction.CONTINUE

        hit = BreakpointHit(
            breakpoint=breakpoint,
            snapshot=snapshot,
            message=message,
        )

        self.logger.info(
            "debug_breakpoint_hit",
            breakpoint=breakpoint.value,
            stage=snapshot.stage,
            records_fetched=snapshot.records_fetched,
        )

        action = self.debug_port.on_breakpoint(hit)

        if action == DebugAction.ABORT:
            raise DebugAbortError(f"Pipeline aborted at breakpoint {breakpoint.value}")

        self.logger.debug(
            "debug_action_taken",
            breakpoint=breakpoint.value,
            action=action.value,
        )
        return action

    @property
    def snapshots(self) -> list[PipelineSnapshot]:
        """Return detached copies of the captured snapshots."""
        return [_copy_snapshot(snapshot) for snapshot in self._snapshots]

    def get_latest_snapshot(self) -> PipelineSnapshot | None:
        """Return the most recent snapshot, or None if no snapshots."""
        return _copy_snapshot(self._snapshots[-1]) if self._snapshots else None

    def clear_snapshots(self) -> None:
        """Clear snapshot history."""
        self._snapshots.clear()
