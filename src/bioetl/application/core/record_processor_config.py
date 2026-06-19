"""Record-processor configuration and content-hash policy types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.application.services.debug_export_service import DebugExportConfig
from bioetl.domain.composite.config_merge import ColumnGroupConfig
from bioetl.domain.config import DQConfig, MemoryConfig, TableConfig
from bioetl.domain.types import (
    ArrowSchema,
    GoldSchemaPolicyByVersion,
    GoldSchemaType,
    ScdConfig,
)

if TYPE_CHECKING:
    from bioetl.domain.composite.config_schema import DataSchemaConfig


@dataclass(frozen=True, slots=True)
class ContentHashVersionPolicy:
    """Hash include/exclude policy for one contract version."""

    version: str
    include_fields: frozenset[str] = field(default_factory=frozenset)
    exclude_fields: frozenset[str] = field(default_factory=frozenset)
    datetime_policy: str = "v2_datetime_utc"


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


ContentHashPolicyByVersion = ContentHashPolicyGroup


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
    debug_export_config: DebugExportConfig | None = None


__all__ = [
    "ContentHashPolicyByVersion",
    "ContentHashPolicyGroup",
    "ContentHashVersionPolicy",
    "GoldSchemaPolicyByVersion",
    "RecordProcessorConfig",
]
