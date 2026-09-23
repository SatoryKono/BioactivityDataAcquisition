"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import (
    _as_mapping,
    _coerce_int,
    _optional_text,
    _rel_path,
)
from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.add_file_structure_zone import _field_quality_index
from memory.graph.sync_pkg.graph_contexts import EntityPipelineContext
from memory.graph.sync_pkg.merge_field_validation_item import _merged_maintenance_config
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _entity_pipeline_sink_config,
)

__all__ = [
    "_entity_storage_context",
]


def _entity_storage_context(
    root: Path,
    entity_path: Path,
    payload: dict[str, object],
    *,
    today: str,
    base_payload: dict[str, object],
) -> tuple[
    EntityPipelineContext,
    dict[str, object],
    dict[str, dict[str, JsonValue]],
]:
    provider_name = str(payload.get("provider", entity_path.parent.name))
    entity_name = str(payload.get("entity", entity_path.stem))
    pipeline_payload = _as_mapping(payload.get("pipeline"))
    pipeline_name = str(
        pipeline_payload.get("pipeline_name", f"{provider_name}_{entity_name}")
    )
    maintenance_config = _merged_maintenance_config(base_payload, payload)
    retention_days = maintenance_config.get("vacuum_retention_days")
    quality_payload = _as_mapping(payload.get("quality"))
    context = EntityPipelineContext(
        provider_name=provider_name,
        entity_name=entity_name,
        pipeline_name=pipeline_name,
        pipeline_key=NodeKey("pipeline_surface", pipeline_name),
        entity_key=NodeKey("entity_config", pipeline_name),
        config_artifact=NodeKey("config_artifact", _rel_path(root, entity_path)),
        today=today,
        contract_ref=f"{provider_name}.{entity_name}",
        retention_days=_coerce_int(retention_days)
        if isinstance(retention_days, int | float)
        else None,
        config_version=_optional_text(payload.get("version")),
        quality_version=_optional_text(quality_payload.get("version")),
    )
    pipeline_sink = _entity_pipeline_sink_config(payload)
    return context, pipeline_sink, _field_quality_index(payload)
