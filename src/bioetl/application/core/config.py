"""Configuration objects for application core components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from bioetl.application.core.memory_monitor import MemoryConfig
from bioetl.domain.config import DQConfig, TableConfig

if TYPE_CHECKING:
    from bioetl.domain.types import RunType


@dataclass(frozen=True)
class RecordProcessorConfig:
    """Configuration for RecordProcessor."""

    pipeline_name: str
    provider: str
    entity_type: str
    silver_schema: Any
    gold_schema: Any
    dq_config: DQConfig | None = None
    table_config: TableConfig = field(default_factory=TableConfig)
    memory_config: MemoryConfig = field(default_factory=MemoryConfig)


@dataclass(frozen=True, slots=True)
class LockConfig:
    """Configuration for LockManager.

    Bundles locking configuration to reduce __init__ parameters.

    Attributes:
        lock_key: The key used for the distributed lock.
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
    ) -> LockConfig:
        """Create LockConfig for a pipeline.

        Generates appropriate lock key based on provider, entity, and run type.

        Args:
            provider: Name of the data provider.
            entity_type: Type of entity being processed.
            run_type: Type of run (determines exclusivity).
            lock_ttl: Time-to-live for the lock in seconds.
            wait_for_lock: Whether to wait for lock acquisition.
            wait_timeout: Maximum time to wait for lock in seconds.
            heartbeat_interval: Interval for sending heartbeats in seconds.

        Returns:
            Configured LockConfig instance.

        """
        from bioetl.domain.types import RunType

        exclusive = run_type in (RunType.BACKFILL, RunType.REBUILD)
        lock_key = f"lock:{provider}_{entity_type}"
        if exclusive:
            lock_key = f"{lock_key}:exclusive"

        return cls(
            lock_key=lock_key,
            exclusive=exclusive,
            lock_ttl=lock_ttl,
            wait_for_lock=wait_for_lock,
            wait_timeout=wait_timeout,
            heartbeat_interval=heartbeat_interval,
        )
