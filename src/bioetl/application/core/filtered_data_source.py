"""Legacy flat facade for filtered data-source wrapper."""

from __future__ import annotations

# Compatibility note: the concrete implementation performs runtime protocol
# validation via isinstance(adapter, FilterableDataSourcePort). This facade
# simply re-exports that implementation for the legacy import path.
from bioetl.application.core.data_sources.filtered import FilteredDataSource

__all__ = ["FilteredDataSource"]
