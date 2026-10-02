"""Runtime override and execution-environment helpers for effective config."""

from __future__ import annotations

import copy
from typing import cast

from bioetl.domain.control_plane.effective_config_artifact import (
    EFFECTIVE_CONFIG_IDENTITY_VERSION,
    EffectiveExecutionConfig,
    ExecutionEnvironmentSnapshot,
    RuntimeOverrideSnapshot,
)
from bioetl.domain.control_plane.effective_config_environment import (
    AMBIENT_ENVIRONMENT_POLICY,
    MATERIALIZED_EXECUTION_ENVIRONMENT_POLICY,
    semantic_runtime_env_dependencies,
)
from bioetl.domain.control_plane.effective_config_runtime_identity import (
    normalize_runtime_overrides_for_semantic_identity as normalize_runtime_overrides_for_semantic_identity,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.normalization.json import stable_json_hash, to_jsonable
from bioetl.domain.types import JsonDict

ALLOWLISTED_SEMANTIC_ENV_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {"execution_environment"}
)


def apply_deep_update(target: JsonDict, source: JsonDict) -> None:
    for key, value in source.items():
        target_value = target.get(key)
        if isinstance(target_value, dict) and isinstance(value, dict):
            apply_deep_update(cast(JsonDict, target_value), cast(JsonDict, value))
            continue
        target[key] = value


def apply_runtime_overrides(base_config: JsonDict, overrides: JsonDict) -> JsonDict:
    effective_config = copy.deepcopy(base_config)
    for layer in ("cli", "env", "runtime"):
        layer_overrides = overrides.get(layer)
        if isinstance(layer_overrides, dict):
            apply_deep_update(effective_config, layer_overrides)
    return effective_config


def coerce_runtime_override_layer(
    runtime_overrides: JsonDict, layer_name: str
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
        override_hash=stable_json_hash(runtime_overrides),
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
    env_materialized = isinstance(execution_environment, dict) and bool(
        execution_environment
    )
    semantic_dependencies = (
        () if env_materialized else semantic_runtime_env_dependencies()
    )
    ambient_environment_policy = (
        MATERIALIZED_EXECUTION_ENVIRONMENT_POLICY
        if env_materialized
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
        environment_hash=stable_json_hash(snapshot_payload),
    )


def build_effective_execution_config(
    *,
    resolved_config: JsonDict,
    runtime_overrides: JsonDict,
) -> EffectiveExecutionConfig:
    effective_config_data = apply_runtime_overrides(resolved_config, runtime_overrides)
    return EffectiveExecutionConfig(
        config_data=effective_config_data,
        effective_hash=stable_json_hash(
            {
                "identity_version": EFFECTIVE_CONFIG_IDENTITY_VERSION,
                "config_data": effective_config_data,
            }
        ),
    )
