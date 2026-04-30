"""Support helpers for FilteredDataSource lifecycle and filter loading."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bioetl.domain.filtering import (
        FilterColumn,
        FilterLoadResult,
        InputFilterConfig,
    )
    from bioetl.domain.ports import (
        DataSourcePort,
        InputFilterPort,
        LoggerPort,
        MetricsPort,
    )


class _FilteredDataSourceState(Protocol):
    """Structural state contract for FilteredDataSource support helpers."""

    _data_source: DataSourcePort
    _filter_reader: InputFilterPort | None
    _filter_config: InputFilterConfig
    _metrics: MetricsPort | None
    _pipeline_name: str
    _logger: LoggerPort | None
    _filter_ids: list[str] | None
    _filter_result: FilterLoadResult | None
    _multi_filter_ids: Mapping[str, list[str]] | None
    _valid_combinations: frozenset[tuple[str, ...]] | None
    _filter_fields: tuple[str, ...] | None
    _fallback_mapping: dict[str, str] | None


CSV_SINGLE_COLUMN_SOURCE_KIND = "csv_single_column"
CSV_MULTI_COLUMN_SOURCE_KIND = "csv_multi_column"


async def enter_filtered_data_source(state: _FilteredDataSourceState) -> None:
    """Enter the wrapped adapter and preload any configured filters."""
    await state._data_source.__aenter__()

    if not state._filter_config.enabled:
        return

    if state._filter_config.direct_multi_filter_ids:
        load_direct_multi_filter_ids(state)
        return

    if state._filter_config.direct_filter_ids:
        load_direct_filter_ids(state)
        return

    await load_csv_filter_ids(state)


def log_filter_file_not_found(
    state: _FilteredDataSourceState,
    source_path: str,
) -> None:
    """Log warning when filter file is not found."""
    if state._logger:
        state._logger.warning(
            "input_filter_file_not_found",
            source_path=source_path,
            pipeline=state._pipeline_name,
            message="Filter file not found, proceeding without filtering",
        )


def load_direct_multi_filter_ids(state: _FilteredDataSourceState) -> None:
    """Load direct multi-field filter IDs from configuration."""
    multi_ids = state._filter_config.direct_multi_filter_ids or {}
    state._multi_filter_ids = {field: list(ids) for field, ids in multi_ids.items()}
    filter_fields = tuple(multi_ids.keys())
    state._filter_fields = filter_fields
    state._valid_combinations = state._filter_config.direct_valid_combinations
    if state._logger:
        state._logger.info(
            "direct_multi_filter_ids_loaded",
            fields=list(filter_fields),
            counts={field: len(ids) for field, ids in multi_ids.items()},
            valid_combinations_count=len(state._valid_combinations)
            if state._valid_combinations
            else 0,
            pipeline=state._pipeline_name,
        )


def load_direct_filter_ids(state: _FilteredDataSourceState) -> None:
    """Load direct filter IDs from configuration."""
    loaded_filter_ids = list(state._filter_config.direct_filter_ids or [])
    state._filter_ids = loaded_filter_ids
    state._fallback_mapping = state._filter_config.direct_fallback_mapping
    if state._logger:
        state._logger.info(
            "direct_filter_ids_loaded",
            count=len(loaded_filter_ids),
            fallback_mapping_size=len(state._fallback_mapping)
            if state._fallback_mapping
            else 0,
            filter_field=state._filter_config.filter_field,
            pipeline=state._pipeline_name,
        )


async def load_csv_filter_ids(state: _FilteredDataSourceState) -> None:
    """Load filter IDs from CSV file when a reader and source path exist."""
    if not state._filter_reader:
        return

    source_path = state._filter_config.source_path
    if not source_path:
        return

    columns = state._filter_config.get_columns()
    try:
        if len(columns) > 1:
            await _load_multi_column_filter(state, source_path, columns)
        elif state._filter_config.column_name:
            await _load_single_column_filter(state, source_path)
    except FileNotFoundError:
        log_filter_file_not_found(state, source_path)


async def _load_multi_column_filter(
    state: _FilteredDataSourceState,
    source_path: str,
    columns: tuple[FilterColumn, ...],
) -> None:
    """Load multi-column filter from CSV."""
    assert state._filter_reader is not None
    result = await state._filter_reader.load_multi_column_filter(
        source_path=source_path,
        columns=list(columns),
    )
    state._filter_result = result
    state._multi_filter_ids = {
        field: list(ids) for field, ids in result.column_ids.items()
    }
    state._valid_combinations = result.valid_combinations
    state._filter_fields = result.filter_fields
    _record_multi_filter_metrics(state)


async def _load_single_column_filter(
    state: _FilteredDataSourceState,
    source_path: str,
) -> None:
    """Load single-column filter from CSV."""
    assert state._filter_reader is not None
    assert state._filter_config.column_name is not None
    if state._filter_config.fallback_column:
        (
            state._filter_result,
            state._fallback_mapping,
        ) = await state._filter_reader.load_filter_with_fallback(
            source_path=source_path,
            primary_column=state._filter_config.column_name,
            fallback_column=state._filter_config.fallback_column,
        )
    else:
        state._filter_result = await state._filter_reader.load_filter_ids(
            source_path=source_path,
            column_name=state._filter_config.column_name,
        )
    assert state._filter_result is not None
    state._filter_ids = list(state._filter_result.ids)
    _record_filter_metrics(state)


def _record_filter_metrics(state: _FilteredDataSourceState) -> None:
    """Record single-column filter loading metrics."""
    if not state._metrics or not state._filter_result:
        return

    state._metrics.increment_counter(
        "bioetl_filter_ids_loaded_total",
        state._filter_result.unique_count,
        {"pipeline": state._pipeline_name, "source_kind": CSV_SINGLE_COLUMN_SOURCE_KIND},
    )
    if state._filter_result.has_duplicates:
        state._metrics.increment_counter(
            "bioetl_filter_ids_duplicates_total",
            state._filter_result.duplicate_count,
            {
                "pipeline": state._pipeline_name,
                "source_kind": CSV_SINGLE_COLUMN_SOURCE_KIND,
            },
        )


def _record_multi_filter_metrics(state: _FilteredDataSourceState) -> None:
    """Record multi-column filter loading metrics."""
    if not state._metrics or not state._filter_result:
        return

    if state._valid_combinations:
        state._metrics.increment_counter(
            "bioetl_filter_combinations_loaded_total",
            len(state._valid_combinations),
            {"pipeline": state._pipeline_name, "source_kind": CSV_MULTI_COLUMN_SOURCE_KIND},
        )

    for field, ids in state._filter_result.column_ids.items():
        # Keep the counter aligned with the registered metric schema.
        # Per-field breakdown is useful, but it cannot be attached here unless the
        # metric definition is explicitly widened in a coordinated registry change.
        _ = field
        state._metrics.increment_counter(
            "bioetl_filter_ids_loaded_total",
            len(ids),
            {
                "pipeline": state._pipeline_name,
                "source_kind": CSV_MULTI_COLUMN_SOURCE_KIND,
            },
        )
