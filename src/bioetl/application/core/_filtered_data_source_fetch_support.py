"""Fetch strategy helpers for FilteredDataSource."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core.data_source_mixins import (
    _yield_plain_wrapped_fetch_records,
)
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping

    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, FilterableDataSourcePort

class _FilteredFetchState(Protocol):
    """Structural contract for FilteredDataSource fetch helpers."""

    _data_source: DataSourcePort
    _filter_config: InputFilterConfig
    _filter_ids: list[str] | None
    _multi_filter_ids: Mapping[str, list[str]] | None
    _valid_combinations: frozenset[tuple[str, ...]] | None
    _filter_fields: tuple[str, ...] | None
    _fallback_mapping: dict[str, str] | None

    def _ensure_filterable_adapter(self, mode: str) -> None:
        """Check adapter supports the requested filtering mode."""
        ...

def matches_valid_combination(
    state: _FilteredFetchState,
    record: JsonDict,  # Any: filter record values vary (str|int|float|list)
) -> bool:  # Any: filter record values vary (str|int|float|list)
    """Check whether a record matches one of the valid multi-column filters."""
    if not state._valid_combinations or not state._filter_fields:
        return True
    record_values = tuple(str(record.get(field, "")) for field in state._filter_fields)
    return record_values in state._valid_combinations

async def fetch_multi_column(
    state: _FilteredFetchState,
    entity_type: str,
    limit: int | None,
) -> AsyncIterator[
    JsonDict  # Any: filter record values vary (str|int|float|list)
]:  # Any: filter record values vary (str|int|float|list)
    """Fetch records using multi-column server-side filtering plus local validation."""
    state._ensure_filterable_adapter("Multi-column filtering")
    adapter = cast("FilterableDataSourcePort", state._data_source)
    assert state._multi_filter_ids is not None
    fetched_count = 0
    async for record in adapter.fetch_multi_filtered(
        entity_type=entity_type,
        filters=dict(state._multi_filter_ids),
        limit=None,
    ):
        if matches_valid_combination(state, record):
            yield record
            fetched_count += 1
            if limit and fetched_count >= limit:
                return

async def fetch_single_column(
    state: _FilteredFetchState,
    entity_type: str,
    limit: int | None,
) -> AsyncIterator[
    JsonDict  # Any: filter record values vary (str|int|float|list)
]:  # Any: filter record values vary (str|int|float|list)
    """Fetch records using a single configured filter column."""
    state._ensure_filterable_adapter("Filtering")
    adapter = cast("FilterableDataSourcePort", state._data_source)
    config_filter_field = state._filter_config.filter_field
    if config_filter_field is None:
        raise ValueError(
            "filter_field must be specified in InputFilterConfig "
            "when filtering is enabled."
        )
    assert state._filter_ids is not None

    if state._fallback_mapping:
        async for record in adapter.fetch_filtered_with_fallback(
            entity_type=entity_type,
            filter_ids=state._filter_ids,
            filter_field=config_filter_field,
            fallback_mapping=state._fallback_mapping,
            limit=limit,
        ):
            yield record
        return

    async for record in adapter.fetch_filtered(
        entity_type=entity_type,
        filter_ids=state._filter_ids,
        filter_field=config_filter_field,
        limit=limit,
    ):
        yield record

def fetch_without_internal_filters(
    state: _FilteredFetchState,
    entity_type: str,
    limit: int | None,
    query: str | None,
    offset: int | None,
) -> AsyncIterator[
    JsonDict  # Any: filter record values vary (str|int|float|list)
]:  # Any: filter record values vary (str|int|float|list)
    """Delegate unfiltered fetches to the wrapped adapter unchanged."""
    return _yield_plain_wrapped_fetch_records(
        state._data_source,
        entity_type=entity_type,
        limit=limit,
        query=query,
        offset=offset,
    )

def fetch_records(
    state: _FilteredFetchState,
    entity_type: str,
    limit: int | None = None,
    query: str | None = None,
    filter_ids: list[str] | None = None,
    filter_field: str | None = None,
    offset: int | None = None,
) -> AsyncIterator[
    JsonDict  # Any: filter record values vary (str|int|float|list)
]:  # Any: filter record values vary (str|int|float|list)
    """Select the fetch strategy based on loaded filter state."""
    _ = filter_ids, filter_field

    if state._filter_config.enabled and state._multi_filter_ids:
        return fetch_multi_column(state, entity_type, limit)

    if state._filter_config.enabled and state._filter_ids:
        return fetch_single_column(state, entity_type, limit)

    return fetch_without_internal_filters(
        state,
        entity_type,
        limit,
        query,
        offset,
    )
