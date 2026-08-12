"""Pure deserialization of composite configuration domain models."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

from .config_composite_section_decoders import (
    build_cross_validation_config,
    build_dq_config,
    build_execution_config,
    build_lineage_config,
)
from .config_parsing import (
    optional_bool,
    optional_int,
    optional_str,
    optional_str_tuple,
    require_object_dict,
    require_object_dict_sequence,
    require_str,
    require_str_mapping,
    require_str_tuple,
    str_key_mapping,
)

__all__ = ["composite_from_dict"]


def _build_seed_config[ConfigT](
    seed_data: dict[str, object],
    seed_cls: Callable[..., ConfigT],
) -> ConfigT:
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
    return dependency_cls(
        pipeline=require_str(dep.get("pipeline"), "dependencies[].pipeline"),
        join_keys=require_str_tuple(dep.get("join_keys"), "dependencies[].join_keys"),
        required=optional_bool(dep.get("required"), False, "dependencies[].required"),
        timeout_seconds=optional_int(
            dep.get("timeout_seconds"), "dependencies[].timeout_seconds", 600
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
    return tuple(
        _build_dependency_config(dep, dependency_cls) for dep in dependency_data
    )


def _build_enricher_config[ConfigT](
    enricher: dict[str, object],
    enricher_cls: Callable[..., ConfigT],
) -> ConfigT:
    kwargs: dict[str, object] = {
        "pipeline": require_str(enricher.get("pipeline"), "enrichers[].pipeline"),
        "join_keys": require_str_tuple(
            enricher.get("join_keys"), "enrichers[].join_keys"
        ),
        "required": optional_bool(
            enricher.get("required"), False, "enrichers[].required"
        ),
        "timeout_seconds": optional_int(
            enricher.get("timeout_seconds"), "enrichers[].timeout_seconds", 600
        ),
        "filter_condition": optional_str(
            enricher.get("filter_condition"), "enrichers[].filter_condition"
        ),
        "silver_table": optional_str(
            enricher.get("silver_table"), "enrichers[].silver_table"
        ),
        "limit": optional_int(enricher.get("limit"), "enrichers[].limit"),
    }
    for optional_key in ("fallback_strategy", "cardinality", "aggregation"):
        if enricher.get(optional_key) is not None:
            kwargs[optional_key] = enricher.get(optional_key)
    return enricher_cls(**kwargs)


def _build_enricher_configs[ConfigT](
    enricher_data: list[dict[str, object]],
    enricher_cls: Callable[..., ConfigT],
) -> tuple[ConfigT, ...]:
    return tuple(_build_enricher_config(item, enricher_cls) for item in enricher_data)


def _parse_field_priorities(raw: object) -> dict[str, tuple[str, ...]]:
    priorities_raw = str_key_mapping(raw, "merge.field_priorities")
    return {
        key: tuple(str(item) for item in value)
        if isinstance(value, list | tuple)
        else (str(value),)
        for key, value in priorities_raw.items()
    }


def _optional_column_groups(raw: object) -> object:
    if raw in (None, ()):
        return ()
    return require_object_dict_sequence(raw or (), "merge.column_groups")


def _build_merge_config[ConfigT](
    merge_data: dict[str, object],
    merge_cls: Callable[..., ConfigT],
) -> ConfigT:
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
        field_priorities=_parse_field_priorities(merge_data.get("field_priorities")),
        normalization_compatibility_overrides=require_str_mapping(
            merge_data.get("normalization_compatibility_overrides"),
            "merge.normalization_compatibility_overrides",
        ),
        field_mappings=require_str_mapping(
            merge_data.get("field_mappings"), "merge.field_mappings"
        ),
        column_groups=_optional_column_groups(merge_data.get("column_groups")),
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


def _attach_optional_section(
    kwargs: dict[str, object],
    data: dict[str, object],
    key: str,
    builder: Callable[[dict[str, object]], object],
) -> None:
    raw = data.get(key)
    if isinstance(raw, dict):
        kwargs[key] = builder(require_object_dict(raw, key))


def _attach_optional_composite_sections(
    kwargs: dict[str, object], data: dict[str, object]
) -> None:
    _attach_optional_section(kwargs, data, "dq", build_dq_config)
    _attach_optional_section(kwargs, data, "execution", build_execution_config)
    _attach_optional_section(kwargs, data, "lineage", build_lineage_config)
    _attach_optional_section(
        kwargs, data, "cross_validation", build_cross_validation_config
    )


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
    """Reconstruct a composite config from a serialized mapping."""
    seed_data = require_object_dict(data.get("seed"), "seed")
    dependency_data = require_object_dict_sequence(
        data.get("dependencies", []), "dependencies"
    )
    enricher_data = require_object_dict_sequence(data.get("enrichers", []), "enrichers")
    merge_data = require_object_dict(data.get("merge"), "merge")
    kwargs: dict[str, object] = {
        "name": require_str(data.get("name"), "name"),
        "version": require_str(data.get("version"), "version"),
        "seed": _build_seed_config(seed_data, seed_cls),
        "dependencies": _build_dependency_configs(
            list(dependency_data), dependency_cls
        ),
        "enrichers": _build_enricher_configs(list(enricher_data), enricher_cls),
        "merge": _build_merge_config(merge_data, merge_cls),
    }
    _attach_optional_composite_sections(kwargs, data)
    return composite_cls(**kwargs)
