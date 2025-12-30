"""Domain services for bioactivity data normalization.

This package provides specialized services for normalizing bioactivity data:

- UnitConverter: Conversion between concentration units (nM, µM, mM)
- ValueValidator: Validation of bioactivity value ranges
- ActivityAggregator: Aggregation of multiple measurements
- NormalizationService: Orchestrator facade combining all services

Services are pure domain logic (no I/O) per RULES.md §1.1.

Usage:
    >>> from bioetl.domain.services import NormalizationService, NormalizationConfig
    >>> config = NormalizationConfig()
    >>> service = NormalizationService(config)
    >>> result = service.normalize_activity(100.0, "nM", "IC50")
    >>> print(result)
    (100.0, 'nM')
"""

from bioetl.domain.services.activity_aggregator import ActivityAggregator
from bioetl.domain.services.normalization_config import NormalizationConfig
from bioetl.domain.services.normalization_service import NormalizationService
from bioetl.domain.services.unit_converter import UnitConverter
from bioetl.domain.services.value_validator import ValueValidator

__all__ = [
    "ActivityAggregator",
    "NormalizationConfig",
    "NormalizationService",
    "UnitConverter",
    "ValueValidator",
]
