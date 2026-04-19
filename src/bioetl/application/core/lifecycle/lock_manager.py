"""Lock Coordinator for ETL Pipelines."""

from __future__ import annotations

__all__ = ["LockCoordinator"]


from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.config import LockConfig
from bioetl.application.core.lifecycle.heartbeat import HeartbeatTask
from bioetl.application.core.lifecycle.lock_lifecycle import (
    acquire_lock,
    enter_lock_context,
    release_lock,
    start_heartbeat,
)
from bioetl.application.core.lifecycle.lock_runtime import (
    build_lock_config,
    build_lock_context,
    validate_lock_ownership,
)
from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.domain.locking import FencingToken, LockContext, LockContextHolder
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointManagerService,
    )
    from bioetl.domain.ports import LockPort, LoggerPort


@dataclass(frozen=True, slots=True)
class LockCoordinatorCreateRequest:
    lock_port: LockPort
    run_id: RunID
    provider: str
    entity_type: str
    run_type: RunType
    lock_ttl: int
    wait_for_lock: bool
    wait_timeout: int
    heartbeat_interval: int
    logger: LoggerPort
    shutdown_signal: ShutdownSignal
    checkpoint_manager: CheckpointManagerService | None = None
    context_holder: LockContextHolder | None = None
    heartbeat_factory: Callable[..., HeartbeatTask] | None = None


class LockCoordinator:
    """Manages acquiring, releasing, and maintaining runtime locks.

    This is an Application Service that coordinates lock lifecycle:
    - Lock acquisition and release
    - Heartbeat management (delegated to HeartbeatTask)
    - Lock context for writers

    Decomposed per REFACTOR-003:
    - LockConfig: bundles configuration parameters
    - HeartbeatTask: manages background heartbeat loop

    Attributes:
        _lock: Port for lock operations.
        _run_id: Unique identifier for the run.
        _config: Lock configuration bundle.
        _logger: Logger instance.
        _shutdown_signal: Signal for graceful shutdown.
        _context_holder: Optional holder for lock context (for writers).
        _heartbeat: Heartbeat task manager.
        _acquired_at: Monotonic timestamp when lock acquired.

    """

    def __init__(
        self,
        lock_port: LockPort,
        run_id: RunID,
        config: LockConfig,
        logger: LoggerPort,
        shutdown_signal: ShutdownSignal,
        checkpoint_manager: CheckpointManagerService | None = None,
        context_holder: LockContextHolder | None = None,
        heartbeat_factory: Callable[..., HeartbeatTask] | None = None,
    ) -> None:
        """Initialize LockCoordinator with explicit dependencies.

        Args:
            lock_port: Port for lock operations.
            run_id: Unique identifier for the run.
            config: Lock configuration bundle.
            logger: Logger instance.
            shutdown_signal: Signal for graceful shutdown.
            checkpoint_manager: Optional checkpoint manager (unused, kept for compatibility).
            context_holder: Optional holder for lock context (for writers).
            heartbeat_factory: Factory for HeartbeatTask construction.
                Allows constructor injection for heartbeat strategy/tests.

        """
        self._lock = lock_port
        self._run_id = run_id
        self._config = config
        self._logger = logger
        self._shutdown_signal = shutdown_signal
        self._checkpoint_manager = (
            checkpoint_manager  # Kept for interface compatibility
        )
        self._context_holder = context_holder
        self._heartbeat_factory = heartbeat_factory or HeartbeatTask
        self._heartbeat: HeartbeatTask | None = None
        self._acquired_at: float | None = None  # monotonic timestamp when lock acquired
        self._fencing_token: FencingToken | None = None

    @classmethod
    def create(
        cls,
        request: LockCoordinatorCreateRequest,
    ) -> LockCoordinator:
        """Create a LockCoordinator instance.

        Factory method that creates LockConfig from pipeline parameters.
        Maintains backward compatibility with existing call sites.

        Args:
            lock_port: Port for lock operations.
            run_id: Unique identifier for the run.
            provider: Name of the data provider.
            entity_type: Type of entity being processed.
            run_type: Type of run (e.g., incremental, backfill).
            lock_ttl: Time-to-live for the lock in seconds.
            wait_for_lock: Whether to wait for lock acquisition.
            wait_timeout: Maximum time to wait for lock in seconds.
            heartbeat_interval: Interval for sending heartbeats in seconds.
            logger: Logger instance.
            shutdown_signal: Signal for graceful shutdown.
            checkpoint_manager: Optional checkpoint manager.
            context_holder: Optional holder for lock context.
            heartbeat_factory: Optional factory for HeartbeatTask creation.

        Returns:
            A configured LockCoordinator instance.

        """
        config = build_lock_config(
            provider=request.provider,
            entity_type=request.entity_type,
            run_type=request.run_type,
            lock_ttl=request.lock_ttl,
            wait_for_lock=request.wait_for_lock,
            wait_timeout=request.wait_timeout,
            heartbeat_interval=request.heartbeat_interval,
        )

        return cls(
            lock_port=request.lock_port,
            run_id=request.run_id,
            config=config,
            logger=request.logger,
            shutdown_signal=request.shutdown_signal,
            checkpoint_manager=request.checkpoint_manager,
            context_holder=request.context_holder,
            heartbeat_factory=request.heartbeat_factory,
        )

    async def acquire(self) -> FencingToken | None:
        """Acquire the runtime lock.

        Returns:
            FencingToken if lock was acquired, None otherwise.

        """
        return await acquire_lock(self)

    async def release(self) -> None:
        """Release the runtime lock and stop heartbeat."""
        await release_lock(self)

    def get_context(self) -> LockContext | None:
        """Get LockContext for passing to writers.

        Returns a LockContext value object that can be passed to storage
        writers for lock validation (RULES.md §3.3).

        Returns:
            LockContext if lock is held, None if not acquired.
        """
        return build_lock_context(
            config=self._config,
            run_id=self._run_id,
            acquired_at=self._acquired_at,
            fencing_token=self._fencing_token,
        )

    async def start_heartbeat(self) -> None:
        """Start the background heartbeat task.

        Delegates to HeartbeatTask for background loop management.

        Raises:
            PipelineShutdownError: If initial heartbeat fails.

        """
        await start_heartbeat(self)

    async def __aenter__(self) -> LockCoordinator:
        """Context manager entry: acquire lock.

        Returns:
            Self instance if lock acquired.

        Raises:
            PipelineShutdownError: If lock acquisition fails.

        """
        return await enter_lock_context(self)

    async def validate(self) -> bool:
        """Validate that this LockCoordinator still holds the lock.

        This is the Safety Guard: before critical operations (e.g., writes),
        call this method to verify lock ownership via fencing token validation.
        This prevents split-brain scenarios where the lock expired but the
        writer continued.

        Returns:
            True if this run_id still holds the lock, False otherwise.

        Example:
            async with lock_coordinator:
                # Before writing to storage:
                if not await lock_coordinator.validate():
                    raise LockLostError(lock_key, run_id)
                await storage.write_silver(...)
        """
        return await validate_lock_ownership(
            lock_port=self._lock,
            config=self._config,
            run_id=self._run_id,
            fencing_token=self._fencing_token,
        )

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit: release lock."""
        await self.release()
