"""Control-plane helpers for runtime runner assembly."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass, replace
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.application.services.run_manifest_service import (
    RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.control_plane import RunArtifactRef, RunSourceRef
from bioetl.infrastructure.control_plane import FileRunLedgerStore, FileRunManifestStore

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.application.core.runner import PipelineRunner
    from bioetl.composition.runtime_builders.inputs_resolver import (
        RunnerInputs,
    )
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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


def _resolve_provider_entity(
    *,
    pipeline_name: str,
    yaml_config: object,
) -> tuple[str, str]:
    """Resolve provider/entity from YAML when available, otherwise fallback."""
    if "_" in pipeline_name:
        fallback_provider, fallback_entity = pipeline_name.split("_", 1)
    else:
        fallback_provider = pipeline_name
        fallback_entity = pipeline_name
    provider = getattr(yaml_config, "provider", fallback_provider) or fallback_provider
    entity = getattr(yaml_config, "entity_type", fallback_entity) or fallback_entity
    return str(provider), str(entity)


def _compute_manifest_config_hash(yaml_config: object) -> str:
    """Compute config hash with a lenient fallback for unit-test stubs."""
    try:
        return compute_config_hash(
            cast("PipelineYamlConfig | dict[str, object]", yaml_config)
        )
    except (TypeError, ValueError):
        return compute_config_hash(_to_serializable_mapping(yaml_config))


def _build_launch_context_snapshot(ctx: PipelineRunContext) -> dict[str, object]:
    """Capture launch-time options that materially affect execution semantics."""
    execution_context = getattr(ctx, "execution_context", "isolated")
    run_type = getattr(ctx, "run_type", "incremental")
    execution_context_value = (
        execution_context.value
        if isinstance(execution_context, Enum)
        else str(execution_context)
    )
    return {
        "pipeline_name": ctx.pipeline_name,
        "run_type": run_type.value if isinstance(run_type, Enum) else str(run_type),
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
        "input_filter": _to_serializable_mapping(getattr(ctx, "input_filter", None)),
        "cached_bronze": _to_serializable_mapping(
            getattr(ctx, "cached_bronze", None)
        ),
    }


def _build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned layer roots for the manifest control-plane snapshot."""
    output_root = Path(getattr(settings, "data_dir", "data")) / "output"
    return (
        RunArtifactRef(layer="bronze", path=str(output_root / "bronze" / provider / entity)),
        RunArtifactRef(layer="silver", path=str(output_root / "silver" / provider / entity)),
        RunArtifactRef(layer="gold", path=str(output_root / "gold" / provider / entity)),
    )


def _control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return Path(getattr(settings, "data_dir", "data")) / "output" / "control" / leaf


def create_run_manifest(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
) -> tuple[str, RunLedgerService | None]:
    """Create immutable manifest before pipeline assembly begins."""
    yaml_config = inputs.yaml_config
    provider, entity = _resolve_provider_entity(
        pipeline_name=ctx.pipeline_name,
        yaml_config=yaml_config,
    )
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(inputs.settings, "run_manifest")
    )
    ledger_service: RunLedgerService | None = None
    if ledger_enabled:
        ledger_service = RunLedgerService(
            ledger_port=FileRunLedgerStore(
                base_path=_control_plane_root(inputs.settings, "run_ledger")
            ),
            manifest_id="pending",
            run_id=ctx.run_id,
        )
    manifest = RunManifestService(manifest_port=manifest_store).create_manifest(
        RunManifestCreateRequest(
            run_id=ctx.run_id,
            run_type=getattr(ctx, "run_type", "incremental"),
            pipeline_name=ctx.pipeline_name,
            provider=provider,
            entity=entity,
            launch_context=_build_launch_context_snapshot(ctx),
            runtime_config=_to_serializable_mapping(inputs.runtime_config),
            resolved_config=_to_serializable_mapping(yaml_config),
            source_refs=(
                RunSourceRef(
                    provider=provider,
                    entity=entity,
                    pipeline_name=ctx.pipeline_name,
                    query=getattr(ctx, "query", None),
                ),
            ),
            planned_artifacts=_build_planned_artifacts(
                settings=inputs.settings,
                provider=provider,
                entity=entity,
            ),
            pipeline_version=get_pipeline_version(yaml_config),
            git_commit=get_git_commit(),
            config_hash=_compute_manifest_config_hash(yaml_config),
        )
    )
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)
    return manifest.manifest_id, ledger_service


def attach_manifest_id(ctx: PipelineRunContext, manifest_id: str) -> PipelineRunContext:
    """Return context carrying manifest_id while tolerating unit-test stubs."""
    if is_dataclass(ctx):
        return replace(ctx, manifest_id=manifest_id)
    if hasattr(ctx, "__dict__"):
        ctx.manifest_id = manifest_id  # type: ignore[attr-defined]
        return ctx
    raise TypeError("PipelineRunContext must support manifest_id attachment")


def _record_artifact(
    service: RunLedgerService,
    *,
    layer: str,
    artifact_path: str,
    details: dict[str, object] | None,
) -> object:
    """Record one published artifact in the control-plane ledger."""
    return service.record_artifact_published(
        layer=layer,
        artifact_path=artifact_path,
        details=details,
    )


def _attach_artifact_recorder(
    target: object,
    service: RunLedgerService,
) -> None:
    """Attach an artifact-recorder callback to one metadata writer when supported."""
    attach = getattr(target, "attach_artifact_recorder", None)
    if callable(attach):
        attach(
            lambda layer, artifact_path, details=None: _record_artifact(
                service,
                layer=layer,
                artifact_path=artifact_path,
                details=details,
            )
        )


def attach_control_plane_collaborators(
    runner: PipelineRunner,
    run_ledger_service: RunLedgerService,
) -> None:
    """Attach ledger collaborators to the runner and its metadata writers."""
    runner.attach_run_ledger_service(run_ledger_service)

    services = getattr(runner, "services", None)
    if services is None:
        return

    candidates: list[object] = []
    metadata_writer = getattr(services, "metadata_writer", None)
    if metadata_writer is not None:
        candidates.append(metadata_writer)

    storage = getattr(services, "storage", None)
    if storage is not None:
        for writer_name in ("bronze", "silver", "gold"):
            writer = getattr(storage, writer_name, None)
            if writer is None:
                continue
            writer_metadata = getattr(writer, "_metadata_writer", None)
            if writer_metadata is not None:
                candidates.append(writer_metadata)

    seen: set[int] = set()
    for candidate in candidates:
        candidate_id = id(candidate)
        if candidate_id in seen:
            continue
        seen.add(candidate_id)
        _attach_artifact_recorder(candidate, run_ledger_service)
