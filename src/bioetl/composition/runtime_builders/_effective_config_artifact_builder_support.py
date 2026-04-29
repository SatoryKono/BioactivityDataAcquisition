"""Support helpers for effective-config artifact runtime builders."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._run_manifest_refs import (
    control_plane_root as _shared_control_plane_root,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    to_serializable_mapping as _to_serializable_mapping,
)
from bioetl.domain.control_plane.config_source_hashing import (
    ConfigSourceHashStrategy,
    compute_config_source_hashes,
)
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings

_EXECUTION_AFFECTING_SETTINGS_SURFACES: tuple[str, ...] = (
    "settings.env",
    "settings.debug",
    "settings.test_mode",
    "settings.data_dir",
    "settings.strict_error_handling",
    "settings.strict_medallion",
    "settings.silver_dedup_timeout_seconds",
    "settings.pii_salt_rotation_active",
    "settings.json_encoder",
    "settings.default_email",
    "settings.pii_salt_current",
    "settings.pii_salt_next",
    "settings.pubmed_api_key",
    "settings.uniprot_api_key",
    "settings.openalex_api_key",
    "settings.semanticscholar_api_key",
    "settings.pipeline.batch_size",
    "settings.pipeline.checkpoint_interval",
    "settings.pipeline.relaxed_dq",
    "settings.pipeline.health_check_mode",
    "settings.pipeline.control_plane.required_persistence_profile",
    "settings.pipeline.control_plane.run_manifest_enabled",
    "settings.pipeline.control_plane.run_ledger_enabled",
    "settings.pipeline.control_plane.checkpoint_compatibility_policy",
    "settings.observability.metrics_enabled",
    "settings.observability.tracing_enabled",
    "settings.observability.audit_enabled",
)

_EXECUTION_SECRET_SETTING_SURFACES: tuple[tuple[str, str], ...] = (
    ("settings.pii_salt_current", "pii_salt_current"),
    ("settings.pii_salt_next", "pii_salt_next"),
    ("settings.pubmed_api_key", "pubmed_api_key"),
    ("settings.uniprot_api_key", "uniprot_api_key"),
    ("settings.openalex_api_key", "openalex_api_key"),
    ("settings.semanticscholar_api_key", "semanticscholar_api_key"),
)


def _setting_attr(host: object, name: str, default: object = None) -> object:
    return getattr(host, name, default)


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _secret_value_hash(value: object) -> str | None:
    if value is None:
        return None
    get_secret_value = getattr(value, "get_secret_value", None)
    raw_value = get_secret_value() if callable(get_secret_value) else value
    if raw_value in (None, ""):
        return None
    return _sha256_text(str(raw_value))


def _build_secret_surface_inventory(settings: Settings) -> dict[str, object]:
    secret_surfaces: dict[str, object] = {}
    for surface, attribute_name in _EXECUTION_SECRET_SETTING_SURFACES:
        value_hash = _secret_value_hash(getattr(settings, attribute_name, None))
        secret_surfaces[surface] = {
            "present": value_hash is not None,
            "value_hash": value_hash,
        }
    return {
        "policy": "secret_values_redacted_hash_anchored",
        "hash_algorithm": "sha256",
        "secret_surfaces": secret_surfaces,
    }


def build_execution_settings_snapshot(settings: Settings) -> dict[str, object]:
    """Materialize env-derived execution settings without exposing secrets."""
    pipeline = _setting_attr(settings, "pipeline", object())
    control_plane = _setting_attr(pipeline, "control_plane", object())
    observability = _setting_attr(settings, "observability", object())
    snapshot: dict[str, object] = {
        "schema_version": "execution-settings-v1",
        "materialized_surfaces": list(_EXECUTION_AFFECTING_SETTINGS_SURFACES),
        "settings": {
            "env": _setting_attr(settings, "env"),
            "debug": _setting_attr(settings, "debug", False),
            "test_mode": _setting_attr(settings, "test_mode", False),
            "data_dir": str(_setting_attr(settings, "data_dir", "")),
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
        "non_materialized_semantic_env_dependencies": [],
    }
    snapshot["snapshot_hash"] = _sha256_text(
        json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    )
    return snapshot


def build_runtime_overrides_snapshot(
    ctx: PipelineRunContext,
    settings: Settings,
) -> dict[str, object]:
    """Convert launch context options into runtime-override snapshot shape."""
    raw_run_type = getattr(ctx, "run_type", "incremental")
    run_type_value = (
        raw_run_type.value if isinstance(raw_run_type, Enum) else str(raw_run_type)
    )
    raw_execution_context = getattr(ctx, "execution_context", "isolated")
    execution_context_value = (
        raw_execution_context.value
        if isinstance(raw_execution_context, Enum)
        else str(raw_execution_context)
    )
    cli_overrides = {
        "run_type": run_type_value,
        "resume": getattr(ctx, "resume", False),
        "dry_run": getattr(ctx, "dry_run", False),
        "limit": getattr(ctx, "limit", None),
        "query": getattr(ctx, "query", None),
        "start_offset": getattr(ctx, "start_offset", None),
        "log_level": getattr(ctx, "log_level", "INFO"),
        "ignore_yaml_filter": getattr(ctx, "ignore_yaml_filter", False),
        "skip_gold": getattr(ctx, "skip_gold", False),
        "exact_replay": getattr(ctx, "exact_replay", False),
        "input_filter": _to_serializable_mapping(getattr(ctx, "input_filter", None)),
        "cached_bronze": _to_serializable_mapping(getattr(ctx, "cached_bronze", None)),
        "vacuum": _to_serializable_mapping(getattr(ctx, "vacuum", None)),
        "replay_of_run_id": getattr(ctx, "replay_of_run_id", None),
        "replay_of_manifest_id": getattr(ctx, "replay_of_manifest_id", None),
    }
    return {
        "cli": cli_overrides,
        "env": {},
        "runtime": {
            "pipeline_name": str(getattr(ctx, "pipeline_name", "unknown")),
            "run_type": run_type_value,
            "resume": getattr(ctx, "resume", False),
            "dry_run": getattr(ctx, "dry_run", False),
            "limit": getattr(ctx, "limit", None),
            "query": getattr(ctx, "query", None),
            "start_offset": getattr(ctx, "start_offset", None),
            "log_level": getattr(ctx, "log_level", "INFO"),
            "ignore_yaml_filter": getattr(ctx, "ignore_yaml_filter", False),
            "skip_gold": getattr(ctx, "skip_gold", False),
            "execution_context": execution_context_value,
            "vacuum": _to_serializable_mapping(getattr(ctx, "vacuum", None)),
            "input_filter": _to_serializable_mapping(
                getattr(ctx, "input_filter", None)
            ),
            "cached_bronze": _to_serializable_mapping(
                getattr(ctx, "cached_bronze", None)
            ),
            "settings_snapshot": build_execution_settings_snapshot(settings),
        },
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
    return {
        "cli": dict(runtime_payload),
        "env": {},
        "runtime": runtime_payload,
    }


def _compute_file_hashes(
    *,
    relative_path: str,
    path: Path,
) -> tuple[str | None, str | None, ConfigSourceHashStrategy | None]:
    """Return semantic and raw hashes for one config source file when available."""
    if not path.exists() or not path.is_file():
        return None, None, None
    hashes = compute_config_source_hashes(
        source_path=relative_path,
        raw_bytes=path.read_bytes(),
    )
    return hashes.semantic_hash, hashes.raw_hash, hashes.hash_strategy


def _build_config_source_ref(
    *,
    relative_path: str,
    priority: int,
    repo_root: Path,
) -> ConfigSourceRef:
    """Build one canonical file-backed source ref with provenance hash."""
    source_path = repo_root / relative_path
    source_hash, raw_source_hash, source_hash_strategy = _compute_file_hashes(
        relative_path=relative_path,
        path=source_path,
    )
    return ConfigSourceRef(
        source_type="file",
        source_path=relative_path,
        source_hash=source_hash,
        raw_source_hash=raw_source_hash,
        source_hash_strategy=source_hash_strategy,
        priority=priority,
    )


def build_effective_config_source_refs(
    *,
    provider: str,
    entity: str,
    repo_root: Path | None = None,
) -> list[ConfigSourceRef]:
    """Build source references used to materialize effective config artifacts."""
    resolved_repo_root = repo_root or Path(__file__).resolve().parents[4]
    candidate_paths = [
        "configs/base/pipeline.yaml",
        "configs/base/quality.yaml",
        f"configs/providers/{provider}.yaml",
        f"configs/entities/{provider}/{entity}.yaml",
        f"configs/quality/entities/{provider}/{entity}.yaml",
        f"configs/contracts/{provider}/{entity}.yaml",
        "configs/base/contract_registry.yaml",
    ]
    if provider == "composite":
        candidate_paths[2:2] = [
            f"configs/composites/{entity}.yaml",
            f"configs/quality/entities/composite/{entity}.yaml",
        ]
    refs: list[ConfigSourceRef] = []
    priority = 1
    for relative_path in candidate_paths:
        if not (resolved_repo_root / relative_path).exists():
            continue
        refs.append(
            _build_config_source_ref(
                relative_path=relative_path,
                priority=priority,
                repo_root=resolved_repo_root,
            )
        )
        priority += 1
    return refs


def resolve_effective_config_entity(provider: str, entity: str) -> str:
    """Map runtime entity labels to canonical effective-config source paths."""
    if provider == "composite" and entity.startswith("composite_"):
        return entity.removeprefix("composite_")
    return entity


def control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _shared_control_plane_root(settings, leaf)
