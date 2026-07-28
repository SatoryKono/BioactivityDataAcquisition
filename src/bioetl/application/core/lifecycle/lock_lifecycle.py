"""Lifecycle helpers for runtime lock orchestration."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Protocol

from bioetl.application.core.config import LockConfig
from bioetl.application.core.lifecycle.heartbeat import HeartbeatTask
from bioetl.application.core.lifecycle.shutdown import (
    PipelineShutdownError,
    ShutdownSignal,
)
from bioetl.domain.locking import FencingToken, LockContext, LockContextHolder
from bioetl.domain.ports import LockPort, LoggerPort
from bioetl.domain.types import RunID

__all__ = ["acquire_lock", "enter_lock_context", "release_lock", "start_heartbeat"]

class _LockRuntimeHostProtocol(Protocol):
    _lock: LockPort
    _config: LockConfig
    _run_id: RunID
    _context_holder: LockContextHolder | None
    _logger: LoggerPort
    _heartbeat_factory: Callable[..., HeartbeatTask]
    _shutdown_signal: ShutdownSignal
    _heartbeat: HeartbeatTask | None
    _acquired_at: float | None
    _fencing_token: FencingToken | None

    def get_context(self) -> LockContext | None: ...

async def acquire_lock(host: _LockRuntimeHostProtocol) -> FencingToken | None:
    """Acquire the runtime lock and update shared runtime state."""
    token = await host._lock.acquire(
        key=host._config.lock_key,
        owner_id=host._run_id,
        ttl=host._config.lock_ttl,
        wait=host._config.wait_for_lock,
        wait_timeout=host._config.wait_timeout,
        exclusive=host._config.exclusive,
    )
    if token is not None:
        host._acquired_at = time.monotonic()
        host._fencing_token = token
        context = host.get_context()
        if host._context_holder is not None and context is not None:
            host._context_holder.set(context)
        host._logger.info(
            "lock_acquired",
            lock_key=host._config.lock_key,
            run_id=str(host._run_id),
            fencing_sequence=token.sequence,
        )
    else:
        host._logger.error(
            "lock_acquisition_failed",
            lock_key=host._config.lock_key,
            run_id=str(host._run_id),
        )
    return token

async def release_lock(host: _LockRuntimeHostProtocol) -> None:
    """Release the runtime lock, stop heartbeat, and clear context state."""
    if (heartbeat := host._heartbeat) is not None:
        await heartbeat.stop()
        host._heartbeat = None

    await host._lock.release(
        host._config.lock_key,
        host._run_id,
        exclusive=host._config.exclusive,
    )
    host._acquired_at = None
    host._fencing_token = None
    if host._context_holder is not None:
        host._context_holder.clear()
    host._logger.info("Lock released", stage="cleanup")

async def start_heartbeat(host: _LockRuntimeHostProtocol) -> None:
    """Start the background heartbeat task for the acquired lock."""
    host._heartbeat = heartbeat = host._heartbeat_factory(
        lock_port=host._lock,
        lock_key=host._config.lock_key,
        owner_id=host._run_id,
        exclusive=host._config.exclusive,
        interval=host._config.heartbeat_interval,
        shutdown_signal=host._shutdown_signal,
        logger=host._logger,
    )
    await heartbeat.start()

async def enter_lock_context[LockRuntimeHostT: _LockRuntimeHostProtocol](
    host: LockRuntimeHostT,
) -> LockRuntimeHostT:
    """Acquire the lock for async context-manager usage and start heartbeat."""
    token = await acquire_lock(host)
    if token is None:
        raise PipelineShutdownError(f"Lock acquisition failed: {host._config.lock_key}")
    await start_heartbeat(host)
    return host
