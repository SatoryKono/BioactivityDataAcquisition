"""Effective config artifact creation for control-plane."""

from __future__ import annotations

import json
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition.runtime_builders import (
    _run_manifest_support as _manifest_support,
)
from bioetl.composition.runtime_builders._run_manifest_builder_policy import (
    resolve_manifest_reproducibility_context,
)
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
from bioetl.infrastructure.control_plane import FileEffectiveConfigArtifactStore

if TYPE_CHECKING:
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.config import Settings


_EXECUTION_AFFECTING_SETTINGS_SURFACES: tuple[str, ...] = (
    "settings.env",
    "settings.debug",
    "settings.test_mode",
    "settings.data_dir",
    "settings.strict_error_handling",
    "settings.strict_medallion",
    "settings.silver_dedup_timeout_seconds",
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


def _build_execution_settings_snapshot(settings: Settings) -> dict[str, object]:
    """Materialize env-derived execution settings without exposing secrets."""
    pipeline = settings.pipeline
    control_plane = pipeline.control_plane
    observability = settings.observability
    return {
        "schema_version": "execution-settings-v1",
        "materialized_surfaces": list(_EXECUTION_AFFECTING_SETTINGS_SURFACES),
        "settings": {
            "env": settings.env,
            "debug": settings.debug,
            "test_mode": settings.test_mode,
            "data_dir": str(settings.data_dir),
            "strict_error_handling": settings.strict_error_handling,
            "strict_medallion": settings.strict_medallion,
            "silver_dedup_timeout_seconds": settings.silver_dedup_timeout_seconds,
        },
        "pipeline": {
            "batch_size": pipeline.batch_size,
            "checkpoint_interval": pipeline.checkpoint_interval,
            "relaxed_dq": pipeline.relaxed_dq,
            "max_concurrent_batches": pipeline.max_concurrent_batches,
            "heartbeat_interval": pipeline.heartbeat_interval,
            "health_check_mode": pipeline.health_check_mode,
        },
        "control_plane": {
            "required_persistence_profile": (
                control_plane.required_persistence_profile
            ),
            "run_manifest_enabled": control_plane.run_manifest_enabled,
            "run_ledger_enabled": control_plane.run_ledger_enabled,
            "checkpoint_compatibility_policy": (
                control_plane.checkpoint_compatibility_policy
            ),
        },
        "observability": {
            "metrics_enabled": observability.metrics_enabled,
            "tracing_enabled": observability.tracing_enabled,
            "audit_enabled": observability.audit_enabled,
        },
    }


def _build_runtime_overrides_snapshot(
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
            "settings_snapshot": _build_execution_settings_snapshot(settings),
        },
    }


def _build_composite_runtime_overrides_snapshot(
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
        "settings_snapshot", _build_execution_settings_snapshot(settings)
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


def _build_effective_config_source_refs(
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


def _resolve_effective_config_entity(provider: str, entity: str) -> str:
    """Map runtime entity labels to canonical effective-config source paths."""
    if provider == "composite" and entity.startswith("composite_"):
        return entity.removeprefix("composite_")
    return entity


def _control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _shared_control_plane_root(settings, leaf)


def _create_and_persist_effective_config_artifact_payload(
    *,
    pipeline_name: str,
    pipeline_kind: str,
    resolved_config: object,
    runtime_overrides: dict[str, object],
    provider: str,
    entity: str,
    required_persistence_profile: str,
    settings: Settings,
    logger: object,
    run_id: RunID,
) -> tuple[str, str, str, str]:
    """Persist one effective-config artifact and return its provenance anchors."""
    service = create_effective_config_service()
    artifact = service.create_effective_config_artifact(
        pipeline_name=pipeline_name,
        pipeline_kind=pipeline_kind,
        resolved_config=_to_serializable_mapping(resolved_config),
        runtime_overrides=runtime_overrides,
        source_refs=_build_effective_config_source_refs(
            provider=provider,
            entity=_resolve_effective_config_entity(provider, entity),
        ),
        required_persistence_profile=required_persistence_profile,
    )
    serialized_payload = service.serialize_artifact(artifact)
    loaded_payload = json.loads(serialized_payload)
    if not isinstance(loaded_payload, dict):
        raise ValueError("Effective-config artifact payload must be a JSON object")
    artifact_payload = {str(key): value for key, value in loaded_payload.items()}
    artifact_store = FileEffectiveConfigArtifactStore(
        base_path=_control_plane_root(settings, "effective_config")
    )
    try:
        artifact_store.save(
            artifact_id=artifact.artifact_id,
            run_id=run_id,
            payload=artifact_payload,
        )
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        log_error = getattr(logger, "error", None)
        if callable(log_error):
            log_error(
                "effective_config_artifact_persist_failed",
                artifact_id=artifact.artifact_id,
                pipeline_name=pipeline_name,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise
    log_info = getattr(logger, "info", None)
    if callable(log_info):
        log_info(
            "effective_config_artifact_persisted",
            artifact_id=artifact.artifact_id,
            pipeline_name=pipeline_name,
            resolved_config_hash=artifact.resolved_config_hash,
            effective_config_hash=artifact.effective_config_hash,
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
        )
    return (
        artifact.artifact_id,
        artifact.resolved_config_hash,
        artifact.effective_config_hash,
        artifact.dq_contract_compatibility_hash,
    )


def create_and_persist_effective_config_artifact(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
) -> tuple[str, str, str, str]:
    """Create effective config artifact, persist it, and return provenance fields."""
    contract_ref, _contract_version, _contract_schema_hash, _dq_policy_ref, _rules = (
        _manifest_support.resolve_contract_identity(provider=provider, entity=entity)
    )
    reproducibility_context = resolve_manifest_reproducibility_context(
        ctx=ctx,
        inputs=inputs,
        provider=provider,
        entity=entity,
        contract_ref=contract_ref,
    )
    return _create_and_persist_effective_config_artifact_payload(
        pipeline_name=ctx.pipeline_name,
        pipeline_kind="standard",
        resolved_config=inputs.yaml_config,
        runtime_overrides=_build_runtime_overrides_snapshot(ctx, inputs.settings),
        provider=provider,
        entity=entity,
        required_persistence_profile=(
            reproducibility_context.required_persistence_profile
        ),
        settings=inputs.settings,
        logger=inputs.observability.logger,
        run_id=ctx.run_id,
    )


def create_and_persist_composite_effective_config_artifact(
    *,
    pipeline_name: str,
    config: object,
    runtime_config: object,
    required_persistence_profile: str,
    settings: Settings,
    logger: object,
    run_id: RunID,
) -> tuple[str, str, str, str]:
    """Persist the composite effective-config artifact using the shared path."""
    return _create_and_persist_effective_config_artifact_payload(
        pipeline_name=pipeline_name,
        pipeline_kind="composite",
        resolved_config=config,
        runtime_overrides=_build_composite_runtime_overrides_snapshot(
            pipeline_name=pipeline_name,
            runtime_config=runtime_config,
            required_persistence_profile=required_persistence_profile,
            settings=settings,
        ),
        provider="composite",
        entity=pipeline_name,
        required_persistence_profile=required_persistence_profile,
        settings=settings,
        logger=logger,
        run_id=run_id,
    )
