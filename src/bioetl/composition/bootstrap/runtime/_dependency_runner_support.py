"""Pure support helpers for dependency-runner factory assembly."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite import DependencyConfig

__all__ = [
    "build_dependency_debug_context",
    "resolve_dependency_runner_limit",
]


def build_dependency_debug_context(
    *,
    pipeline_name: str,
    keys: pl.DataFrame,
    dep_cfg: DependencyConfig | None,
    filter_field: str | None,
    filter_ids: tuple[str, ...] | None,
    multi_filter_ids: dict[str, tuple[str, ...]] | None,
) -> dict[str, object]:
    """Build structured logging context for dependency-runner creation."""
    join_keys = [] if dep_cfg is None else list(dep_cfg.join_keys)
    filter_ids_sample = [] if filter_ids is None else list(filter_ids)[:5]
    multi_filter_fields = []
    multi_filter_counts: dict[str, int] = {}

    if multi_filter_ids is not None:
        multi_filter_fields = list(multi_filter_ids.keys())
        multi_filter_counts = {
            field: len(ids) for field, ids in multi_filter_ids.items()
        }

    return {
        "pipeline": pipeline_name,
        "keys_columns": list(keys.columns),
        "keys_count": len(keys),
        "join_keys": join_keys,
        "filter_field": filter_field,
        "filter_ids_count": 0 if filter_ids is None else len(filter_ids),
        "filter_ids_sample": filter_ids_sample,
        "multi_filter_fields": multi_filter_fields,
        "multi_filter_counts": multi_filter_counts,
        "is_chained": dep_cfg is not None and dep_cfg.key_source is not None,
        "key_source": None if dep_cfg is None else dep_cfg.key_source,
    }


def resolve_dependency_runner_limit(
    *,
    keys: pl.DataFrame,
    filter_ids: tuple[str, ...] | None,
    multi_filter_ids: dict[str, tuple[str, ...]] | None,
) -> int | None:
    """Return dependency-runner limit when filter inputs are present."""
    if filter_ids is None and multi_filter_ids is None:
        return None
    return len(keys)
