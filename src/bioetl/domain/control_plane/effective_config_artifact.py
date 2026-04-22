"""Effective configuration runtime artifact with DQ integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

from bioetl.domain.control_plane.config_source_hashing import (
    ConfigSourceHashStrategy,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition, DQPolicyRef


def _require_non_empty(value: str, field_name: str) -> None:
    if not value:
        raise ValueError(f"{field_name} cannot be empty")


def _compute_dq_compatibility_hash(policy_refs: list[DQPolicyRef]) -> str:
    if not policy_refs:
        return "no_dq_policies"
    policy_hashes = sorted(ref.policy_hash for ref in policy_refs if ref.policy_hash)
    if not policy_hashes:
        return "no_dq_policy_hashes"
    return ":".join(policy_hashes)


def _normalize_utc(value: datetime) -> datetime:
    """Normalize an explicit timestamp to timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _current_utc_time() -> datetime:
    """Resolve the sanctioned domain time source lazily to avoid import cycles."""
    from bioetl.domain.context import current_utc_time

    return current_utc_time()


@dataclass(frozen=True)
class ConfigSourceRef:
    """Reference to a configuration source file or input."""

    source_type: str  # "file", "env", "cli", "default"
    source_path: str
    source_hash: str | None = None
    priority: int = 0
    raw_source_hash: str | None = None
    source_hash_strategy: ConfigSourceHashStrategy | None = None


@dataclass(frozen=True)
class SourceClassProvenance:
    """Published provenance contract for one supported config/input source class."""

    source_class: str
    provenance_status: Literal["identity_anchored", "external_anchor", "unsupported"]
    artifact_surface: str
    anchor_field: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ConfigResolutionPolicy:
    """Policy governing configuration resolution."""

    merge_strategy: str = "hierarchical"
    default_materialization: bool = True
    strict_validation: bool = True
    allow_runtime_overrides: bool = True


@dataclass(frozen=True)
class ResolvedConfigSnapshot:
    """Snapshot of resolved configuration before runtime overrides."""

    config_type: str  # "standard" | "composite"
    config_data: JsonDict
    config_hash: str
    timestamp: datetime = field(default_factory=_current_utc_time)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", _normalize_utc(self.timestamp))


@dataclass(frozen=True)
class RuntimeOverrideSnapshot:
    """Snapshot of runtime overrides applied to resolved config."""

    cli_overrides: JsonDict = field(default_factory=dict)
    env_overrides: JsonDict = field(default_factory=dict)
    runtime_adjustments: JsonDict = field(default_factory=dict)
    override_hash: str = ""


@dataclass(frozen=True)
class EffectiveExecutionConfig:
    """Final effective configuration after all overrides."""

    config_data: JsonDict
    effective_hash: str
    timestamp: datetime = field(default_factory=_current_utc_time)

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", _normalize_utc(self.timestamp))


@dataclass(frozen=True)
class DQPolicySnapshot:
    """Snapshot of Data Quality policy configuration."""

    contract_ref: str
    contract_version: str
    rule_bundle_version: str
    policy_hash: str
    default_disposition: DQDisposition
    disposition_overrides: dict[str, DQDisposition] = field(default_factory=dict)
    strictness_mode: Literal["lenient", "moderate", "standard", "strict"] = "standard"


@dataclass(frozen=True)
class EffectiveConfigArtifact:
    """First-class runtime artifact representing effective configuration."""

    artifact_id: str
    pipeline_name: str
    pipeline_kind: str  # "standard" | "composite"
    source_refs: list[ConfigSourceRef]
    resolution_policy: ConfigResolutionPolicy
    resolved_config: ResolvedConfigSnapshot
    runtime_overrides: RuntimeOverrideSnapshot
    effective_execution_config: EffectiveExecutionConfig
    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str
    source_class_provenance: tuple[SourceClassProvenance, ...] = ()
    schema_version: str = "1.0"
    created_at: datetime = field(default_factory=_current_utc_time)
    contract_refs: list[str] = field(default_factory=list)
    dq_policy_refs: list[DQPolicyRef] = field(default_factory=list)
    dq_rule_bundle_versions: dict[str, str] = field(default_factory=dict)
    dq_contract_compatibility_hash: str = ""
    dq_policy_snapshots: list[DQPolicySnapshot] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate required fields and ensure compatibility hash is populated."""
        _require_non_empty(self.artifact_id, "artifact_id")
        _require_non_empty(self.pipeline_name, "pipeline_name")
        _require_non_empty(self.pipeline_kind, "pipeline_kind")
        object.__setattr__(self, "created_at", _normalize_utc(self.created_at))
        compatibility_hash = (
            self.dq_contract_compatibility_hash
            or _compute_dq_compatibility_hash(self.dq_policy_refs)
        )
        object.__setattr__(self, "dq_contract_compatibility_hash", compatibility_hash)


@dataclass(frozen=True)
class EffectiveConfigHashes:
    """Container for configuration hashes used in compatibility checks."""

    resolved_config_hash: str
    effective_config_hash: str
    source_fingerprint: str
    dq_contract_compatibility_hash: str

    def __post_init__(self) -> None:
        """Validate hash fields."""
        _require_non_empty(self.resolved_config_hash, "resolved_config_hash")
        _require_non_empty(self.effective_config_hash, "effective_config_hash")
        _require_non_empty(self.source_fingerprint, "source_fingerprint")
