"""Derived context builder for effective-config artifacts."""

from __future__ import annotations

import copy
from dataclasses import dataclass

from bioetl.application.services.control_plane.effective_config.provenance_support import (
    build_source_class_provenance,
)
from bioetl.application.services.control_plane.effective_config.runtime_overrides import (
    build_effective_execution_config,
    build_execution_environment_snapshot,
    build_runtime_override_snapshot,
    normalize_runtime_overrides_for_semantic_identity,
    validate_runtime_environment_provenance,
)
from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
    RESOLVED_CONFIG_IDENTITY_VERSION,
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    EffectiveExecutionConfig,
    ExecutionEnvironmentSnapshot,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
    SourceClassProvenance,
)
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQPolicyRef

__all__ = ["EffectiveConfigContext", "build_effective_config_context"]


@dataclass(frozen=True, slots=True)
class EffectiveConfigContext:
    """Typed derived values used to assemble one effective-config artifact."""

    contract_refs: list[str]
    dq_contract_compatibility_hash: str
    dq_policy_refs: list[DQPolicyRef]
    dq_policy_snapshots: list[DQPolicySnapshot]
    dq_rule_bundle_versions: dict[str, str]
    effective_snapshot: EffectiveExecutionConfig
    execution_environment: ExecutionEnvironmentSnapshot
    overrides_snapshot: RuntimeOverrideSnapshot
    resolved_policy: ConfigResolutionPolicy
    resolved_snapshot: ResolvedConfigSnapshot
    semantic_overrides_snapshot: RuntimeOverrideSnapshot
    source_class_provenance: tuple[SourceClassProvenance, ...]
    source_fingerprint: str
    source_refs: list[ConfigSourceRef]


def build_dq_components(
    dq_config: DQConfig | None,
) -> tuple[list[DQPolicyRef], list[DQPolicySnapshot], dict[str, str]]:
    if dq_config is None:
        return [], [], {}

    resolver = DQPolicyResolver(dq_config)
    policy_ref = resolver.build_policy_ref()
    policy_snapshot = DQPolicySnapshot(
        contract_ref=policy_ref.contract_ref,
        contract_version=policy_ref.contract_version,
        rule_bundle_version=policy_ref.rule_bundle_version,
        policy_hash=policy_ref.policy_hash or "",
        default_disposition=dq_config.default_disposition_policy,
        disposition_overrides=dict(dq_config.disposition_overrides),
        strictness_mode=dq_config.strictness_mode,
    )
    dq_rule_bundle_versions: dict[str, str] = {}
    if policy_ref.contract_ref and policy_ref.rule_bundle_version:
        dq_rule_bundle_versions[policy_ref.contract_ref] = (
            policy_ref.rule_bundle_version
        )
    return [policy_ref], [policy_snapshot], dq_rule_bundle_versions


def extract_contract_refs(dq_config: DQConfig | None) -> list[str]:
    if dq_config is None or not dq_config.contract_ref:
        return []
    return [dq_config.contract_ref]


def resolve_resolution_policy(
    resolution_policy: ConfigResolutionPolicy | None,
) -> ConfigResolutionPolicy:
    if resolution_policy is not None:
        return resolution_policy
    return ConfigResolutionPolicy()


def compute_source_fingerprint(source_refs: list[ConfigSourceRef]) -> str:
    if not source_refs:
        return "no_sources"
    ordered = sorted(
        source_refs,
        key=lambda src: (
            src.priority,
            src.source_type,
            src.source_path,
            src.source_hash or "",
            src.raw_source_hash or "",
        ),
    )
    return stable_json_hash(
        [
            {
                "type": src.source_type,
                "path": src.source_path,
                "hash": src.source_hash or "no_hash",
                "hash_version": src.source_hash_version or "unversioned",
                "priority": src.priority,
            }
            for src in ordered
        ]
    )


def build_resolved_config_snapshot(
    *,
    pipeline_kind: str,
    resolved_config: JsonDict,
) -> ResolvedConfigSnapshot:
    return ResolvedConfigSnapshot(
        config_type=pipeline_kind,
        config_data=resolved_config,
        config_hash=stable_json_hash(
            {
                "identity_version": RESOLVED_CONFIG_IDENTITY_VERSION,
                "config_data": resolved_config,
            }
        ),
    )


def build_effective_config_context(
    *,
    pipeline_kind: str,
    resolved_config: JsonDict,
    runtime_overrides: JsonDict,
    source_refs: list[ConfigSourceRef],
    dq_config: DQConfig | None,
    resolution_policy: ConfigResolutionPolicy | None,
    required_persistence_profile: str,
) -> EffectiveConfigContext:
    """Build derived snapshots for one effective-config artifact."""
    validate_runtime_environment_provenance(
        runtime_overrides=runtime_overrides,
        required_persistence_profile=required_persistence_profile,
    )
    resolved_policy = resolve_resolution_policy(resolution_policy)
    isolated_resolved_config = copy.deepcopy(resolved_config)
    isolated_runtime_overrides = copy.deepcopy(runtime_overrides)
    resolved_snapshot = build_resolved_config_snapshot(
        pipeline_kind=pipeline_kind,
        resolved_config=isolated_resolved_config,
    )
    overrides_snapshot = build_runtime_override_snapshot(isolated_runtime_overrides)
    semantic_runtime_overrides = normalize_runtime_overrides_for_semantic_identity(
        isolated_runtime_overrides
    )
    semantic_overrides_snapshot = build_runtime_override_snapshot(
        semantic_runtime_overrides
    )
    execution_environment = build_execution_environment_snapshot(
        semantic_runtime_overrides,
        required_persistence_profile=required_persistence_profile,
    )
    effective_snapshot = build_effective_execution_config(
        resolved_config=isolated_resolved_config,
        runtime_overrides=semantic_runtime_overrides,
    )
    dq_policy_refs, dq_policy_snapshots, dq_rule_bundle_versions = build_dq_components(
        dq_config
    )
    dq_contract_compatibility_hash = (
        "no_dq_policies"
        if not dq_policy_refs
        else ":".join(
            sorted(
                ref.policy_hash
                for ref in dq_policy_refs
                if ref.policy_hash is not None and ref.policy_hash
            )
        )
        or "no_dq_policy_hashes"
    )
    return EffectiveConfigContext(
        contract_refs=extract_contract_refs(dq_config),
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        dq_policy_refs=dq_policy_refs,
        dq_policy_snapshots=dq_policy_snapshots,
        dq_rule_bundle_versions=dq_rule_bundle_versions,
        effective_snapshot=effective_snapshot,
        execution_environment=execution_environment,
        overrides_snapshot=overrides_snapshot,
        resolved_policy=resolved_policy,
        resolved_snapshot=resolved_snapshot,
        semantic_overrides_snapshot=semantic_overrides_snapshot,
        source_class_provenance=build_source_class_provenance(),
        source_fingerprint=compute_source_fingerprint(source_refs),
        source_refs=source_refs,
    )
