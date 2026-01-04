"""Filter configuration for pipeline filtering.

This package provides:
- Input filtering: API requests based on input IDs from external sources (CSV files)
- Gold filtering: Configurable column-based filters for Gold layer records

All public classes are re-exported from this module for backwards compatibility.
"""

from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.gold_config import GoldFilterConfig
from bioetl.domain.filtering.input_config import FilterColumn, InputFilterConfig
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
from bioetl.domain.filtering.load_result import FilterLoadResult
from bioetl.domain.filtering.range_filter import GoldRangeFilter

__all__ = [
    "FilterColumn",
    "FilterLoadResult",
    "GoldColumnFilter",
    "GoldFilterConfig",
    "GoldListContainsFilter",
    "GoldListLengthFilter",
    "GoldRangeFilter",
    "InputFilterConfig",
]
