"""Serialization helpers for CompositeConfig."""

from __future__ import annotations

from typing import Any

from collections.abc import Callable, Mapping

from bioetl.domain.composite.config_composite_protocols import (
    CompositeConfigProtocol,
)
from bioetl.domain.composite.config_cross_validation import CrossValidationConfig
from bioetl.domain.composite.config_dq import CompositeDQConfig, DQOverrideConfig
from bioetl.domain.composite.config_parsing import (
    optional_bool,
    optional_int,
    optional_str,
    optional_str_tuple,
    require_object_dict,
    require_object_dict_sequence,
    require_str,
    require_str_tuple,
)
from bioetl.domain.composite.config_runtime import ExecutionConfig, LineageConfig
from bioetl.domain.composite.cross_validation import (
    ComparisonMethod,
    EnricherFieldPairing,
    FieldComparisonSpec,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

__all__ = [
    "composite_from_dict",
    "composite_to_dict",
]


def _build_seed_config[ConfigT](
    seed_data: dict[str, object],
    seed_cls: Callable[..., ConfigT],
) -> ConfigT:
    """Build seed config from parsed seed mapping."""
    return seed_cls(
        pipeline=require_str(seed_data.get("pipeline"), "seed.pipeline"),
        output_keys=require_str_tuple(seed_data.get("output_keys"), "seed.output_keys"),
        silver_table=require_str(seed_data.get("silver_table"), "seed.silver_table"),
        limit=optional_int(seed_data.get("limit"), "seed.limit"),
    )


def _build_dependency_config[ConfigT](
    dep: dict[str, object],
    dependency_cls: Callable[..., ConfigT],
) -> ConfigT:
    """Build one dependency config from serialized mapping."""
    return dependency_cls(
        pipeline=require_str(dep.get("pipeline"), "dependencies[].pipeline"),
        join_keys=require_str_tuple(dep.get("join_keys"), "dependencies[].join_keys"),
        required=optional_bool(dep.get("required"), False, "dependencies[].required"),
        timeout_seconds=optional_int(
            dep.get("timeout_seconds"),
            "dependencies[].timeout_seconds",
            600,
        ),
        silver_table=optional_str(
            dep.get("silver_table"), "dependencies[].silver_table"
        ),
        key_source=optional_str(dep.get("key_source"), "dependencies[].key_source"),
        filter_field=optional_str(
            dep.get("filter_field"), "dependencies[].filter_field"
        ),
        filter_fields=optional_str_tuple(
            dep.get("filter_fields"), "dependencies[].filter_fields"
        ),
        key_filter=optional_str(dep.get("key_filter"), "dependencies[].key_filter"),
    )


def _build_dependency_configs[ConfigT](
    dependency_data: list[dict[str, object]],
    dependency_cls: Callable[..., ConfigT],
) -> tuple[ConfigT, ...]:
    """Build dependency config tuple."""
    return tuple(
        _build_dependency_config(dep, dependency_cls) for dep in dependency_data
    )


def _build_enricher_config[ConfigT](
    enricher: dict[str, object],
    enricher_cls: Callable[..., ConfigT],
) -> ConfigT:
    """Build one enricher config from serialized mapping."""
    kwargs: dict[str, object] = {
        "pipeline": require_str(enricher.get("pipeline"), "enrichers[].pipeline"),
        "join_keys": require_str_tuple(
            enricher.get("join_keys"), "enrichers[].join_keys"
        ),
        "required": optional_bool(
            enricher.get("required"), False, "enrichers[].required"
        ),
        "timeout_seconds": optional_int(
            enricher.get("timeout_seconds"),
            "enrichers[].timeout_seconds",
            600,
        ),
        "filter_condition": optional_str(
            enricher.get("filter_condition"), "enrichers[].filter_condition"
        ),
        "silver_table": optional_str(
            enricher.get("silver_table"), "enrichers[].silver_table"
        ),
        "limit": optional_int(enricher.get("limit"), "enrichers[].limit"),
    }
    if enricher.get("fallback_strategy") is not None:
        kwargs["fallback_strategy"] = enricher.get("fallback_strategy")
    if enricher.get("cardinality") is not None:
        kwargs["cardinality"] = enricher.get("cardinality")
    if enricher.get("aggregation") is not None:
        kwargs["aggregation"] = enricher.get("aggregation")
    return enricher_cls(**kwargs)


def _build_enricher_configs[ConfigT](
    enricher_data: list[dict[str, object]],
    enricher_cls: Callable[..., ConfigT],
) -> tuple[ConfigT, ...]:
    """Build enricher config tuple."""
    return tuple(
        _build_enricher_config(enricher, enricher_cls) for enricher in enricher_data
    )



def _optional_str_tuple_map(
    raw: object,
    *,
    value_as_tuple: bool,
) -> dict[str, object]:
    """Parse optional mapping of str keys to str or tuple[str, ...]."""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, object] = {}
    for key, value in raw.items():
        key_s = str(key)
        if value_as_tuple:
            if isinstance(value, list | tuple):
                result[key_s] = tuple(str(item) for item in value)
            else:
                result[key_s] = (str(value),)
        else:
            result[key_s] = str(value)
    return result


def _str_str_map(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _build_merge_config[ConfigT](
    merge_data: dict[str, object],
    merge_cls: Callable[..., ConfigT],
) -> ConfigT:
    """Build merge config from serialized mapping."""
    return merge_cls(
        strategy=MergeStrategy.from_string(
            require_str(merge_data.get("strategy"), "merge.strategy")
        ),
        conflict_resolution=ConflictResolution.from_string(
            require_str(
                merge_data.get("conflict_resolution"), "merge.conflict_resolution"
            )
        ),
        output_silver_path=require_str(
            merge_data.get("output_silver_path"), "merge.output_silver_path"
        ),
        output_gold_path=require_str(
            merge_data.get("output_gold_path"), "merge.output_gold_path"
        ),
        sort_by_silver=optional_str_tuple(
            merge_data.get("sort_by_silver"), "merge.sort_by_silver"
        )
        or (),
        sort_by_gold=optional_str_tuple(
            merge_data.get("sort_by_gold"), "merge.sort_by_gold"
        )
        or (),
        field_priorities=_optional_str_tuple_map(  # type: ignore[arg-type]
            merge_data.get("field_priorities"), value_as_tuple=True
        ),  # type: ignore[arg-type]
        normalization_compatibility_overrides=_str_str_map(
            merge_data.get("normalization_compatibility_overrides")
        ),
        field_mappings=_str_str_map(merge_data.get("field_mappings")),
        column_groups=merge_data.get("column_groups") or (),
        exclude_fields=optional_str_tuple(
            merge_data.get("exclude_fields"), "merge.exclude_fields"
        )
        or (),
        preserve_all_sources=optional_bool(
            merge_data.get("preserve_all_sources"),
            False,
            "merge.preserve_all_sources",
        ),
    )



def _dependency_entry(dependency: Any) -> dict[str, object]:
    """Serialize one dependency node for composite_to_dict."""
    entry: dict[str, object] = {
        "pipeline": dependency.pipeline,
        "join_keys": list(dependency.join_keys),
        "required": dependency.required,
        "timeout_seconds": dependency.timeout_seconds,
        "silver_table": dependency.silver_table,
        "key_source": dependency.key_source,
        "filter_field": dependency.filter_field,
        "key_filter": dependency.key_filter,
    }
    filter_fields = getattr(dependency, "filter_fields", None)
    if filter_fields:
        entry["filter_fields"] = list(filter_fields)
    return entry



def _enricher_entry(enricher: Any) -> dict[str, object]:
    """Serialize one enricher node for composite_to_dict."""
    entry: dict[str, object] = {
        "pipeline": enricher.pipeline,
        "join_keys": list(enricher.join_keys),
        "required": enricher.required,
        "timeout_seconds": enricher.timeout_seconds,
        "filter_condition": enricher.filter_condition,
        "silver_table": enricher.silver_table,
        "limit": enricher.limit,
        "fallback_strategy": enricher.fallback_strategy.value,
        "cardinality": enricher.cardinality.value,
    }
    aggregation = getattr(enricher, "aggregation", None)
    if aggregation is not None:
        entry["aggregation"] = {
            "group_by": aggregation.group_by,
            "order_by": list(aggregation.order_by),
            "fields": [
                {
                    "source_field": field.source_field,
                    "agg_function": field.agg_function.value,
                    "filter_condition": field.filter_condition,
                    "output_field": field.output_field,
                }
                for field in aggregation.fields
            ],
        }
    return entry


def composite_to_dict(config: CompositeConfigProtocol) -> dict[str, object]:
    """Convert CompositeConfig to serializable dictionary.

    Args:
        config: CompositeConfig instance to serialize.

    Returns:
        Dictionary representation of the CompositeConfig suitable for serialization.
    """
    return {
        "name": config.name,
        "version": config.version,
        "seed": {
            "pipeline": config.seed.pipeline,
            "output_keys": list(config.seed.output_keys),
            "silver_table": config.seed.silver_table,
            "limit": config.seed.limit,
        },
        "dependencies": [
            _dependency_entry(dependency)
            for dependency in config.dependencies
        ],
        "enrichers": [
            _enricher_entry(enricher)
            for enricher in config.enrichers
        ],
        "merge": {
            "strategy": config.merge.strategy.value,
            "conflict_resolution": config.merge.conflict_resolution.value,
            "output_silver_path": config.merge.output_silver_path,
            "output_gold_path": config.merge.output_gold_path,
            "sort_by_silver": list(config.merge.sort_by_silver),
            "sort_by_gold": list(config.merge.sort_by_gold),
            "field_priorities": {
                key: list(value) for key, value in config.merge.field_priorities.items()
            },
            "normalization_compatibility_overrides": dict(
                config.merge.normalization_compatibility_overrides
            ),
            "field_mappings": dict(config.merge.field_mappings),
            "column_groups": [
                {
                    "name": group.name,
                    "fields": list(group.fields),
                    "pattern": group.pattern,
                    "provider_order": list(group.provider_order),
                }
                for group in config.merge.column_groups
            ],
            "exclude_fields": list(config.merge.exclude_fields),
            "preserve_all_sources": config.merge.preserve_all_sources,
        },
        "dq": {
            "soft_fail_threshold": config.dq.soft_fail_threshold,
            "hard_fail_threshold": config.dq.hard_fail_threshold,
            "required_fields": list(config.dq.required_fields),
            "enricher_overrides": {
                name: {
                    "soft_fail_threshold": override.soft_fail_threshold,
                    "hard_fail_threshold": override.hard_fail_threshold,
                }
                for name, override in config.dq.enricher_overrides.items()
            },
        },
        "execution": {
            "max_concurrency": config.execution.max_concurrency,
            "checkpoint_enabled": config.execution.checkpoint_enabled,
            "retry_max_attempts": config.execution.retry_max_attempts,
            "retry_backoff_multiplier": config.execution.retry_backoff_multiplier,
        },
        "lineage": {
            "track_field_sources": config.lineage.track_field_sources,
            "track_timestamps": config.lineage.track_timestamps,
            "track_status": config.lineage.track_status,
            "provider_lookup_fields": {
                provider: dict(fields)
                for provider, fields in config.lineage.provider_lookup_fields.items()
            },
            "track_source_for_fields": list(config.lineage.track_source_for_fields),
        },
        "cross_validation": {
            "enabled": config.cross_validation.enabled,
            "warning_threshold": config.cross_validation.warning_threshold,
            "error_threshold": config.cross_validation.error_threshold,
            "quarantine_threshold": config.cross_validation.quarantine_threshold,
            "fuzzy_threshold": config.cross_validation.fuzzy_threshold,
            "numeric_tolerance": config.cross_validation.numeric_tolerance,
            "enricher_pairings": [
                {
                    "enricher_pipeline": pairing.enricher_pipeline,
                    "fields": [
                        {
                            "field_name": field.field_name,
                            "method": field.method.value,
                            "threshold": field.threshold,
                        }
                        for field in pairing.fields
                    ],
                }
                for pairing in config.cross_validation.enricher_pairings
            ],
        },
    }


def composite_from_dict[
    CompositeConfigT,
    SeedConfigT,
    DependencyConfigT,
    EnricherConfigT,
    MergeConfigT,
](
    data: dict[str, object],
    *,
    composite_cls: Callable[..., CompositeConfigT],
    seed_cls: Callable[..., SeedConfigT],
    dependency_cls: Callable[..., DependencyConfigT],
    enricher_cls: Callable[..., EnricherConfigT],
    merge_cls: Callable[..., MergeConfigT],
) -> CompositeConfigT:
    """Construct CompositeConfig from serialized dictionary.

    Args:
        data: Dictionary previously produced by ``composite_to_dict()``.

    Returns:
        CompositeConfig instance reconstructed from the input dictionary.
    """
    seed_data = require_object_dict(data.get("seed"), "seed")
    dependency_data = require_object_dict_sequence(
        data.get("dependencies", []), "dependencies"
    )
    enricher_data = require_object_dict_sequence(data.get("enrichers", []), "enrichers")
    merge_data = require_object_dict(data.get("merge"), "merge")

    seed = _build_seed_config(seed_data, seed_cls)
    dependencies = _build_dependency_configs(
        dependency_data=list(dependency_data),
        dependency_cls=dependency_cls,
    )
    enrichers = _build_enricher_configs(
        enricher_data=list(enricher_data),
        enricher_cls=enricher_cls,
    )
    merge = _build_merge_config(merge_data, merge_cls)

    kwargs: dict[str, object] = {
        "name": require_str(data.get("name"), "name"),
        "version": require_str(data.get("version"), "version"),
        "seed": seed,
        "dependencies": dependencies,
        "enrichers": enrichers,
        "merge": merge,
    }
    if isinstance(data.get("dq"), dict):
        kwargs["dq"] = _build_dq_config(require_object_dict(data.get("dq"), "dq"))
    if isinstance(data.get("execution"), dict):
        kwargs["execution"] = _build_execution_config(
            require_object_dict(data.get("execution"), "execution")
        )
    if isinstance(data.get("lineage"), dict):
        kwargs["lineage"] = _build_lineage_config(
            require_object_dict(data.get("lineage"), "lineage")
        )
    if isinstance(data.get("cross_validation"), dict):
        kwargs["cross_validation"] = _build_cross_validation_config(
            require_object_dict(data.get("cross_validation"), "cross_validation")
        )
    return composite_cls(**kwargs)


def _build_dq_config(dq_data: dict[str, object]) -> CompositeDQConfig:
    overrides_raw = dq_data.get("enricher_overrides") or {}
    overrides: dict[str, DQOverrideConfig] = {}
    if isinstance(overrides_raw, Mapping):
        for name, raw in overrides_raw.items():
            if isinstance(raw, dict):
                overrides[str(name)] = DQOverrideConfig(
                    soft_fail_threshold=raw.get("soft_fail_threshold"),  # type: ignore[arg-type]
                    hard_fail_threshold=raw.get("hard_fail_threshold"),  # type: ignore[arg-type]
                )
    return CompositeDQConfig(
        soft_fail_threshold=float(dq_data.get("soft_fail_threshold", 0.10)),
        hard_fail_threshold=float(dq_data.get("hard_fail_threshold", 0.50)),
        enricher_overrides=overrides,
        required_fields=tuple(
            str(item) for item in (dq_data.get("required_fields") or ())
        ),
    )


def _build_execution_config(execution_data: dict[str, object]) -> ExecutionConfig:
    return ExecutionConfig(
        max_concurrency=int(execution_data.get("max_concurrency", 4)),
        checkpoint_enabled=bool(execution_data.get("checkpoint_enabled", True)),
        retry_max_attempts=int(execution_data.get("retry_max_attempts", 3)),
        retry_backoff_multiplier=float(
            execution_data.get("retry_backoff_multiplier", 2.0)
        ),
    )


def _build_lineage_config(lineage_data: dict[str, object]) -> LineageConfig:
    lookup_raw = lineage_data.get("provider_lookup_fields") or {}
    lookup: dict[str, dict[str, str]] = {}
    if isinstance(lookup_raw, Mapping):
        for provider, fields in lookup_raw.items():
            if isinstance(fields, Mapping):
                lookup[str(provider)] = {
                    str(key): str(value) for key, value in fields.items()
                }
    track_fields = lineage_data.get("track_source_for_fields") or ()
    return LineageConfig(
        track_field_sources=bool(lineage_data.get("track_field_sources", True)),
        track_timestamps=bool(lineage_data.get("track_timestamps", True)),
        track_status=bool(lineage_data.get("track_status", True)),
        provider_lookup_fields=lookup,
        track_source_for_fields=tuple(str(item) for item in track_fields),
    )


def _field_comparison_specs(fields_raw: object) -> tuple[FieldComparisonSpec, ...]:
    if not isinstance(fields_raw, list | tuple):
        return ()
    fields: list[FieldComparisonSpec] = []
    for field in fields_raw:
        if not isinstance(field, dict):
            continue
        method = field.get("method", "exact")
        fields.append(
            FieldComparisonSpec(
                field_name=str(field.get("field_name") or ""),
                method=(
                    ComparisonMethod(str(method))
                    if not isinstance(method, ComparisonMethod)
                    else method
                ),
                threshold=float(field.get("threshold", 0.0)),
            )
        )
    return tuple(fields)


def _enricher_field_pairings(pairings_raw: object) -> tuple[EnricherFieldPairing, ...]:
    if not isinstance(pairings_raw, list | tuple):
        return ()
    pairings: list[EnricherFieldPairing] = []
    for raw in pairings_raw:
        if not isinstance(raw, dict):
            continue
        pairings.append(
            EnricherFieldPairing(
                enricher_pipeline=str(raw.get("enricher_pipeline") or ""),
                fields=_field_comparison_specs(raw.get("fields") or ()),
            )
        )
    return tuple(pairings)


def _build_cross_validation_config(
    cv_data: dict[str, object],
) -> CrossValidationConfig:
    return CrossValidationConfig(
        enabled=bool(cv_data.get("enabled", True)),
        warning_threshold=int(str(cv_data.get("warning_threshold", 1))),
        error_threshold=int(str(cv_data.get("error_threshold", 2))),
        quarantine_threshold=int(str(cv_data.get("quarantine_threshold", 2))),
        fuzzy_threshold=float(str(cv_data.get("fuzzy_threshold", 0.8))),
        numeric_tolerance=float(str(cv_data.get("numeric_tolerance", 0.10))),
        enricher_pairings=_enricher_field_pairings(
            cv_data.get("enricher_pairings") or ()
        ),
    )
