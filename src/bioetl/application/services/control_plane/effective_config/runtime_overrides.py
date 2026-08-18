"""Runtime override and execution-environment helpers for effective config."""

from __future__ import annotations

import copy
from typing import cast

from bioetl.application.services.control_plane.effective_config.serialization import (
    stable_hash,
    to_jsonable,
)
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
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
    normalize_required_persistence_profile,
)
from bioetl.domain.types import JsonDict

ALLOWLISTED_SEMANTIC_ENV_OVERRIDE_KEYS: frozenset[str] = frozenset(
    {"execution_environment"}
)
_EXPLICIT_DATA_DIR_SENTINEL = "<explicit-data-dir>"
_CACHED_BRONZE_PATH_SENTINEL = "<cached-bronze-path>"


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
        override_hash=stable_hash(runtime_overrides),
    )


def _normalized_settings_snapshot_hash(settings_snapshot: JsonDict) -> str:
    snapshot_payload = copy.deepcopy(settings_snapshot)
    snapshot_payload.pop("snapshot_hash", None)
    return f"sha256:{stable_hash(snapshot_payload)}"


def _normalize_settings_snapshot_for_semantic_identity(
    settings_snapshot: JsonDict,
) -> str:
    settings = settings_snapshot.get("settings")
    if isinstance(settings, dict) and settings.get("data_root_mode") == "explicit":
        data_dir = settings.get("data_dir")
        if isinstance(data_dir, str) and data_dir:
            settings["data_dir"] = _EXPLICIT_DATA_DIR_SENTINEL
    snapshot_hash = _normalized_settings_snapshot_hash(settings_snapshot)
    settings_snapshot["snapshot_hash"] = snapshot_hash
    return snapshot_hash


def _normalize_cached_bronze_surface_for_semantic_identity(candidate: JsonDict) -> None:
    cached_bronze = candidate.get("cached_bronze")
    if not isinstance(cached_bronze, dict):
        return
    bronze_path = cached_bronze.get("bronze_path")
    if isinstance(bronze_path, str) and bronze_path:
        cached_bronze["bronze_path"] = _CACHED_BRONZE_PATH_SENTINEL


def normalize_runtime_overrides_for_semantic_identity(
    runtime_overrides: JsonDict,
) -> JsonDict:
    """Drop machine-local path variance from semantic replay identity inputs."""
    normalized = copy.deepcopy(runtime_overrides)

    for layer_name in ("cli", "runtime"):
        layer_overrides = normalized.get(layer_name)
        if isinstance(layer_overrides, dict):
            _normalize_cached_bronze_surface_for_semantic_identity(layer_overrides)

    normalized_settings_hash: str | None = None
    runtime_overrides_payload = normalized.get("runtime")
    if isinstance(runtime_overrides_payload, dict):
        settings_snapshot = runtime_overrides_payload.get("settings_snapshot")
        if isinstance(settings_snapshot, dict):
            normalized_settings_hash = (
                _normalize_settings_snapshot_for_semantic_identity(settings_snapshot)
            )

    env_overrides = normalized.get("env")
    if isinstance(env_overrides, dict):
        execution_environment = env_overrides.get("execution_environment")
        if isinstance(execution_environment, dict):
            if normalized_settings_hash is not None:
                execution_environment["settings_snapshot_hash"] = (
                    normalized_settings_hash
                )
            else:
                execution_environment.pop("settings_snapshot_hash", None)

    return normalized


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
        environment_hash=stable_hash(snapshot_payload),
    )


def build_effective_execution_config(
    *,
    resolved_config: JsonDict,
    runtime_overrides: JsonDict,
) -> EffectiveExecutionConfig:
    effective_config_data = apply_runtime_overrides(resolved_config, runtime_overrides)
    return EffectiveExecutionConfig(
        config_data=effective_config_data,
        effective_hash=stable_hash(
            {
                "identity_version": EFFECTIVE_CONFIG_IDENTITY_VERSION,
                "config_data": effective_config_data,
            }
        ),
    )
