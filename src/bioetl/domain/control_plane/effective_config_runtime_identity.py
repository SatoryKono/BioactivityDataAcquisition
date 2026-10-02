"""Canonical machine-local path normalization for effective-config identity."""

from __future__ import annotations

import copy

from bioetl.domain.normalization.json import stable_json_hash
from bioetl.domain.types import JsonDict

_EXPLICIT_DATA_DIR_SENTINEL = "<explicit-data-dir>"
_CACHED_BRONZE_PATH_SENTINEL = "<cached-bronze-path>"


def _normalized_settings_snapshot_hash(settings_snapshot: JsonDict) -> str:
    snapshot_payload = copy.deepcopy(settings_snapshot)
    snapshot_payload.pop("snapshot_hash", None)
    return f"sha256:{stable_json_hash(snapshot_payload)}"


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


def _normalize_runtime_settings(runtime: object) -> str | None:
    """Normalize settings only when the persisted runtime carries a snapshot."""
    if not isinstance(runtime, dict):
        return None
    snapshot = runtime.get("settings_snapshot")
    if not isinstance(snapshot, dict):
        return None
    return _normalize_settings_snapshot_for_semantic_identity(snapshot)


def _bind_environment_settings_hash(env: object, snapshot_hash: str | None) -> None:
    """Keep environment identity aligned with the normalized runtime snapshot."""
    if not isinstance(env, dict):
        return
    execution = env.get("execution_environment")
    if not isinstance(execution, dict):
        return
    if snapshot_hash is None:
        execution.pop("settings_snapshot_hash", None)
    else:
        execution["settings_snapshot_hash"] = snapshot_hash


def normalize_runtime_overrides_for_semantic_identity(
    runtime_overrides: JsonDict,
) -> JsonDict:
    """Drop machine-local path variance from semantic replay identity inputs."""
    normalized = copy.deepcopy(runtime_overrides)

    for layer_name in ("cli", "runtime"):
        layer_overrides = normalized.get(layer_name)
        if isinstance(layer_overrides, dict):
            _normalize_cached_bronze_surface_for_semantic_identity(layer_overrides)

    normalized_settings_hash = _normalize_runtime_settings(normalized.get("runtime"))
    _bind_environment_settings_hash(normalized.get("env"), normalized_settings_hash)

    return normalized


def normalize_persisted_runtime_overrides(overrides: JsonDict) -> JsonDict:
    """Project serialized overrides onto the same identity as config creation.

    Keep raw paths in persisted evidence; normalize only the comparison copy.
    """
    layers = {
        "cli": overrides.get("cli_overrides", {}),
        "env": overrides.get("env_overrides", {}),
        "runtime": overrides.get("runtime_adjustments", {}),
    }
    normalized_layers = normalize_runtime_overrides_for_semantic_identity(layers)
    normalized = copy.deepcopy(overrides)
    for stored_key, layer in (
        ("cli_overrides", "cli"),
        ("env_overrides", "env"),
        ("runtime_adjustments", "runtime"),
    ):
        if stored_key in normalized:
            normalized[stored_key] = normalized_layers[layer]
    if "override_hash" in normalized:
        normalized["override_hash"] = stable_json_hash(normalized_layers)
    return normalized
