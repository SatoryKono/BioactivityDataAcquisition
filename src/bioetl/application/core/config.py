"""Configuration objects for application core components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.record_processor_config import (
    ContentHashPolicyByVersion,
    ContentHashPolicyGroup,
    ContentHashVersionPolicy,
    RecordProcessorConfig,
)

if TYPE_CHECKING:
    from bioetl.domain.types import RunType

__all__ = [
    "ContentHashPolicyByVersion",
    "ContentHashPolicyGroup",
    "ContentHashVersionPolicy",
    "LockConfig",
    "RecordProcessorConfig",
]

@dataclass(frozen=True, slots=True)
class LockConfig:
    """Configuration for LockRuntimeService.

    Bundles locking configuration to reduce __init__ parameters.

    Attributes:
        lock_key: The key used for runtime lock coordination.
        exclusive: Whether the lock is exclusive.
        lock_ttl: Time-to-live for the lock in seconds.
        wait_for_lock: Whether to wait for lock acquisition.
        wait_timeout: Maximum time to wait for lock in seconds.
        heartbeat_interval: Interval for sending heartbeats in seconds.

    """

    lock_key: str
    exclusive: bool = False
    lock_ttl: int = 90
    wait_for_lock: bool = True
    wait_timeout: int = 300
    heartbeat_interval: int = 30

    @classmethod
    def for_pipeline(
        cls,
        provider: str,
        entity_type: str,
        run_type: RunType,
        lock_ttl: int = 90,
        wait_for_lock: bool = True,
        wait_timeout: int = 300,
        heartbeat_interval: int = 30,
        batch_size_hint: int | None = None,
    ) -> LockConfig:
        """Create LockConfig for a pipeline.

        Generates appropriate lock key based on provider, entity, and run type.
        When ``batch_size_hint`` is provided, the TTL is scaled adaptively to
        accommodate larger batches while respecting the configured minimum and a
        hard ceiling of 600 seconds.

        Args:
            provider: Name of the data provider.
            entity_type: Type of entity being processed.
            run_type: Type of run (determines exclusivity).
            lock_ttl: Time-to-live for the lock in seconds (minimum bound).
            wait_for_lock: Whether to wait for lock acquisition.
            wait_timeout: Maximum time to wait for lock in seconds.
            heartbeat_interval: Interval for sending heartbeats in seconds.
            batch_size_hint: Optional expected batch size used to scale TTL
                adaptively (~0.3 s per record).  When ``None`` the configured
                ``lock_ttl`` is used unchanged (backward-compatible default).

        Returns:
            Configured LockConfig instance.

        """
        from bioetl.domain.types import RunType

        exclusive = run_type in (RunType.BACKFILL, RunType.REBUILD)
        lock_key = f"lock:{provider}_{entity_type}"
        if exclusive:
            lock_key = f"{lock_key}:exclusive"

        if batch_size_hint is not None and batch_size_hint > 0:
            # Scale TTL: ~0.3s per record, minimum is the configured lock_ttl
            adaptive_ttl = int(batch_size_hint * 0.3)
            lock_ttl = min(max(lock_ttl, adaptive_ttl), 600)  # ceiling 600s

        return cls(
            lock_key=lock_key,
            exclusive=exclusive,
            lock_ttl=lock_ttl,
            wait_for_lock=wait_for_lock,
            wait_timeout=wait_timeout,
            heartbeat_interval=heartbeat_interval,
        )
