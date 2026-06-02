"""Private helpers for effective configuration artifact construction."""

from __future__ import annotations

import copy
from typing import cast

from bioetl.application.services.control_plane.effective_config.serialization import (
    SemanticIdentityPayloadContext,
    build_effective_config_artifact_id,
    build_semantic_identity_payload,
    canonical_source_refs,
    serialize_artifact,
    stable_hash,
    to_jsonable,
)
from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
    DQPolicySnapshot,
    EffectiveExecutionConfig,
    ExecutionEnvironmentSnapshot,
    ResolvedConfigSnapshot,
    RuntimeOverrideSnapshot,
)
from bioetl.domain.control_plane.effective_config_environment import (
    AMBIENT_ENVIRONMENT_POLICY,
    MATERIALIZED_EXECUTION_ENVIRONMENT_POLICY,
    semantic_runtime_env_dependencies,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQPolicyRef

__all__ = [
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
    "compute_source_fingerprint",
    "extract_contract_refs",
    "resolve_resolution_policy",
    "serialize_artifact",
    "validate_runtime_environment_provenance",
]

ALLOWLISTED_SEMANTIC_ENV_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {"execution_environment"}
)


def apply_deep_update(target: JsonDict, source: JsonDict) -> None:
    for key, value in source.items():
        target_value = target.get(key)
        if isinstance(target_value, dict) and isinstance(value, dict):
            apply_deep_update(
                cast(JsonDict, target_value),
                cast(JsonDict, value),
            )
            continue
        target[key] = value


def apply_runtime_overrides(base_config: JsonDict, overrides: JsonDict) -> JsonDict:
    effective_config = copy.deepcopy(base_config)
    for layer in ("cli", "env", "runtime"):
        layer_overrides = overrides.get(layer)
        if isinstance(layer_overrides, dict):
            apply_deep_update(effective_config, layer_overrides)
    return effective_config


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
        config_hash=stable_hash(resolved_config),
    )


def coerce_runtime_override_layer(
    runtime_overrides: JsonDict,
    layer_name: str,
) -> JsonDict:
    layer_overrides = runtime_overrides.get(layer_name, {})
    if layer_overrides is None:
        return {}
    if not isinstance(layer_overrides, dict):
        raise TypeError(f"runtime_overrides.{layer_name} must be a mapping")
    return cast(JsonDict, layer_overrides)


def validate_runtime_environment_provenance(
    *,
    runtime_overrides: JsonDict,
    required_persistence_profile: object,
) -> None:
    profile = normalize_required_persistence_profile(required_persistence_profile)
    if profile not in STRICT_PERSISTENCE_PROFILES:
        return
    env_overrides = coerce_runtime_override_layer(runtime_overrides, "env")
    unsupported_keys = sorted(
        str(key)
        for key in env_overrides
        if str(key) not in ALLOWLISTED_SEMANTIC_ENV_OVERRIDE_KEYS
    )
    if unsupported_keys:
        raise ValueError(
            "runtime_overrides.env contains non-allowlisted semantic environment "
            f"overrides for required persistence profile '{profile}': "
            f"{', '.join(unsupported_keys)}"
        )
    execution_environment = env_overrides.get("execution_environment")
    if execution_environment is None:
        raise ValueError(
            "runtime_overrides.env.execution_environment must be materialized "
            f"for required persistence profile '{profile}'"
        )
    if not isinstance(execution_environment, dict):
        raise TypeError("runtime_overrides.env.execution_environment must be a mapping")
    if not execution_environment:
        raise ValueError(
            "runtime_overrides.env.execution_environment must be non-empty for "
            f"required persistence profile '{profile}'"
        )


def build_runtime_override_snapshot(
    runtime_overrides: JsonDict,
) -> RuntimeOverrideSnapshot:
    return RuntimeOverrideSnapshot(
        cli_overrides=coerce_runtime_override_layer(runtime_overrides, "cli"),
        env_overrides=coerce_runtime_override_layer(runtime_overrides, "env"),
        runtime_adjustments=coerce_runtime_override_layer(runtime_overrides, "runtime"),
        override_hash=stable_hash(runtime_overrides),
    )


def build_execution_environment_snapshot(
    runtime_overrides: JsonDict,
    *,
    required_persistence_profile: object | None = None,
) -> ExecutionEnvironmentSnapshot:
    """Materialize explicit execution-affecting environment overrides."""
    env_overrides = coerce_runtime_override_layer(runtime_overrides, "env")
    materialized_env_overrides = {
        str(key): to_jsonable(value)
        for key, value in sorted(env_overrides.items(), key=lambda item: str(item[0]))
    }
    profile = normalize_required_persistence_profile(required_persistence_profile)
    execution_environment = env_overrides.get("execution_environment")
    execution_environment_materialized = isinstance(
        execution_environment, dict
    ) and bool(execution_environment)
    semantic_dependencies = (
        ()
        if execution_environment_materialized
        else semantic_runtime_env_dependencies()
    )
    ambient_environment_policy = (
        MATERIALIZED_EXECUTION_ENVIRONMENT_POLICY
        if execution_environment_materialized
        else AMBIENT_ENVIRONMENT_POLICY
    )
    snapshot_payload = {
        "materialized_env_overrides": materialized_env_overrides,
        "non_materialized_semantic_env_dependencies": semantic_dependencies,
        "ambient_environment_policy": ambient_environment_policy,
        "required_persistence_profile": profile,
    }
    return ExecutionEnvironmentSnapshot(
        materialized_env_keys=tuple(materialized_env_overrides),
        materialized_env_overrides=materialized_env_overrides,
        ambient_environment_policy=ambient_environment_policy,
        non_materialized_semantic_env_dependencies=semantic_dependencies,
        environment_hash=stable_hash(snapshot_payload),
    )


def build_effective_execution_config(
    *,
    resolved_config: JsonDict,
    runtime_overrides: JsonDict,
) -> EffectiveExecutionConfig:
    effective_config_data = apply_runtime_overrides(
        resolved_config,
        runtime_overrides,
    )
    return EffectiveExecutionConfig(
        config_data=effective_config_data,
        effective_hash=stable_hash(effective_config_data),
    )
