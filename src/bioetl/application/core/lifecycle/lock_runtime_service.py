"""Runtime lock lifecycle service for ETL pipelines."""

from __future__ import annotations

__all__ = ["LockRuntimeService", "LockRuntimeServiceCreateContext"]

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
        CheckpointRuntimeService,
    )
    from bioetl.domain.ports import LockPort, LoggerPort

@dataclass(frozen=True, slots=True)
class LockRuntimeServiceCreateContext:
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
    checkpoint_manager: CheckpointRuntimeService | None = None
    context_holder: LockContextHolder | None = None
    heartbeat_factory: Callable[..., HeartbeatTask] | None = None

class LockRuntimeService:
    """Manage runtime lock acquisition, release, validation, and heartbeat."""

    def __init__(
        self,
        lock_port: LockPort,
        run_id: RunID,
        config: LockConfig,
        logger: LoggerPort,
        shutdown_signal: ShutdownSignal,
        checkpoint_manager: CheckpointRuntimeService | None = None,
        context_holder: LockContextHolder | None = None,
        heartbeat_factory: Callable[..., HeartbeatTask] | None = None,
    ) -> None:
        """Initialize the runtime lock lifecycle collaborator."""
        self._lock = lock_port
        self._run_id = run_id
        self._config = config
        self._logger = logger
        self._shutdown_signal = shutdown_signal
        self._checkpoint_manager = checkpoint_manager
        self._context_holder = context_holder
        self._heartbeat_factory = heartbeat_factory or HeartbeatTask
        self._heartbeat: HeartbeatTask | None = None
        self._acquired_at: float | None = None
        self._fencing_token: FencingToken | None = None

    @classmethod
    def create(
        cls,
        request: LockRuntimeServiceCreateContext,
    ) -> LockRuntimeService:
        """Create a runtime lock collaborator from pipeline-run inputs."""
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
        """Acquire the runtime lock."""
        return await acquire_lock(self)

    async def release(self) -> None:
        """Release the runtime lock and stop heartbeat."""
        await release_lock(self)

    def get_context(self) -> LockContext | None:
        """Return the current writer-facing LockContext when held."""
        return build_lock_context(
            config=self._config,
            run_id=self._run_id,
            acquired_at=self._acquired_at,
            fencing_token=self._fencing_token,
        )

    async def start_heartbeat(self) -> None:
        """Start the background heartbeat task."""
        await start_heartbeat(self)

    async def __aenter__(self) -> LockRuntimeService:
        """Acquire the lock for async context-manager usage."""
        return await enter_lock_context(self)

    async def validate(self) -> bool:
        """Validate ownership, renewing a delayed lease before write stages."""
        owned = await validate_lock_ownership(
            lock_port=self._lock,
            config=self._config,
            run_id=self._run_id,
            fencing_token=self._fencing_token,
        )
        if not await self._lock.heartbeat(
            self._config.lock_key,
            self._run_id,
            exclusive=self._config.exclusive,
        ):
            return False
        return owned or await validate_lock_ownership(
            lock_port=self._lock,
            config=self._config,
            run_id=self._run_id,
            fencing_token=self._fencing_token,
        )

    async def __aexit__(self, *_exc_info: object) -> None:
        """Release the lock when leaving the async context manager."""
        await self.release()
