"""Lifecycle helpers for runtime lock orchestration."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.lifecycle.shutdown import PipelineShutdownError
from bioetl.domain.ports import LoggerPort


class _HeartbeatTaskProtocol(Protocol):
    async def start(self) -> None: ...

    async def stop(self) -> None: ...


class _HeartbeatFactoryProtocol(Protocol):
    def __call__(
        self,
        *,
        lock_port: object,
        lock_key: object,
        owner_id: object,
        exclusive: object,
        interval: object,
        shutdown_signal: object,
        logger: object,
    ) -> _HeartbeatTaskProtocol: ...


class _LockContextHolderProtocol(Protocol):
    def set(self, context: object) -> None: ...

    def clear(self) -> None: ...


class _LockPortProtocol(Protocol):
    async def acquire(
        self,
        *,
        key: str,
        owner_id: object,
        ttl: object,
        wait: object,
        wait_timeout: object,
        exclusive: bool,
    ) -> FencingToken | None: ...

    async def release(
        self,
        key: str,
        owner_id: object,
        *,
        exclusive: bool,
    ) -> bool: ...


class _LockConfigProtocol(Protocol):
    lock_key: str
    lock_ttl: object
    wait_for_lock: object
    wait_timeout: object
    exclusive: bool
    heartbeat_interval: object


class _LockRuntimeHostProtocol(Protocol):
    _lock: _LockPortProtocol
    _config: _LockConfigProtocol
    _run_id: object
    _context_holder: _LockContextHolderProtocol | None
    _logger: LoggerPort
    _heartbeat_factory: _HeartbeatFactoryProtocol
    _shutdown_signal: object
    _heartbeat: _HeartbeatTaskProtocol | None
    _acquired_at: float | None
    _fencing_token: FencingToken | None

    def get_context(self) -> object | None: ...


if TYPE_CHECKING:
    from bioetl.domain.locking import FencingToken

__all__ = [
    "acquire_lock",
    "enter_lock_context",
    "release_lock",
    "start_heartbeat",
]


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
        if host._context_holder is not None:
            context = host.get_context()
            if context is not None:
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
    if host._heartbeat:
        await host._heartbeat.stop()
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
    host._heartbeat = host._heartbeat_factory(
        lock_port=host._lock,
        lock_key=host._config.lock_key,
        owner_id=host._run_id,
        exclusive=host._config.exclusive,
        interval=host._config.heartbeat_interval,
        shutdown_signal=host._shutdown_signal,
        logger=host._logger,
    )
    await host._heartbeat.start()


async def enter_lock_context(
    host: _LockRuntimeHostProtocol,
) -> _LockRuntimeHostProtocol:
    """Acquire the lock for async context-manager usage and start heartbeat."""
    token = await acquire_lock(host)
    if token is None:
        raise PipelineShutdownError(
            f"Failed to acquire lock for {host._config.lock_key}"
        )
    await start_heartbeat(host)
    return host
