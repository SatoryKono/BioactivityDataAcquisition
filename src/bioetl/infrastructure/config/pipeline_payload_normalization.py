"""Pipeline payload normalization helpers for config-loader orchestration.

Keeps convention defaults, source merging, and legacy/new-shape schema
normalization behind one infrastructure boundary so ``config_loader`` can stay
focused on read -> validate -> map orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config.pipeline_normalizers import (
    apply_pipeline_schema_normalization,
)
from bioetl.infrastructure.config.source_config_loader import load_source_config
from bioetl.infrastructure.config_loader_filtering import (
    apply_hierarchical_filter_config,
)
from bioetl.infrastructure.config_merge import config_merge


@dataclass(frozen=True)
class PipelineConfigReadPayload:
    """Raw payload + context produced by pipeline-config read stage."""

    config: JsonDict  # Any: YAML config has heterogeneous values
    entity_config: JsonDict  # Any: YAML config has heterogeneous values
    config_path: Path
    unified_schema: JsonDict | None = None  # Any: YAML values are heterogeneous


def _apply_file_reference_defaults(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
) -> None:
    """Apply convention-based defaults for file references."""
    config.setdefault("source_file", f"../../providers/{provider}.yaml")
    config.setdefault("dq_config_file", f"../../entities/{provider}/{entity_type}.yaml")
    config.setdefault(
        "filter_config_file",
        f"../../entities/{provider}/{entity_type}.yaml",
    )


def _apply_layer_defaults(
    layer: JsonDict,  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
    layer_name: str,
    sort_policy: list[str],
) -> None:
    """Apply convention-based defaults for a single medallion layer."""
    layer.setdefault("path", f"data/output/{layer_name}/{provider}/{entity_type}")
    if layer_name in {"silver", "gold"}:
        layer.setdefault("sort_by", list(sort_policy))

    csv_export = layer.setdefault("csv_export", {})
    csv_export.setdefault("path", layer["path"])


def apply_convention_defaults(
    config: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Apply convention-based defaults for paths, references, and table names."""
    provider = config.get("provider")
    entity_type = config.get("entity_type")

    if not provider or not entity_type:
        return config

    raw_primary_keys = config.get("business_primary_keys") or config.get(
        "primary_keys", []
    )
    primary_keys = [str(key) for key in raw_primary_keys if str(key).strip()]
    technical_primary_key = str(config.get("technical_primary_key", "entity_id"))
    sort_policy = [technical_primary_key] + [
        key for key in primary_keys if key != technical_primary_key
    ]
    _apply_file_reference_defaults(config, provider, entity_type)

    table_name = f"{provider}_{entity_type}"
    config.setdefault("silver_table", table_name)
    config.setdefault("gold_table", table_name)

    sink = config.setdefault("sink", {})
    for layer_name in ("bronze", "silver", "gold"):
        layer = sink.setdefault(layer_name, {})
        _apply_layer_defaults(layer, provider, entity_type, layer_name, sort_policy)

    return config


def load_source_section(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: Path,
) -> None:
    """Load source config from external file and merge with entity overrides."""
    source_file = config.get("source_file")
    if not source_file:
        return
    provider = config.get("provider")
    if not isinstance(provider, str) or not provider:
        return

    del config_path
    try:
        source_config = load_source_config(provider)
    except ValueError:
        return

    base_source = source_config.model_dump(exclude_none=True).get("source", {})
    entity_source = config.get("source", {})
    config["source"] = config_merge(base_source, entity_source)


def normalize_pipeline_payload(
    payload: PipelineConfigReadPayload,
    *,
    filter_loader: FilterConfigLoader,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Normalize pipeline payload before validation."""
    config = apply_convention_defaults(payload.config.copy())
    apply_hierarchical_filter_config(
        config,
        payload.entity_config,
        filter_loader=filter_loader,
    )
    apply_pipeline_schema_normalization(
        config,
        entity_config=payload.entity_config,
        config_path=payload.config_path,
        unified_schema=payload.unified_schema,
    )
    load_source_section(config, payload.config_path)

    for key in ("source_file", "data_schema", "filter_defaults", "contract_defaults"):
        config.pop(key, None)
    for key in ("schema_file", "data_schema_file", "column_groups_file"):
        config.pop(key, None)
    return config


__all__ = [
    "PipelineConfigReadPayload",
    "apply_convention_defaults",
    "load_source_section",
    "normalize_pipeline_payload",
]
