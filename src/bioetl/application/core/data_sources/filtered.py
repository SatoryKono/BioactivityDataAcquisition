"""Filtered Data Source wrapper.

Decorates a DataSourcePort with input filtering capability.
Loads filter IDs from external sources (CSV) and passes them to the adapter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.data_source_mixins import _SourceMetadataDelegationMixin
from bioetl.application.core.filtered_data_source_mixins import (
    _FilteredDataSourceFetchMixin,
    _FilteredDataSourceLifecycleMixin,
)
from bioetl.domain.ports import FilterableDataSourcePort

if TYPE_CHECKING:
    from collections.abc import Mapping

    from bioetl.domain.filtering import FilterLoadResult, InputFilterConfig
    from bioetl.domain.ports import (
        DataSourcePort,
        InputFilterPort,
        LoggerPort,
        MetricsPort,
    )

__all__ = ["FilteredDataSource"]


class FilteredDataSource(
    _FilteredDataSourceFetchMixin,
    _FilteredDataSourceLifecycleMixin,
    _SourceMetadataDelegationMixin,
):
    """Wraps a DataSourcePort to add CSV-based filtering.
    Decorator pattern: loads filter IDs from CSV, calls fetch_filtered() on
    adapters that support it, delegates all other operations to wrapped adapter.
    Multi-column filtering uses hybrid approach (server + client-side filtering).
    """

    def __init__(
        self,
        data_source: DataSourcePort,
        filter_reader: InputFilterPort | None,
        filter_config: InputFilterConfig,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize filtered data source wrapper."""
        self._data_source = data_source
        self._filter_reader = filter_reader
        self._filter_config = filter_config
        self._metrics = metrics
        self._pipeline_name = pipeline_name
        self._logger = logger
        self._filter_ids: list[str] | None = None
        self._filter_result: FilterLoadResult | None = None
        self._multi_filter_ids: Mapping[str, list[str]] | None = None
        self._valid_combinations: frozenset[tuple[str, ...]] | None = None
        self._filter_fields: tuple[str, ...] | None = None
        self._fallback_mapping: dict[str, str] | None = None

    @property
    def provider_name(self) -> str:
        """Provider name from the wrapped data source."""
        provider_name: str = self._data_source.provider_name
        return provider_name

    @property
    def filter_result(self) -> FilterLoadResult | None:
        """Access to filter load result with duplicate statistics."""
        return self._filter_result

    def _ensure_filterable_adapter(self, mode: str) -> None:
        """Check that adapter implements FilterableDataSourcePort."""
        if not isinstance(self._data_source, FilterableDataSourcePort):
            raise TypeError(
                f"Adapter {self._data_source.provider_name} does not implement "
                f"FilterableDataSourcePort. {mode} requires an adapter with "
                "fetch_filtered() method."
            )
