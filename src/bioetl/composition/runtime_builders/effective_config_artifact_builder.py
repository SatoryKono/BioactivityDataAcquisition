"""Effective config artifact creation for control-plane."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.services.control_plane.effective_config_service import (
    create_effective_config_service,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    control_plane_root as _shared_control_plane_root,
)
from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef
from bioetl.infrastructure.control_plane import FileEffectiveConfigArtifactStore

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings


def _normalize_snapshot(value: object) -> object:
    """Normalize dataclass/Pydantic values into JSON-safe primitives."""
    if not isinstance(value, type) and is_dataclass(value):
        return _normalize_snapshot(asdict(cast("DataclassInstance", value)))
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return _normalize_snapshot(
            {key: item for key, item in vars(value).items() if not key.startswith("_")}
        )
    if isinstance(value, dict):
        return {str(key): _normalize_snapshot(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_normalize_snapshot(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    return value


def _to_serializable_mapping(value: object) -> dict[str, object]:
    """Convert dataclass or model objects into plain mappings."""
    if hasattr(value, "model_dump"):
        payload = value.model_dump(mode="json", exclude_none=True)
    elif hasattr(value, "dict"):
        payload = value.dict(exclude_none=True)
    elif hasattr(value, "__dict__"):
        payload = {
            key: item for key, item in vars(value).items() if not key.startswith("_")
        }
    else:
        payload = _normalize_snapshot(value)
    if not isinstance(payload, dict):
        return {"value": _normalize_snapshot(payload)}
    normalized = _normalize_snapshot(payload)
    if not isinstance(normalized, dict):
        raise TypeError("Manifest snapshot normalization must return a mapping")
    return normalized


def _build_runtime_overrides_snapshot(ctx: PipelineRunContext) -> dict[str, object]:
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
    return {
        "cli": {},
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
        },
    }


def _compute_file_hash(path: Path) -> str | None:
    """Return a stable SHA-256 hash for one config source file when available."""
    if not path.exists() or not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _build_config_source_ref(
    *,
    relative_path: str,
    priority: int,
    repo_root: Path,
) -> ConfigSourceRef:
    """Build one canonical file-backed source ref with provenance hash."""
    source_path = repo_root / relative_path
    return ConfigSourceRef(
        source_type="file",
        source_path=relative_path,
        source_hash=_compute_file_hash(source_path),
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
    return [
        _build_config_source_ref(
            relative_path="configs/base/pipeline.yaml",
            priority=1,
            repo_root=resolved_repo_root,
        ),
        _build_config_source_ref(
            relative_path=f"configs/entities/{provider}/{entity}.yaml",
            priority=2,
            repo_root=resolved_repo_root,
        ),
        _build_config_source_ref(
            relative_path="configs/base/contract_registry.yaml",
            priority=3,
            repo_root=resolved_repo_root,
        ),
    ]


def _control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return _shared_control_plane_root(settings, leaf)


def create_and_persist_effective_config_artifact(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
) -> tuple[str, str, str]:
    """Create effective config artifact, persist it, and return provenance fields."""
    logger = inputs.observability.logger
    service = create_effective_config_service()
    artifact = service.create_effective_config_artifact(
        pipeline_name=ctx.pipeline_name,
        pipeline_kind="standard",
        resolved_config=_to_serializable_mapping(inputs.yaml_config),
        runtime_overrides=_build_runtime_overrides_snapshot(ctx),
        source_refs=_build_effective_config_source_refs(
            provider=provider, entity=entity
        ),
    )
    serialized_payload = service.serialize_artifact(artifact)
    loaded_payload = json.loads(serialized_payload)
    if not isinstance(loaded_payload, dict):
        raise ValueError("Effective-config artifact payload must be a JSON object")
    artifact_payload = {str(key): value for key, value in loaded_payload.items()}
    artifact_store = FileEffectiveConfigArtifactStore(
        base_path=_control_plane_root(inputs.settings, "effective_config")
    )
    try:
        artifact_store.save(
            artifact_id=artifact.artifact_id,
            run_id=ctx.run_id,
            payload=artifact_payload,
        )
    except (OSError, RuntimeError, ValueError, TypeError) as exc:
        log_error = getattr(logger, "error", None)
        if callable(log_error):
            log_error(
                "effective_config_artifact_persist_failed",
                artifact_id=artifact.artifact_id,
                pipeline_name=ctx.pipeline_name,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
        raise
    log_info = getattr(logger, "info", None)
    if callable(log_info):
        log_info(
            "effective_config_artifact_persisted",
            artifact_id=artifact.artifact_id,
            pipeline_name=ctx.pipeline_name,
            effective_config_hash=artifact.effective_config_hash,
            dq_contract_compatibility_hash=artifact.dq_contract_compatibility_hash,
        )
    return (
        artifact.artifact_id,
        artifact.effective_config_hash,
        artifact.dq_contract_compatibility_hash,
    )
