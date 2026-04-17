"""Private support helpers for control-plane manifest creation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, cast
from uuid import UUID

import yaml

from bioetl.composition.runtime_builders._cached_bronze_snapshot_support import (
    build_cached_bronze_input_snapshot_refs,
)
from bioetl.composition.runtime_builders._run_manifest_refs import (
    ManifestControlPlaneRefs,
    build_planned_artifacts,
    control_plane_root,
    create_control_plane_refs,
    resolve_run_context_values,
)
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunSourceRef,
)

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config import Settings

__all__ = [
    "ManifestControlPlaneRefs",
    "build_launch_context_snapshot",
    "build_planned_artifacts",
    "build_run_source_refs",
    "control_plane_root",
    "create_control_plane_refs",
    "normalize_snapshot",
    "resolve_contract_identity",
    "resolve_provider_entity",
    "resolve_replay_capability",
    "resolve_replay_parentage",
    "resolve_run_context_values",
    "to_serializable_mapping",
]


def normalize_snapshot(value: object) -> object:
    """Normalize dataclass/Pydantic values into JSON-safe primitives."""
    if not isinstance(value, type) and is_dataclass(value):
        return normalize_snapshot(asdict(cast("DataclassInstance", value)))
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return normalize_snapshot(
            {key: item for key, item in vars(value).items() if not key.startswith("_")}
        )
    if isinstance(value, dict):
        return {str(key): normalize_snapshot(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [normalize_snapshot(item) for item in value]
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID):
        return str(value)
    return value


def to_serializable_mapping(value: object) -> dict[str, object]:
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
        payload = normalize_snapshot(value)
    if not isinstance(payload, dict):
        return {"value": normalize_snapshot(payload)}
    normalized = normalize_snapshot(payload)
    if not isinstance(normalized, dict):
        raise TypeError("Manifest snapshot normalization must return a mapping")
    return normalized


def build_launch_context_snapshot(
    ctx: PipelineRunContext,
    *,
    run_type_value: str,
    execution_context_value: str,
    required_persistence_profile: str,
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
        "exact_replay": getattr(ctx, "exact_replay", False),
        "execution_context": execution_context_value,
        "required_persistence_profile": required_persistence_profile,
        "exact_replay_support_boundary": (
            "snapshot_backed_source_runs_only"
            if execution_context_value != "composite"
            else "composite_execution_unsupported"
        ),
        "vacuum": to_serializable_mapping(getattr(ctx, "vacuum", None)),
        "input_filter": to_serializable_mapping(getattr(ctx, "input_filter", None)),
        "cached_bronze": to_serializable_mapping(getattr(ctx, "cached_bronze", None)),
    }


def resolve_replay_parentage(
    *,
    ctx: PipelineRunContext,
    runtime_config: object,
) -> tuple[str | None, str | None]:
    """Resolve explicit replay ancestry from context or runtime configuration."""
    runtime_config_mapping = _as_runtime_config_mapping(runtime_config)
    replay_of_run_id = _coerce_optional_text(getattr(ctx, "replay_of_run_id", None))
    replay_of_manifest_id = _coerce_optional_text(
        getattr(ctx, "replay_of_manifest_id", None)
    )
    if replay_of_run_id is None:
        replay_of_run_id = _resolve_replay_parentage_mapping_value(
            runtime_config_mapping,
            "replay_of_run_id",
            "exact_replay_parent_run_id",
        )
    if replay_of_manifest_id is None:
        replay_of_manifest_id = _resolve_replay_parentage_mapping_value(
            runtime_config_mapping,
            "replay_of_manifest_id",
            "exact_replay_parent_manifest_id",
        )
    return replay_of_run_id, replay_of_manifest_id


def _as_runtime_config_mapping(runtime_config: object) -> Mapping[str, object]:
    """Return a mapping view for runtime-config lookups or an empty mapping."""
    if isinstance(runtime_config, Mapping):
        return runtime_config
    return {}


def _resolve_replay_parentage_mapping_value(
    runtime_config: Mapping[str, object],
    *keys: str,
) -> str | None:
    """Resolve one replay parentage field from known runtime-config locations."""
    for key in keys:
        direct_value = _coerce_optional_text(runtime_config.get(key))
        if direct_value is not None:
            return direct_value
        control_plane = runtime_config.get("control_plane")
        if isinstance(control_plane, Mapping):
            nested_value = _coerce_optional_text(control_plane.get(key))
            if nested_value is not None:
                return nested_value
        pipeline = runtime_config.get("pipeline")
        if isinstance(pipeline, Mapping):
            nested_direct = _coerce_optional_text(pipeline.get(key))
            if nested_direct is not None:
                return nested_direct
            nested_control_plane = pipeline.get("control_plane")
            if isinstance(nested_control_plane, Mapping):
                nested_value = _coerce_optional_text(nested_control_plane.get(key))
                if nested_value is not None:
                    return nested_value
    return None


def resolve_provider_entity(
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
    provider = _resolve_name_component(
        getattr(yaml_config, "provider", None),
        fallback=fallback_provider,
    )
    entity = _resolve_name_component(
        getattr(yaml_config, "entity_type", None),
        fallback=fallback_entity,
    )
    return provider, entity


def _resolve_name_component(value: object, *, fallback: str) -> str:
    """Return a canonical provider/entity component or fall back safely.

    ``MagicMock`` and other object doubles frequently expose arbitrary attributes
    in tests; they must not leak into manifest ``contract_ref`` values.
    """
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return fallback


def build_run_source_refs(
    *,
    ctx: PipelineRunContext,
    cached_bronze: object | None,
    settings: Settings,
    provider: str,
    entity: str,
) -> tuple[RunSourceRef, ...]:
    """Build manifest source refs, including cached-Bronze snapshot provenance."""
    input_snapshots = _build_cached_bronze_snapshot_refs(
        cached_bronze=cached_bronze,
        settings=settings,
        pipeline_name=ctx.pipeline_name,
        provider=provider,
        entity=entity,
    )
    if getattr(ctx, "exact_replay", False) and not input_snapshots:
        raise RuntimeError(
            "Exact replay requires immutable input snapshots; no snapshot-backed source refs were resolved for this run"
        )
    return (
        RunSourceRef(
            provider=provider,
            entity=entity,
            pipeline_name=ctx.pipeline_name,
            query=getattr(ctx, "query", None),
            input_snapshots=input_snapshots,
        ),
    )


def resolve_replay_capability(
    *,
    source_refs: tuple[RunSourceRef, ...],
    resume_requested: bool,
) -> ReplayCapability:
    """Classify control-plane replay capability for one manifested run."""
    has_input_snapshots = any(ref.input_snapshots for ref in source_refs)
    if has_input_snapshots:
        return ReplayCapability.EXACT_REPLAY_SUPPORTED
    if resume_requested:
        return ReplayCapability.RESUME_ONLY
    return ReplayCapability.REBUILD_ONLY


def _build_cached_bronze_snapshot_refs(
    *,
    cached_bronze: object | None,
    settings: Settings,
    pipeline_name: str,
    provider: str,
    entity: str,
) -> tuple[RunInputSnapshotRef, ...]:
    """Build immutable snapshot refs for cached-Bronze executions."""
    if cached_bronze is None or not getattr(cached_bronze, "enabled", False):
        return ()
    bronze_path = getattr(cached_bronze, "bronze_path", None)
    bronze_date = getattr(cached_bronze, "bronze_date", None)
    bronze_root = (
        Path(str(bronze_path))
        if bronze_path is not None
        else settings.bronze_path / provider / entity
    )
    snapshot_refs = build_cached_bronze_input_snapshot_refs(
        bronze_root=bronze_root,
        bronze_date=cast("str | None", bronze_date),
        pipeline_name=pipeline_name,
    )
    if not snapshot_refs:
        raise RuntimeError(
            "Cached Bronze execution requires at least one persisted batch file for snapshot provenance"
        )
    return snapshot_refs


def _coerce_optional_text(value: object) -> str | None:
    """Return normalized non-empty text when available."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def resolve_contract_identity(
    *,
    provider: str,
    entity: str,
) -> tuple[str, str | None, str | None, str | None, str | None]:
    """Resolve contract identity fields from canonical registry when available."""
    contract_ref = f"{provider}.{entity}"
    registry_path = Path("configs/base/contract_registry.yaml")
    if not registry_path.exists():
        return contract_ref, None, None, None, None
    entry = _load_contract_registry_entry(registry_path, contract_ref)
    if entry is None:
        return contract_ref, None, None, None, None
    return (contract_ref, *_extract_contract_identity_fields(entry))


def _load_contract_registry_entry(
    registry_path: Path,
    contract_ref: str,
) -> dict[str, object] | None:
    """Load one contract-registry entry when the registry is valid."""
    payload = _read_contract_registry_payload(registry_path)
    if payload is None:
        return None
    entries = payload.get("entries")
    if not isinstance(entries, dict):
        return None
    entry = entries.get(contract_ref)
    if not isinstance(entry, dict):
        return None
    return entry


def _read_contract_registry_payload(
    registry_path: Path,
) -> dict[str, object] | None:
    """Read and validate contract registry payload."""
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _extract_contract_identity_fields(
    entry: dict[str, object],
) -> tuple[str | None, str | None, str | None, str | None]:
    """Extract normalized identity fields from one registry entry."""
    identity_payload = _identity_payload(entry)
    contract_version = _coerce_optional_text(identity_payload.get("contract_version"))
    contract_schema_hash = _coerce_optional_text(identity_payload.get("schema_hash"))
    dq_policy_ref = _coerce_optional_text(
        identity_payload.get("dq_policy_ref") or entry.get("dq_policy_ref")
    )
    rule_bundle_version = _coerce_optional_text(
        identity_payload.get("rule_bundle_version") or entry.get("rule_bundle_version")
    )
    return (
        contract_version,
        contract_schema_hash,
        dq_policy_ref,
        rule_bundle_version,
    )


def _identity_payload(entry: Mapping[str, object]) -> Mapping[str, object]:
    """Return normalized identity payload for one registry entry."""
    identity = entry.get("identity")
    if isinstance(identity, Mapping):
        return identity
    return {}
