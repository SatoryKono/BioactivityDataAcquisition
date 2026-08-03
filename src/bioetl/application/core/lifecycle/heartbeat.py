"""Heartbeat management for runtime locks.

Extracted from LockRuntimeService to follow Single Responsibility Principle.
Handles background heartbeat tasks that keep locks alive.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING

from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
    from bioetl.domain.ports import LockPort, LoggerPort


class HeartbeatTask:
    """Manages background heartbeat task for lock maintenance.
    Responsibilities:
    - Start and stop background heartbeat loop
    - Send periodic heartbeats to extend lock TTL
    - Handle lock loss detection and trigger shutdown
    Attributes:
        _lock_port: Port for lock operations.
        _lock_key: Key identifying the lock.
        _owner_id: Identifier of the lock owner (RunID).
        _exclusive: Whether the lock is exclusive.
        _interval: Heartbeat interval in seconds.
        _shutdown_signal: Signal to trigger graceful shutdown.
        _logger: Logger for heartbeat messages.
        _task: Background task reference.
    """

    def __init__(
        self,
        lock_port: LockPort,
        lock_key: str,
        owner_id: RunID,
        exclusive: bool,
        interval: int,
        shutdown_signal: ShutdownSignal,
        logger: LoggerPort,
    ) -> None:
        """Initialize heartbeat task.
        Args:
            lock_port: Port for lock operations.
            lock_key: Key identifying the lock.
            owner_id: Identifier of the lock owner (RunID).
            exclusive: Whether the lock is exclusive.
            interval: Heartbeat interval in seconds.
            shutdown_signal: Signal to trigger graceful shutdown.
            logger: Logger for heartbeat messages.
        """
        self._lock_port = lock_port
        self._lock_key = lock_key
        self._owner_id = owner_id
        self._exclusive = exclusive
        self._interval = interval
        self._shutdown_signal = shutdown_signal
        self._logger = logger
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background heartbeat task.
        Performs initial heartbeat and starts background loop.
        Raises:
            PipelineShutdownError: If initial heartbeat fails.
        """
        initial_success = await self._lock_port.heartbeat(
            self._lock_key, self._owner_id, exclusive=self._exclusive
        )
        if not initial_success:
            self._logger.error("Heartbeat failed on start; shutting down")
            self._shutdown_signal.request()
            raise PipelineShutdownError("Lock lost on heartbeat start")
        self._task = asyncio.create_task(self._heartbeat_loop())

    async def stop(self) -> None:
        """Stop the background heartbeat task.
        Cancels the task and waits for completion.
        """
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    @property
    def is_running(self) -> bool:
        """Check if heartbeat task is running."""
        return self._task is not None and not self._task.done()

    async def _heartbeat_loop(self) -> None:
        """Background loop that sends periodic heartbeats.
        Raises:
            PipelineShutdownError: If lock is lost during heartbeat.
        """
        while not self._shutdown_signal.is_requested:
            await asyncio.sleep(self._interval)
            success = await self._lock_port.heartbeat(
                self._lock_key, self._owner_id, exclusive=self._exclusive
            )
            if not success:
                self._logger.error("Lost lock during execution!")
                self._shutdown_signal.request()
                raise PipelineShutdownError("Lock lost")


__all__ = ["HeartbeatTask"]
