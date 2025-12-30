"""Lock Manager for ETL Pipelines."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.config import LockConfig
from bioetl.application.core.heartbeat import HeartbeatTask
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.locking import LockContext, LockContextHolder
from bioetl.domain.types import RunID, RunType

if TYPE_CHECKING:
    from bioetl.application.core.checkpoint_manager import CheckpointManager
    from bioetl.domain.ports import LockPort, LoggerPort


class LockManager:
    """Manages acquiring, releasing, and maintaining distributed locks.

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
        checkpoint_manager: CheckpointManager | None = None,
        context_holder: LockContextHolder | None = None,
    ) -> None:
        """Initialize LockManager with explicit dependencies.

        Args:
            lock_port: Port for lock operations.
            run_id: Unique identifier for the run.
            config: Lock configuration bundle.
            logger: Logger instance.
            shutdown_signal: Signal for graceful shutdown.
            checkpoint_manager: Optional checkpoint manager (unused, kept for compatibility).
            context_holder: Optional holder for lock context (for writers).

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
        self._heartbeat: HeartbeatTask | None = None
        self._acquired_at: float | None = None  # monotonic timestamp when lock acquired

    @classmethod
    def create(
        cls,
        lock_port: LockPort,
        run_id: RunID,
        provider: str,
        entity_type: str,
        run_type: RunType,
        lock_ttl: int,
        wait_for_lock: bool,
        wait_timeout: int,
        heartbeat_interval: int,
        logger: LoggerPort,
        shutdown_signal: ShutdownSignal,
        checkpoint_manager: CheckpointManager | None = None,
        context_holder: LockContextHolder | None = None,
    ) -> LockManager:
        """Create a LockManager instance.

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

        Returns:
            A configured LockManager instance.

        """
        config = LockConfig.for_pipeline(
            provider=provider,
            entity_type=entity_type,
            run_type=run_type,
            lock_ttl=lock_ttl,
            wait_for_lock=wait_for_lock,
            wait_timeout=wait_timeout,
            heartbeat_interval=heartbeat_interval,
        )

        return cls(
            lock_port=lock_port,
            run_id=run_id,
            config=config,
            logger=logger,
            shutdown_signal=shutdown_signal,
            checkpoint_manager=checkpoint_manager,
            context_holder=context_holder,
        )

    async def acquire(self) -> bool:
        """Acquire the distributed lock.

        Returns:
            True if lock was acquired, False otherwise.

        """
        import time

        acquired = await self._lock.acquire(
            key=self._config.lock_key,
            owner_id=self._run_id,
            ttl=self._config.lock_ttl,
            wait=self._config.wait_for_lock,
            wait_timeout=self._config.wait_timeout,
            exclusive=self._config.exclusive,
        )
        if acquired:
            self._acquired_at = time.monotonic()
            # Update shared context holder for writers
            if self._context_holder is not None:
                self._context_holder.set(self.get_context())  # type: ignore[arg-type]
            self._logger.info(f"Lock acquired for {self._config.lock_key}")
        else:
            self._logger.error(f"Failed to acquire lock for {self._config.lock_key}")
        return acquired

    async def release(self) -> None:
        """Release the distributed lock and stop heartbeat."""
        if self._heartbeat:
            await self._heartbeat.stop()
            self._heartbeat = None

        await self._lock.release(
            self._config.lock_key, self._run_id, exclusive=self._config.exclusive
        )
        self._acquired_at = None
        # Clear shared context holder
        if self._context_holder is not None:
            self._context_holder.clear()
        self._logger.info("Lock released", extra={"stage": "cleanup"})

    def get_context(self) -> LockContext | None:
        """Get LockContext for passing to writers.

        Returns a LockContext value object that can be passed to storage
        writers for lock validation (RULES.md §3.3).

        Returns:
            LockContext if lock is held, None if not acquired.
        """
        if self._acquired_at is None:
            return None

        return LockContext(
            key=self._config.lock_key,
            owner_id=self._run_id,
            exclusive=self._config.exclusive,
            acquired_at=self._acquired_at,
        )

    async def start_heartbeat(self) -> None:
        """Start the background heartbeat task.

        Delegates to HeartbeatTask for background loop management.

        Raises:
            PipelineShutdownError: If initial heartbeat fails.

        """
        self._heartbeat = HeartbeatTask(
            lock_port=self._lock,
            lock_key=self._config.lock_key,
            owner_id=self._run_id,
            exclusive=self._config.exclusive,
            interval=self._config.heartbeat_interval,
            shutdown_signal=self._shutdown_signal,
            logger=self._logger,
        )
        await self._heartbeat.start()

    async def __aenter__(self) -> LockManager:
        """Context manager entry: acquire lock.

        Returns:
            Self instance if lock acquired.

        Raises:
            PipelineShutdownError: If lock acquisition fails.

        """
        acquired = await self.acquire()
        if not acquired:
            raise PipelineShutdownError(
                f"Failed to acquire lock for {self._config.lock_key}"
            )
        await self.start_heartbeat()
        return self

    async def validate(self) -> bool:
        """Validate that this LockManager still holds the lock.

        This is the Safety Guard: before critical operations (e.g., writes),
        call this method to verify lock ownership. This prevents split-brain
        scenarios where the lock expired but the writer continued.

        Returns:
            True if this run_id still holds the lock, False otherwise.

        Example:
            async with lock_manager:
                # Before writing to storage:
                if not await lock_manager.validate():
                    raise LockLostError(lock_key, run_id)
                await storage.write_silver(...)
        """
        return await self._lock.validate_owner(self._config.lock_key, self._run_id)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit: release lock."""
        await self.release()
