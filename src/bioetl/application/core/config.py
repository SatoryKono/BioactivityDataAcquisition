"""Configuration objects for application core components."""

from __future__ import annotations

__all__ = [
    "ContentHashPolicyByVersion",
    "ContentHashPolicyGroup",
    "ContentHashVersionPolicy",
    "GoldSchemaPolicyByVersion",
    "LockConfig",
    "RecordProcessorConfig",
]


from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.domain.composite.config import ColumnGroupConfig
from bioetl.domain.config import DQConfig, MemoryConfig, TableConfig
from bioetl.domain.types import (
    ArrowSchema,
    GoldSchemaPolicyByVersion,
    GoldSchemaType,
    ScdConfig,
)

if TYPE_CHECKING:
    from bioetl.domain.composite.config import DataSchemaConfig
    from bioetl.domain.types import RunType


@dataclass(frozen=True, slots=True)
class ContentHashVersionPolicy:
    """Hash include/exclude policy for one contract version."""

    version: str
    include_fields: frozenset[str] = field(default_factory=frozenset)
    exclude_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class ContentHashPolicyGroup:
    """Typed container for active and shadow content-hash policies."""

    active_version: str
    policies: tuple[ContentHashVersionPolicy, ...]
    affects_hash: bool = False

    def __post_init__(self) -> None:
        """Validate version uniqueness and active-version presence."""
        if not self.active_version.strip():
            raise ValueError("active_version cannot be empty")
        versions = tuple(policy.version for policy in self.policies)
        if len(versions) != len(set(versions)):
            raise ValueError("hash policy versions must be unique")
        if self.active_version not in versions:
            raise ValueError("active_version must be present in hash policies")

    def for_version(self, version: str) -> ContentHashVersionPolicy | None:
        """Return the policy for one contract version when present."""
        return next(
            (policy for policy in self.policies if policy.version == version), None
        )

    @property
    def active_policy(self) -> ContentHashVersionPolicy:
        """Return the active-version content hash policy."""
        policy = self.for_version(self.active_version)
        if policy is None:  # pragma: no cover - guarded by __post_init__
            raise ValueError("active_version must be present in hash policies")
        return policy

    @property
    def versions(self) -> tuple[str, ...]:
        """Return the ordered policy versions."""
        return tuple(policy.version for policy in self.policies)

    @property
    def is_multi_version(self) -> bool:
        """Whether the rollout needs multiple content hashes in one run."""
        return len(self.policies) > 1

    @property
    def requires_projected_hashes(self) -> bool:
        """Whether the current rollout must compute per-version hash projections."""
        return self.affects_hash and self.is_multi_version


@dataclass(frozen=True)
class RecordProcessorConfig:
    """Configuration for RecordProcessor."""

    pipeline_name: str
    provider: str
    entity_type: str
    silver_schema: ArrowSchema | None
    gold_schema: GoldSchemaType
    dq_config: DQConfig | None = None
    table_config: TableConfig = field(default_factory=TableConfig)
    memory_config: MemoryConfig = field(default_factory=MemoryConfig)
    column_groups: tuple[ColumnGroupConfig, ...] = ()
    # Backward-compat for tests/callers still passing data_schema directly.
    data_schema: DataSchemaConfig | None = None
    # SCD Type 2 configuration (Gold layer)
    scd_config: ScdConfig | None = None
    # DQ report output paths (for flat_structure support)
    bronze_output_path: str | None = None
    silver_output_path: str | None = None
    gold_output_path: str | None = None
    flat_structure: bool = False
    normalization_enabled: bool = True
    normalization_rule_set: NormalizationRulesPolicy = field(
        default_factory=NormalizationRulesPolicy
    )
    allow_compatibility_fallback: bool = False
    content_hash_policy_authoritative: bool = False
    content_hash_include_fields: frozenset[str] = field(default_factory=frozenset)
    content_hash_exclude_fields: frozenset[str] = field(default_factory=frozenset)
    content_hash_policy_by_version: ContentHashPolicyByVersion | None = None
    gold_schema_policy_by_version: GoldSchemaPolicyByVersion | None = None


ContentHashPolicyByVersion = ContentHashPolicyGroup


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
