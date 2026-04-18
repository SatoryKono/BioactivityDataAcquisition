from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, cast
from uuid import UUID

if TYPE_CHECKING:
    from _typeshed import DataclassInstance

    from bioetl.domain.context import PipelineRunContext


def normalize_snapshot(value: object) -> object:
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
    """Build a snapshot of the launch context."""
    snapshot = _build_base_snapshot(ctx, run_type_value, execution_context_value)
    snapshot.update({
        "required_persistence_profile": required_persistence_profile,
        "exact_replay_support_boundary": _determine_replay_support_boundary(execution_context_value),
    })
    _add_optional_fields(snapshot, ctx)
    return snapshot


def _build_base_snapshot(
    ctx: PipelineRunContext,
    run_type_value: str,
    execution_context_value: str,
) -> dict[str, object]:
    """Build the base snapshot."""
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
    }


def _determine_replay_support_boundary(execution_context_value: str) -> str:
    """Determine the replay support boundary."""
    return (
        "snapshot_backed_source_runs_only"
        if execution_context_value != "composite"
        else "composite_execution_unsupported"
    )


def _add_optional_fields(snapshot: dict[str, object], ctx: PipelineRunContext) -> None:
    """Add optional fields to the snapshot."""
    snapshot["vacuum"] = to_serializable_mapping(getattr(ctx, "vacuum", None))
    snapshot["input_filter"] = to_serializable_mapping(getattr(ctx, "input_filter", None))
    snapshot["cached_bronze"] = to_serializable_mapping(getattr(ctx, "cached_bronze", None))


def resolve_replay_parentage(
    *,
    ctx: PipelineRunContext,
    runtime_config: object,
) -> tuple[str | None, str | None]:
    """Resolve the replay parentage."""
    runtime_config_mapping = _as_runtime_config_mapping(runtime_config)
    replay_of_run_id = _resolve_replay_id(ctx, "replay_of_run_id", runtime_config_mapping)
    replay_of_manifest_id = _resolve_replay_id(ctx, "replay_of_manifest_id", runtime_config_mapping)
    return replay_of_run_id, replay_of_manifest_id


def _resolve_replay_id(
    ctx: PipelineRunContext,
    attr_name: str,
    runtime_config_mapping: Mapping[str, object],
) -> str | None:
    """Resolve the replay ID from context or runtime config."""
    ctx_value = _coerce_optional_text(getattr(ctx, attr_name, None))
    if ctx_value is not None:
        return ctx_value
    
    keys = (attr_name, f"exact_replay_parent_{attr_name}")
    return _resolve_replay_parentage_mapping_value(runtime_config_mapping, *keys)


def resolve_provider_entity(
    *,
    pipeline_name: str,
    yaml_config: object,
) -> tuple[str, str]:
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


def _as_runtime_config_mapping(runtime_config: object) -> Mapping[str, object]:
    if isinstance(runtime_config, Mapping):
        return runtime_config
    return {}


def _resolve_replay_parentage_mapping_value(
    runtime_config: Mapping[str, object],
    *keys: str,
) -> str | None:
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


def _resolve_name_component(value: object, *, fallback: str) -> str:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return fallback


def _coerce_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
