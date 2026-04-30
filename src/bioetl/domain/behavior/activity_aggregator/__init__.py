"""Activity aggregator service for bioactivity measurements.

Handles aggregation of multiple activity measurements into
representative values with uncertainty estimates.

Pure domain service (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from bioetl.domain.behavior.activity_aggregator._aggregator import ActivityAggregator
from bioetl.domain.behavior.activity_aggregator._methods import AggregationMethod

__all__ = [
    "ActivityAggregator",
    "AggregationMethod",
]
