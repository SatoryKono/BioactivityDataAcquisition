"""Sanitized runtime-setting snapshots for effective-config artifacts."""

from __future__ import annotations

import hashlib
import json

from bioetl.composition.runtime_builders._run_manifest_refs import (
    resolve_data_root_mode,
)
from bioetl.composition.services.versioning import get_dependency_lock_hash
from bioetl.domain.control_plane.effective_config_environment import (
    semantic_runtime_env_dependencies,
)
from bioetl.domain.filtering.silver_filter_identity import (
    build_silver_filter_compatibility_snapshot,
    resolve_silver_filter_compatibility_mode,
)
from bioetl.infrastructure.config.settings_api import Settings

from ._effective_config_secret_support import build_secret_surface_inventory

_EXECUTION_AFFECTING_SETTINGS_SURFACES = semantic_runtime_env_dependencies()


def current_silver_filter_compatibility_mode() -> str:
    return resolve_silver_filter_compatibility_mode()


def current_silver_filter_compatibility_snapshot() -> dict[str, object]:
    return build_silver_filter_compatibility_snapshot()


def add_silver_filter_compatibility_defaults(payload: dict[str, object]) -> None:
    payload.setdefault(
        "silver_filter_compatibility_mode",
        current_silver_filter_compatibility_mode(),
    )
    payload.setdefault(
        "silver_filter_compatibility",
        current_silver_filter_compatibility_snapshot(),
    )


def build_execution_settings_snapshot(settings: Settings) -> dict[str, object]:
    """Materialize env-derived execution settings without exposing secrets."""
    pipeline = _setting_attr(settings, "pipeline", object())
    control_plane = _setting_attr(pipeline, "control_plane", object())
    observability = _setting_attr(settings, "observability", object())
    snapshot: dict[str, object] = {
        "schema_version": "execution-settings-v1",
        "materialized_surfaces": list(_EXECUTION_AFFECTING_SETTINGS_SURFACES),
        "silver_filter_compatibility": current_silver_filter_compatibility_snapshot(),
        "settings": {
            "env": _setting_attr(settings, "env"),
            "debug": _setting_attr(settings, "debug", False),
            "test_mode": _setting_attr(settings, "test_mode", False),
            "data_dir": str(_setting_attr(settings, "data_dir", "")),
            "data_root_mode": resolve_data_root_mode(settings),
            "strict_error_handling": _setting_attr(
                settings, "strict_error_handling", False
            ),
            "strict_medallion": _setting_attr(settings, "strict_medallion", False),
            "silver_dedup_timeout_seconds": _setting_attr(
                settings, "silver_dedup_timeout_seconds", None
            ),
            "pii_salt_rotation_active": _setting_attr(
                settings, "pii_salt_rotation_active", False
            ),
            "json_encoder": _setting_attr(settings, "json_encoder"),
            "default_email": _setting_attr(settings, "default_email"),
        },
        "pipeline": {
            "batch_size": _setting_attr(pipeline, "batch_size", None),
            "checkpoint_interval": _setting_attr(pipeline, "checkpoint_interval", None),
            "relaxed_dq": _setting_attr(pipeline, "relaxed_dq", False),
            "max_concurrent_batches": _setting_attr(
                pipeline, "max_concurrent_batches", None
            ),
            "heartbeat_interval": _setting_attr(pipeline, "heartbeat_interval", None),
            "health_check_mode": _setting_attr(pipeline, "health_check_mode", None),
        },
        "control_plane": {
            "required_persistence_profile": (
                _setting_attr(control_plane, "required_persistence_profile", None)
            ),
            "run_manifest_enabled": _setting_attr(
                control_plane, "run_manifest_enabled", True
            ),
            "run_ledger_enabled": _setting_attr(
                control_plane, "run_ledger_enabled", True
            ),
            "checkpoint_compatibility_policy": (
                _setting_attr(control_plane, "checkpoint_compatibility_policy", None)
            ),
        },
        "observability": {
            "metrics_enabled": _setting_attr(observability, "metrics_enabled", True),
            "tracing_enabled": _setting_attr(observability, "tracing_enabled", False),
            "audit_enabled": _setting_attr(observability, "audit_enabled", False),
        },
        "secret_redaction": build_secret_surface_inventory(
            settings=settings,
            value_hash=_sha256_text,
        ),
        "non_materialized_semantic_env_dependencies": list(
            _EXECUTION_AFFECTING_SETTINGS_SURFACES
        ),
    }
    snapshot["snapshot_hash"] = _sha256_text(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    )
    return snapshot


def build_execution_environment_snapshot(settings: Settings) -> dict[str, object]:
    """Materialize sanitized environment/dependency provenance for env overrides."""
    settings_snapshot = build_execution_settings_snapshot(settings)
    dependency_lock_hash = get_dependency_lock_hash()
    return {
        "schema_version": "execution-environment-v1",
        "settings_env": _setting_attr(settings, "env"),
        "debug": _setting_attr(settings, "debug", False),
        "test_mode": _setting_attr(settings, "test_mode", False),
        "data_root_mode": resolve_data_root_mode(settings),
        "dependency_lock_hash": dependency_lock_hash,
        "dependency_lock_present": dependency_lock_hash is not None,
        "settings_snapshot_hash": settings_snapshot["snapshot_hash"],
    }


def _setting_attr(host: object, name: str, default: object = None) -> object:
    return getattr(host, name, default)


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"
