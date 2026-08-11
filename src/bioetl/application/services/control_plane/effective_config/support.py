"""Private helpers for effective configuration artifact construction."""

from __future__ import annotations

from bioetl.application.services.control_plane.effective_config.runtime_overrides import (
    ALLOWLISTED_SEMANTIC_ENV_OVERRIDE_KEYS,
    apply_deep_update,
    apply_runtime_overrides,
    build_effective_execution_config,
    build_execution_environment_snapshot,
    build_runtime_override_snapshot,
    coerce_runtime_override_layer,
    normalize_runtime_overrides_for_semantic_identity,
    validate_runtime_environment_provenance,
)
from bioetl.application.services.control_plane.effective_config.serialization import (
    SemanticIdentityPayloadContext,
    build_effective_config_artifact_id,
    build_semantic_identity_payload,
    canonical_source_refs,
    serialize_artifact,
    stable_hash,
)
from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
    RESOLVED_CONFIG_IDENTITY_VERSION,
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    ResolvedConfigSnapshot,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQPolicyRef

__all__ = [
    "ALLOWLISTED_SEMANTIC_ENV_OVERRIDE_KEYS",
    "SemanticIdentityPayloadContext",
    "apply_deep_update",
    "apply_runtime_overrides",
    "build_dq_components",
    "build_effective_config_artifact_id",
    "build_effective_execution_config",
    "build_execution_environment_snapshot",
    "build_resolved_config_snapshot",
    "build_runtime_override_snapshot",
    "build_semantic_identity_payload",
    "coerce_runtime_override_layer",
    "compute_source_fingerprint",
    "extract_contract_refs",
    "normalize_runtime_overrides_for_semantic_identity",
    "resolve_resolution_policy",
    "serialize_artifact",
    "stable_hash",
    "validate_runtime_environment_provenance",
]


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
        strictness_mode=dq_config.strictness_mode or "standard",
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
    return stable_hash(
        [
            {
                "type": src.source_type,
                "path": src.source_path,
                "hash": src.source_hash or "no_hash",
                "hash_version": src.source_hash_version or "unversioned",
                "priority": src.priority,
            }
            for src in canonical_source_refs(source_refs)
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
        config_hash=stable_hash(
            {
                "identity_version": RESOLVED_CONFIG_IDENTITY_VERSION,
                "config_data": resolved_config,
            }
        ),
    )
