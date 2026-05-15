"""Support helpers for effective-config artifact runtime builders."""

from __future__ import annotations

import hashlib
import json
import posixpath
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from bioetl.composition.runtime_builders._run_manifest_refs import (
    control_plane_root as _shared_control_plane_root,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    resolve_data_root_mode,
)
from bioetl.composition.runtime_builders._run_manifest_support import (
    to_serializable_mapping as _to_serializable_mapping,
)
from bioetl.composition.runtime_builders._silver_filter_compatibility_support import (
    add_silver_filter_compatibility_defaults,
    current_silver_filter_compatibility_mode,
    current_silver_filter_compatibility_snapshot,
)
from bioetl.composition.services.versioning import get_dependency_lock_hash
from bioetl.domain.control_plane.config_source_hashing import (
    ConfigSourceHashStrategy,
    compute_config_source_hashes,
)
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.domain.control_plane.effective_config_environment import (
    semantic_runtime_env_dependencies,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings

_EXECUTION_AFFECTING_SETTINGS_SURFACES = semantic_runtime_env_dependencies()

_EXECUTION_SECRET_SETTING_SURFACES: tuple[tuple[str, str], ...] = (
    ("settings.pii_salt_current", "pii_salt_current"),
    ("settings.pii_salt_next", "pii_salt_next"),
    ("settings.pubmed_api_key", "pubmed_api_key"),
    ("settings.uniprot_api_key", "uniprot_api_key"),
    ("settings.openalex_api_key", "openalex_api_key"),
    ("settings.semanticscholar_api_key", "semanticscholar_api_key"),
)
_CONFIG_GRAPH_FILE_SUFFIXES = (".yaml", ".yml", ".toml", ".lock")
_DEPENDENCY_PROVENANCE_FILES = ("pyproject.toml", "uv.lock", "poetry.lock")


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
        "silver_filter_compatibility_mode": current_silver_filter_compatibility_mode(),
    }
    silver_filter_compatibility = current_silver_filter_compatibility_snapshot()
    return {
        "cli": cli_overrides,
        "env": {
            "execution_environment": _build_execution_environment_snapshot(settings)
        },
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
            "silver_filter_compatibility": silver_filter_compatibility,
            "silver_filter_compatibility_mode": silver_filter_compatibility["mode"],
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
    add_silver_filter_compatibility_defaults(runtime_payload)
    return {
        "cli": dict(runtime_payload),
        "env": {
            "execution_environment": _build_execution_environment_snapshot(settings)
        },
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


def _normalize_relative_posix_path(value: str) -> str:
    return posixpath.normpath(value.replace("\\", "/"))


def _core_config_graph_paths(*, provider: str, entity: str) -> list[str]:
    core_paths = ["configs/base/pipeline.yaml", "configs/base/quality.yaml"]
    if provider == "composite":
        core_paths.extend(
            [
                f"configs/composites/{entity}.yaml",
                f"configs/quality/entities/composite/{entity}.yaml",
            ]
        )
    else:
        core_paths.extend(
            [
                f"configs/providers/{provider}.yaml",
                f"configs/entities/{provider}/{entity}.yaml",
                f"configs/quality/entities/{provider}/{entity}.yaml",
            ]
        )
    core_paths.append("configs/base/contract_registry.yaml")
    return core_paths


def _candidate_seed_paths(*, provider: str, entity: str) -> tuple[str, ...]:
    if provider == "composite":
        return (
            f"configs/composites/{entity}.yaml",
            f"configs/quality/entities/composite/{entity}.yaml",
        )
    return (
        f"configs/providers/{provider}.yaml",
        f"configs/entities/{provider}/{entity}.yaml",
        f"configs/quality/entities/{provider}/{entity}.yaml",
    )


def _extract_config_reference_strings(payload: object) -> list[str]:
    references: list[str] = []
    if isinstance(payload, str):
        references.append(payload)
    elif isinstance(payload, dict):
        for value in payload.values():
            references.extend(_extract_config_reference_strings(value))
    elif isinstance(payload, (list, tuple)):
        for value in payload:
            references.extend(_extract_config_reference_strings(value))
    return references


def _resolve_config_graph_reference(
    *,
    raw_value: str,
    base_dir: str,
) -> str | None:
    candidate = raw_value.strip()
    if not candidate or "://" in candidate:
        return None
    if not candidate.endswith(_CONFIG_GRAPH_FILE_SUFFIXES):
        return None
    normalized_candidate = _normalize_relative_posix_path(candidate)
    if normalized_candidate in _DEPENDENCY_PROVENANCE_FILES:
        return normalized_candidate
    if normalized_candidate.startswith("/"):
        return None
    if normalized_candidate.startswith("configs/"):
        return normalized_candidate
    resolved = _normalize_relative_posix_path(
        posixpath.join(base_dir, normalized_candidate)
    )
    if resolved.startswith("../") or resolved == "..":
        return None
    if resolved.startswith("configs/"):
        return resolved
    return None


def _load_config_graph_references(
    *,
    relative_path: str,
    repo_root: Path,
) -> list[str]:
    source_path = repo_root / relative_path
    if source_path.suffix not in {".yaml", ".yml"} or not source_path.exists():
        return []
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}
    base_dir = posixpath.dirname(relative_path)
    discovered: list[str] = []
    for raw_value in _extract_config_reference_strings(payload):
        resolved = _resolve_config_graph_reference(
            raw_value=raw_value,
            base_dir=base_dir,
        )
        if resolved is not None:
            discovered.append(resolved)
    return discovered


def _discover_effective_config_graph_paths(
    *,
    provider: str,
    entity: str,
    repo_root: Path,
) -> list[str]:
    discovered: list[str] = []
    pending = list(_candidate_seed_paths(provider=provider, entity=entity))
    seen: set[str] = set()
    while pending:
        relative_path = pending.pop(0)
        normalized = _normalize_relative_posix_path(relative_path)
        if normalized in seen:
            continue
        seen.add(normalized)
        if not (repo_root / normalized).exists():
            continue
        discovered.append(normalized)
        for reference in _load_config_graph_references(
            relative_path=normalized,
            repo_root=repo_root,
        ):
            if reference not in seen:
                pending.append(reference)
    return discovered


def build_effective_config_source_refs(
    *,
    provider: str,
    entity: str,
    repo_root: Path | None = None,
) -> list[ConfigSourceRef]:
    """Build source references used to materialize effective config artifacts."""
    resolved_repo_root = repo_root or Path(__file__).resolve().parents[4]
    candidate_paths: list[str] = []
    for relative_path in _core_config_graph_paths(provider=provider, entity=entity):
        if relative_path not in candidate_paths:
            candidate_paths.append(relative_path)
    for relative_path in _discover_effective_config_graph_paths(
        provider=provider,
        entity=entity,
        repo_root=resolved_repo_root,
    ):
        if relative_path not in candidate_paths:
            candidate_paths.append(relative_path)
    for relative_path in _DEPENDENCY_PROVENANCE_FILES:
        if relative_path not in candidate_paths:
            candidate_paths.append(relative_path)
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
