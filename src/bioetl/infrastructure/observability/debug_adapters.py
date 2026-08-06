"""Debug adapter implementations for PipelineDebugPort.

Provides two concrete adapters:
- InteractiveDebugAdapter: CLI-interactive breakpoint handling with user prompts.
- LoggingDebugAdapter: Non-interactive mode that logs snapshots to structured logger.
"""

from __future__ import annotations

__all__ = ["InteractiveDebugAdapter", "LoggingDebugAdapter"]

import json
from collections import deque
from typing import TYPE_CHECKING

from bioetl.domain.ports import (
    BreakpointHit,
    DebugAction,
    PipelineSnapshot,
    StageBreakpoint,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class InteractiveDebugAdapter:
    """CLI-interactive debugger that prompts user at breakpoints.

    Uses click.prompt for terminal interaction. Intended for local
    development and debugging sessions only.
    """

    def __init__(
        self,
        enabled_breakpoints: set[StageBreakpoint] | None = None,
        logger: LoggerPort | None = None,
        *,
        max_snapshots: int = 100,
    ) -> None:
        """Initialize interactive debugger.

        Args:
            enabled_breakpoints: Set of breakpoints to pause at.
                If None, all breakpoints are enabled.
            logger: Optional logger for structured output.
            max_snapshots: Maximum retained snapshots (bounded ring buffer).
        """
        self._enabled = enabled_breakpoints or set(StageBreakpoint)
        self._logger = logger
        self._max_snapshots = max(1, max_snapshots)
        self._snapshots: deque[PipelineSnapshot] = deque(maxlen=self._max_snapshots)

    def is_breakpoint_enabled(self, breakpoint: StageBreakpoint) -> bool:
        """Check if breakpoint is in the enabled set."""
        return breakpoint in self._enabled

    def on_breakpoint(self, hit: BreakpointHit) -> DebugAction:
        """Prompt user for action at breakpoint."""
        import click

        snapshot = hit.snapshot
        click.echo(f"\n{'=' * 60}")
        click.echo(f"  BREAKPOINT: {hit.breakpoint.value}")
        if hit.message:
            click.echo(f"  {hit.message}")
        click.echo(f"{'=' * 60}")
        click.echo(f"  Stage:        {snapshot.stage}")
        click.echo(f"  Fetched:      {snapshot.records_fetched}")
        click.echo(f"  Bronze:       {snapshot.records_bronze}")
        click.echo(f"  Silver:       {snapshot.records_silver}")
        click.echo(f"  Gold:         {snapshot.records_gold}")
        click.echo(f"  Quarantined:  {snapshot.records_quarantined}")

        if snapshot.dq_issues:
            click.echo(f"  DQ Issues:    {snapshot.dq_issues}")

        if snapshot.sample_records:
            click.echo(f"  Sample ({len(snapshot.sample_records)} records):")
            for rec in snapshot.sample_records[:3]:
                click.echo(f"    {json.dumps(rec, default=str)[:120]}")

        click.echo("")
        actions = {a.value: a for a in DebugAction}
        choices = ", ".join(actions.keys())
        choice = click.prompt(
            f"Action [{choices}]",
            type=click.Choice(list(actions.keys())),
            default=DebugAction.CONTINUE.value,
        )
        return actions[choice]

    def on_snapshot(self, snapshot: PipelineSnapshot) -> None:
        """Store snapshot and optionally log it."""
        self._snapshots.append(snapshot)
        if self._logger:
            self._logger.debug(
                "debug_snapshot",
                stage=snapshot.stage,
                records_fetched=snapshot.records_fetched,
                records_bronze=snapshot.records_bronze,
                records_silver=snapshot.records_silver,
            )


class LoggingDebugAdapter:
    """Non-interactive debugger that logs all snapshots.

    Never pauses execution. Useful for CI/automated runs where
    you want snapshot data in logs without interactivity.
    """

    def __init__(
        self,
        logger: LoggerPort,
        enabled_breakpoints: set[StageBreakpoint] | None = None,
        *,
        max_snapshots: int = 100,
    ) -> None:
        """Initialize logging debugger.

        Args:
            logger: Structured logger for snapshot output.
            enabled_breakpoints: Breakpoints to log (None = log all).
            max_snapshots: Maximum retained snapshots (bounded ring buffer).
        """
        self._logger = logger
        self._enabled = enabled_breakpoints or set(StageBreakpoint)
        self._max_snapshots = max(1, max_snapshots)
        self._snapshots: deque[PipelineSnapshot] = deque(maxlen=self._max_snapshots)

    def is_breakpoint_enabled(self, breakpoint: StageBreakpoint) -> bool:
        """Check if breakpoint should be logged."""
        return breakpoint in self._enabled

    def on_breakpoint(self, hit: BreakpointHit) -> DebugAction:
        """Log the breakpoint and auto-continue."""
        self._logger.info(
            "debug_breakpoint",
            breakpoint=hit.breakpoint.value,
            stage=hit.snapshot.stage,
            records_fetched=hit.snapshot.records_fetched,
            records_bronze=hit.snapshot.records_bronze,
            records_silver=hit.snapshot.records_silver,
            records_gold=hit.snapshot.records_gold,
            records_quarantined=hit.snapshot.records_quarantined,
            message=hit.message,
        )
        return DebugAction.CONTINUE

    def on_snapshot(self, snapshot: PipelineSnapshot) -> None:
        """Store and log snapshot."""
        self._snapshots.append(snapshot)
        self._logger.debug(
            "debug_snapshot",
            stage=snapshot.stage,
            records_fetched=snapshot.records_fetched,
        )
