"""Support helpers for effective-config artifact runtime builders."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._effective_config_graph_support import (
    build_effective_config_candidate_paths,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    resolve_data_root_mode,
    resolve_run_context_values,
)
from bioetl.composition.runtime_builders._effective_config_source_refs_support import (
    build_effective_config_source_refs as _build_effective_config_source_refs,
    resolve_effective_config_entity,
)
from bioetl.composition.runtime_builders.config_access import resolve_configs_root
from bioetl.composition.runtime_builders._effective_config_secret_support import (
    build_secret_surface_inventory,
)
from bioetl.composition.runtime_builders._silver_filter_compatibility_support import (
    add_silver_filter_compatibility_defaults,
    current_silver_filter_compatibility_mode,
    current_silver_filter_compatibility_snapshot,
)
from bioetl.composition.runtime_builders._runtime_launch_context_fields import (
    build_runtime_launch_field_snapshot,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    to_serializable_mapping as _to_serializable_mapping,
)
from bioetl.composition.services.versioning import get_dependency_lock_hash
from bioetl.domain.control_plane.effective_config_environment import (
    semantic_runtime_env_dependencies,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef

_EXECUTION_AFFECTING_SETTINGS_SURFACES = semantic_runtime_env_dependencies()


def _setting_attr(host: object, name: str, default: object = None) -> object:
    return getattr(host, name, default)


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _build_secret_surface_inventory(settings: Settings) -> dict[str, object]:
    return build_secret_surface_inventory(settings=settings, value_hash=_sha256_text)


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
        "secret_redaction": _build_secret_surface_inventory(settings),
        "non_materialized_semantic_env_dependencies": list(
            _EXECUTION_AFFECTING_SETTINGS_SURFACES
        ),
    }
    snapshot["snapshot_hash"] = _sha256_text(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    )
    return snapshot


def _build_execution_environment_snapshot(settings: Settings) -> dict[str, object]:
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


def build_runtime_overrides_snapshot(
    ctx: PipelineRunContext,
    settings: Settings,
) -> dict[str, object]:
    """Convert launch context options into runtime-override snapshot shape."""
    run_type_value, execution_context_value = resolve_run_context_values(ctx)
    cli_overrides = build_runtime_launch_field_snapshot(
        ctx,
        run_type_value=run_type_value,
    )
    cli_overrides.update(
        {
            "required_persistence_profile": getattr(
                ctx, "required_persistence_profile", None
            ),
            "input_filter": _to_serializable_mapping(
                getattr(ctx, "input_filter", None)
            ),
            "cached_bronze": _to_serializable_mapping(
                getattr(ctx, "cached_bronze", None)
            ),
            "vacuum": _to_serializable_mapping(getattr(ctx, "vacuum", None)),
            "replay_of_run_id": getattr(ctx, "replay_of_run_id", None),
            "replay_of_manifest_id": getattr(ctx, "replay_of_manifest_id", None),
            "silver_filter_compatibility_mode": current_silver_filter_compatibility_mode(),
        }
    )
    silver_filter_compatibility = current_silver_filter_compatibility_snapshot()
    runtime_fields = build_runtime_launch_field_snapshot(
        ctx,
        run_type_value=run_type_value,
        execution_context_value=execution_context_value,
    )
    runtime_fields.update(
        {
            "required_persistence_profile": getattr(
                ctx, "required_persistence_profile", None
            ),
            "vacuum": _to_serializable_mapping(getattr(ctx, "vacuum", None)),
            "input_filter": _to_serializable_mapping(
                getattr(ctx, "input_filter", None)
            ),
            "cached_bronze": _to_serializable_mapping(
                getattr(ctx, "cached_bronze", None)
            ),
            "settings_snapshot": build_execution_settings_snapshot(settings),
            "silver_filter_compatibility": silver_filter_compatibility,
            "silver_filter_compatibility_mode": silver_filter_compatibility["mode"],
        }
    )
    return {
        "cli": cli_overrides,
        "env": {
            "execution_environment": _build_execution_environment_snapshot(settings)
        },
        "runtime": runtime_fields,
    }


def build_composite_runtime_overrides_snapshot(
    *,
    pipeline_name: str,
    runtime_config: object,
    required_persistence_profile: str,
    settings: Settings,
) -> dict[str, object]:
    """Convert composite runtime config into effective-config override shape."""
    runtime_payload = _to_serializable_mapping(runtime_config)
    runtime_payload.setdefault("pipeline_name", pipeline_name)
    runtime_payload.setdefault("execution_context", "composite")
    runtime_payload.setdefault(
        "required_persistence_profile", required_persistence_profile
    )
    runtime_payload.setdefault(
        "settings_snapshot", build_execution_settings_snapshot(settings)
    )
    add_silver_filter_compatibility_defaults(runtime_payload)
    return {
        "cli": dict(runtime_payload),
        "env": {
            "execution_environment": _build_execution_environment_snapshot(settings)
        },
        "runtime": runtime_payload,
    }


def build_effective_config_source_refs(
    *,
    provider: str,
    entity: str,
    repo_root: Path | None = None,
) -> list[ConfigSourceRef]:
    """Build source references used to materialize effective config artifacts."""
    resolved_repo_root = repo_root or resolve_configs_root().parent
    return _build_effective_config_source_refs(
        provider=provider,
        entity=resolve_effective_config_entity(provider, entity),
        candidate_paths_factory=build_effective_config_candidate_paths,
        repo_root=resolved_repo_root,
    )
