"""Run manifest creation for control-plane."""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

import yaml

from bioetl.application.services.run_ledger_service import RunLedgerService
from bioetl.application.services.run_manifest_service import (
    RunManifestCreateRequest,
    RunManifestService,
)
from bioetl.composition.services.versioning import (
    get_git_commit,
    get_pipeline_version,
)
from bioetl.domain.control_plane import RunArtifactRef, RunSourceRef
from bioetl.infrastructure.control_plane import FileRunManifestStore

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


def _build_launch_context_snapshot(
    ctx: PipelineRunContext,
    *,
    run_type_value: str,
    execution_context_value: str,
) -> dict[str, object]:
    """Capture launch-time options that materially affect execution semantics."""
    return {
        "pipeline_name": str(ctx.pipeline_name),
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
        "input_filter": _to_serializable_mapping(getattr(ctx, "input_filter", None)),
        "cached_bronze": _to_serializable_mapping(getattr(ctx, "cached_bronze", None)),
    }


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


def _coerce_optional_text(value: object) -> str | None:
    """Return normalized non-empty text when available."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_contract_identity(
    *,
    provider: str,
    entity: str,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Resolve contract identity fields from canonical registry when available."""
    contract_ref = f"{provider}.{entity}"
    registry_path = Path("configs/base/contract_registry.yaml")
    if not registry_path.exists():
        return contract_ref, None, None, None, None
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return contract_ref, None, None, None, None
    if not isinstance(payload, dict):
        return contract_ref, None, None, None, None
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return contract_ref, None, None, None, None
    entry = entries.get(contract_ref)
    if not isinstance(entry, dict):
        return contract_ref, None, None, None, None
    identity = entry.get("identity")
    identity_payload = identity if isinstance(identity, dict) else {}
    contract_version = _coerce_optional_text(identity_payload.get("contract_version"))
    contract_schema_hash = _coerce_optional_text(identity_payload.get("schema_hash"))
    dq_policy_ref = _coerce_optional_text(
        identity_payload.get("dq_policy_ref") or entry.get("dq_policy_ref")
    )
    rule_bundle_version = _coerce_optional_text(
        identity_payload.get("rule_bundle_version") or entry.get("rule_bundle_version")
    )
    return (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    )


def _build_planned_artifacts(
    *,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunArtifactRef, ...]:
    """Capture planned layer roots for the manifest control-plane snapshot."""
    output_root = Path(getattr(settings, "data_dir", "data")) / "output"
    return (
        RunArtifactRef(
            layer="bronze", path=str(output_root / "bronze" / provider / entity)
        ),
        RunArtifactRef(
            layer="silver", path=str(output_root / "silver" / provider / entity)
        ),
        RunArtifactRef(
            layer="gold", path=str(output_root / "gold" / provider / entity)
        ),
    )


def _control_plane_root(settings: Settings, leaf: str) -> Path:
    """Return the canonical control-plane output root for one leaf namespace."""
    return Path(getattr(settings, "data_dir", "data")) / "output" / "control" / leaf


@dataclass(frozen=True, slots=True)
class _ManifestControlPlaneRefs:
    """Resolved control-plane references produced before factory runner wiring."""

    manifest_id: str
    config_hash: str | None
    dq_contract_compatibility_hash: str | None
    effective_config_artifact_id: str | None
    contract_ref: str | None
    contract_version: str | None
    contract_schema_hash: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None


def _resolve_run_context_values(
    ctx: PipelineRunContext,
) -> tuple[str, str]:
    """Resolve run type and execution context values from context."""
    raw_run_type = getattr(ctx, "run_type", "incremental")
    run_type_value = str(getattr(raw_run_type, "value", raw_run_type))
    raw_execution_context = getattr(ctx, "execution_context", "isolated")
    execution_context_value = str(
        getattr(raw_execution_context, "value", raw_execution_context)
    )
    return run_type_value, execution_context_value


def _create_ledger_service(
    inputs: RunnerInputs,
    ctx: PipelineRunContext,
) -> RunLedgerService | None:
    """Create ledger service if enabled."""
    from bioetl.application.services.run_ledger_service import RunLedgerService
    from bioetl.infrastructure.control_plane import FileRunLedgerStore

    return RunLedgerService(
        ledger_port=FileRunLedgerStore(
            base_path=_control_plane_root(inputs.settings, "run_ledger"),
            metrics=inputs.observability.metrics,
        ),
        manifest_id="pending",
        run_id=ctx.run_id,
    )


def _build_manifest_create_request(
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    provider: str,
    entity: str,
    run_type_value: str,
    execution_context_value: str,
    effective_config_hash: str,
    contract_ref: str,
    contract_version: str,
    contract_schema_hash: str,
    dq_policy_ref: str,
    rule_bundle_version: str,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
) -> RunManifestCreateRequest:
    """Build the manifest create request."""
    yaml_config = inputs.yaml_config
    return RunManifestCreateRequest(
        run_id=ctx.run_id,
        run_type=getattr(ctx, "run_type", "incremental"),
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
        launch_context=_build_launch_context_snapshot(
            ctx,
            run_type_value=run_type_value,
            execution_context_value=execution_context_value,
        ),
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
        config_hash=effective_config_hash,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
    )


def _create_control_plane_refs(
    manifest: RunManifest,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
    effective_config_artifact_id: str,
    contract_ref: str,
    contract_version: str,
    contract_schema_hash: str,
    dq_policy_ref: str,
    rule_bundle_version: str,
) -> _ManifestControlPlaneRefs:
    """Create control plane references from manifest."""
    return _ManifestControlPlaneRefs(
        manifest_id=manifest.manifest_id,
        config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        contract_ref=contract_ref,
        contract_version=contract_version,
        contract_schema_hash=contract_schema_hash,
        dq_policy_ref=dq_policy_ref,
        rule_bundle_version=rule_bundle_version,
    )


def create_run_manifest(
    *,
    ctx: PipelineRunContext,
    inputs: RunnerInputs,
    ledger_enabled: bool,
    effective_config_artifact_id: str,
    effective_config_hash: str,
    dq_contract_compatibility_hash: str,
) -> tuple[_ManifestControlPlaneRefs, RunLedgerService | None]:
    """Create immutable manifest before pipeline assembly begins."""
    yaml_config = inputs.yaml_config
    
    # Resolve context values
    run_type_value, execution_context_value = _resolve_run_context_values(ctx)
    
    # Resolve provider and entity
    provider, entity = _resolve_provider_entity(
        pipeline_name=ctx.pipeline_name,
        yaml_config=yaml_config,
    )
    
    # Resolve contract identity
    (
        contract_ref,
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    ) = _resolve_contract_identity(provider=provider, entity=entity)
    
    # Create manifest store
    manifest_store = FileRunManifestStore(
        base_path=_control_plane_root(inputs.settings, "run_manifest"),
        metrics=inputs.observability.metrics,
    )
    
    # Create ledger service if enabled
    ledger_service: RunLedgerService | None = None
    if ledger_enabled:
        ledger_service = _create_ledger_service(inputs, ctx)
    
    # Build and create manifest
    manifest_create_request = _build_manifest_create_request(
        ctx, inputs, provider, entity, run_type_value, execution_context_value,
        effective_config_hash, contract_ref, contract_version, contract_schema_hash,
        dq_policy_ref, rule_bundle_version, dq_contract_compatibility_hash,
        effective_config_artifact_id
    )
    
    manifest = RunManifestService(manifest_port=manifest_store).create_manifest(
        manifest_create_request
    )
    
    # Update ledger service with manifest ID
    if ledger_service is not None:
        ledger_service.manifest_id = manifest.manifest_id
        ledger_service.record_manifest_created(manifest)
    
    # Create control plane references
    control_plane_refs = _create_control_plane_refs(
        manifest, effective_config_hash, dq_contract_compatibility_hash,
        effective_config_artifact_id, contract_ref, contract_version,
        contract_schema_hash, dq_policy_ref, rule_bundle_version
    )
    
    return control_plane_refs, ledger_service
