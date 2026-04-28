"""Serialization helpers for CompositeConfig."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

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
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy

if TYPE_CHECKING:
    from bioetl.domain.composite.config import CompositeConfig

__all__ = [
    "composite_from_dict",
    "composite_to_dict",
]

_ConfigT = TypeVar("_ConfigT")


def _build_seed_config[ConfigT](
    seed_data: dict[str, object],
    seed_cls: Callable[..., _ConfigT],
) -> _ConfigT:
    """Build seed config from parsed seed mapping."""
    return seed_cls(
        pipeline=require_str(seed_data.get("pipeline"), "seed.pipeline"),
        output_keys=require_str_tuple(seed_data.get("output_keys"), "seed.output_keys"),
        silver_table=require_str(seed_data.get("silver_table"), "seed.silver_table"),
        limit=optional_int(seed_data.get("limit"), "seed.limit"),
    )


def _build_dependency_config[ConfigT](
    dep: dict[str, object],
    dependency_cls: Callable[..., _ConfigT],
) -> _ConfigT:
    """Build one dependency config from serialized mapping."""
    return dependency_cls(
        pipeline=require_str(dep.get("pipeline"), "dependencies[].pipeline"),
        join_keys=require_str_tuple(dep.get("join_keys"), "dependencies[].join_keys"),
        required=optional_bool(dep.get("required"), False, "dependencies[].required"),
        timeout_seconds=optional_int(
            dep.get("timeout_seconds"),
            "dependencies[].timeout_seconds",
            600,
        )
        or 600,
        silver_table=optional_str(
            dep.get("silver_table"), "dependencies[].silver_table"
        ),
        filter_fields=optional_str_tuple(
            dep.get("filter_fields"), "dependencies[].filter_fields"
        ),
    )


def _build_dependency_configs[ConfigT](
    dependency_data: list[dict[str, object]],
    dependency_cls: Callable[..., _ConfigT],
) -> tuple[_ConfigT, ...]:
    """Build dependency config tuple."""
    return tuple(
        _build_dependency_config(dep, dependency_cls) for dep in dependency_data
    )


def _build_enricher_config[ConfigT](
    enricher: dict[str, object],
    enricher_cls: Callable[..., _ConfigT],
) -> _ConfigT:
    """Build one enricher config from serialized mapping."""
    return enricher_cls(
        pipeline=require_str(enricher.get("pipeline"), "enrichers[].pipeline"),
        join_keys=require_str_tuple(enricher.get("join_keys"), "enrichers[].join_keys"),
        required=optional_bool(enricher.get("required"), False, "enrichers[].required"),
        timeout_seconds=optional_int(
            enricher.get("timeout_seconds"),
            "enrichers[].timeout_seconds",
            600,
        )
        or 600,
    )


def _build_enricher_configs[ConfigT](
    enricher_data: list[dict[str, object]],
    enricher_cls: Callable[..., _ConfigT],
) -> tuple[_ConfigT, ...]:
    """Build enricher config tuple."""
    return tuple(
        _build_enricher_config(enricher, enricher_cls) for enricher in enricher_data
    )


def _build_merge_config[ConfigT](
    merge_data: dict[str, object],
    merge_cls: Callable[..., _ConfigT],
) -> _ConfigT:
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
    )


def composite_to_dict(config: CompositeConfig) -> dict[str, object]:
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
        },
        "dependencies": [
            {
                "pipeline": dependency.pipeline,
                "join_keys": list(dependency.join_keys),
                "required": dependency.required,
                "timeout_seconds": dependency.timeout_seconds,
                "silver_table": dependency.silver_table,
                **(
                    {"filter_fields": list(dependency.filter_fields)}
                    if dependency.filter_fields
                    else {}
                ),
            }
            for dependency in config.dependencies
        ],
        "enrichers": [
            {
                "pipeline": enricher.pipeline,
                "join_keys": list(enricher.join_keys),
                "required": enricher.required,
                "timeout_seconds": enricher.timeout_seconds,
            }
            for enricher in config.enrichers
        ],
        "merge": {
            "strategy": config.merge.strategy.value,
            "conflict_resolution": config.merge.conflict_resolution.value,
            "output_silver_path": config.merge.output_silver_path,
            "output_gold_path": config.merge.output_gold_path,
            "sort_by_silver": list(config.merge.sort_by_silver),
            "sort_by_gold": list(config.merge.sort_by_gold),
        },
    }


def composite_from_dict(data: dict[str, object]) -> CompositeConfig:
    """Construct CompositeConfig from serialized dictionary.

    Args:
        data: Dictionary previously produced by ``composite_to_dict()``.

    Returns:
        CompositeConfig instance reconstructed from the input dictionary.
    """
    # Local imports avoid runtime circular dependency with config.py facade.
    from bioetl.domain.composite.config import (
        CompositeConfig,
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
        SeedConfig,
    )

    seed_data = require_object_dict(data.get("seed"), "seed")
    dependency_data = require_object_dict_sequence(
        data.get("dependencies", []), "dependencies"
    )
    enricher_data = require_object_dict_sequence(data.get("enrichers", []), "enrichers")
    merge_data = require_object_dict(data.get("merge"), "merge")

    seed = _build_seed_config(seed_data, SeedConfig)
    dependencies = _build_dependency_configs(
        dependency_data=list(dependency_data),
        dependency_cls=DependencyConfig,
    )
    enrichers = _build_enricher_configs(
        enricher_data=list(enricher_data),
        enricher_cls=EnricherConfig,
    )
    merge = _build_merge_config(merge_data, MergeConfig)

    return CompositeConfig(
        name=require_str(data.get("name"), "name"),
        version=require_str(data.get("version"), "version"),
        seed=seed,
        dependencies=dependencies,
        enrichers=enrichers,
        merge=merge,
    )
