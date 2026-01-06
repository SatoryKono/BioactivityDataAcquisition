"""Domain services for bioactivity data processing.

This package provides specialized services for domain operations:

- IdentityService: Entity ID and content hash generation (RULES.md §2.8)
- UnitConverter: Conversion between concentration units (nM, µM, mM)
- ValueValidator: Validation of bioactivity value ranges
- ActivityAggregator: Aggregation of multiple measurements
- NormalizationService: Orchestrator facade combining bioactivity normalization
- DataNormalizationService: Text and data normalization (DOI, PMID, authors, HTML)

Services are pure domain logic (no I/O) per RULES.md §1.1.

Usage:
    >>> from bioetl.domain.services import IdentityService
    >>> identity = IdentityService()
    >>> entity_id = identity.compute_entity_id("chembl", "activity", "12345", {})
    >>> content_hash = identity.compute_content_hash("chembl", {"value": 100})

    >>> from bioetl.domain.services import NormalizationService, NormalizationConfig
    >>> config = NormalizationConfig()
    >>> service = NormalizationService(config)
    >>> result = service.normalize_activity(100.0, "nM", "IC50")

    >>> from bioetl.domain.services import DataNormalizationService
    >>> data_normalizer = DataNormalizationService()
    >>> data_normalizer.normalize_doi("10.1038/NATURE12373")
    '10.1038/nature12373'
"""

from bioetl.domain.services.activity_aggregator import ActivityAggregator
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig
from bioetl.domain.services.data_normalization_service import (
    DefaultDataNormalizationService,
)
from bioetl.domain.services.identity_service import IdentityService
from bioetl.domain.services.normalization_config import NormalizationConfig
from bioetl.domain.services.normalization_service import NormalizationService
from bioetl.domain.services.unit_converter import UnitConverter
from bioetl.domain.services.value_validator import ValueValidator

# Alias for backward compatibility and shorter name
DataNormalizationService = DefaultDataNormalizationService

__all__ = [
    "ActivityAggregator",
    "DataNormalizationConfig",
    "DataNormalizationService",
    "DefaultDataNormalizationService",
    "IdentityService",
    "NormalizationConfig",
    "NormalizationService",
    "UnitConverter",
    "ValueValidator",
]
