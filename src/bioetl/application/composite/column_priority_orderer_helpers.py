"""Pure helper functions for explicit column-priority ordering."""

from __future__ import annotations

from collections.abc import Sequence

from bioetl.application.composite.join_planner_helpers import parse_pipeline_name
from bioetl.domain.composite.config import EnricherConfig


def get_enricher_prefix(enricher_pipeline: str) -> str:
    """Return qualified provider/entity prefix or legacy fallback prefix."""
    try:
        provider, entity = parse_pipeline_name(enricher_pipeline)
        return f"{provider}.{entity}."
    except ValueError:
        return f"{enricher_pipeline}_"


def resolve_seed_column(
    *,
    field: str,
    seed_provider: str | None,
    seed_entity: str | None,
) -> str | None:
    """Resolve the seed token to a qualified seed column when context exists."""
    if seed_provider and seed_entity:
        return f"{seed_provider}.{seed_entity}.{field}"
    return None


def resolve_by_column_scan(
    *,
    provider: str,
    field: str,
    columns_set: set[str],
) -> str | None:
    """Find a provider-prefixed column by scanning available columns."""
    for column in columns_set:
        if column.startswith(f"{provider}.") and column.endswith(f".{field}"):
            return column
    return None


def resolve_priority_column(
    *,
    source: str,
    field: str,
    columns_set: set[str],
    seed_provider: str | None,
    seed_entity: str | None,
) -> str | None:
    """Resolve one priority token to a concrete column name."""
    source_lower = source.lower()
    if source_lower == "seed":
        return resolve_seed_column(
            field=field,
            seed_provider=seed_provider,
            seed_entity=seed_entity,
        )
    if "." in source:
        provider, entity = source.split(".", 1)
        return f"{provider.lower()}.{entity.lower()}.{field}"
    provider = source_lower
    if seed_provider and provider == seed_provider.lower() and seed_entity:
        return f"{provider}.{seed_entity}.{field}"
    return resolve_by_column_scan(
        provider=provider,
        field=field,
        columns_set=columns_set,
    )


def collect_field_columns(
    *,
    field: str,
    enrichers: Sequence[EnricherConfig],
    available_columns: set[str],
    seed_pipeline: str | None = None,
) -> tuple[list[str], bool]:
    """Collect candidate field columns and indicate whether parsing fallback was used."""
    columns: list[str] = []
    used_parse_fallback = False
    if seed_pipeline:
        try:
            seed_provider, seed_entity = parse_pipeline_name(seed_pipeline)
            seed_qualified = f"{seed_provider}.{seed_entity}.{field}"
            if seed_qualified in available_columns:
                columns.append(seed_qualified)
        except ValueError:
            used_parse_fallback = True
    for enricher in enrichers:
        try:
            provider, entity = parse_pipeline_name(enricher.pipeline)
            enricher_qualified = f"{provider}.{entity}.{field}"
            if (
                enricher_qualified in available_columns
                and enricher_qualified not in columns
            ):
                columns.append(enricher_qualified)
        except ValueError:
            legacy_col = f"{get_enricher_prefix(enricher.pipeline)}{field}".rstrip(".")
            if legacy_col in available_columns and legacy_col not in columns:
                columns.append(legacy_col)
    return columns, used_parse_fallback


def order_columns_by_priority(
    *,
    field: str,
    columns: list[str],
    priorities: Sequence[str],
    seed_pipeline: str | None = None,
) -> tuple[list[str], bool]:
    """Order columns by source priority and indicate seed-pipeline parse fallback."""
    ordered_cols: list[str] = []
    columns_set = set(columns)
    seed_provider: str | None = None
    seed_entity: str | None = None
    used_parse_fallback = False
    if seed_pipeline:
        try:
            seed_provider, seed_entity = parse_pipeline_name(seed_pipeline)
        except ValueError:
            used_parse_fallback = True
    for source in priorities:
        qualified = resolve_priority_column(
            source=source,
            field=field,
            columns_set=columns_set,
            seed_provider=seed_provider,
            seed_entity=seed_entity,
        )
        if qualified and qualified in columns_set and qualified not in ordered_cols:
            ordered_cols.append(qualified)
    for column in columns:
        if column not in ordered_cols:
            ordered_cols.append(column)
    return ordered_cols, used_parse_fallback


__all__ = [
    "collect_field_columns",
    "get_enricher_prefix",
    "order_columns_by_priority",
    "resolve_by_column_scan",
    "resolve_priority_column",
    "resolve_seed_column",
]
