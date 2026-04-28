"""Domain services for bioactivity data processing.

This package provides specialized services for domain operations:

- IdentityService: Entity ID and content hash generation (RULES.md §2.8)
- UnitConverter: Conversion between concentration units (nM, µM, mM)
- ValueValidator: Validation of bioactivity value ranges
- ActivityAggregator: Aggregation of multiple measurements
- NormalizationService: Orchestrator facade combining bioactivity normalization
- DataNormalizationService: Text and data normalization (DOI, PMID, authors, HTML)
- OrganismClassificationService: Organism cellularity classification for assay filtering

Services are pure domain logic (no I/O) per RULES.md §1.1.

Note:
    ``DoiNormalizationService``, ``PmidNormalizationService``,
    ``DateNormalizationService``, and ``TextNormalizationService`` are retained
    as deprecated compatibility façades over ``bioetl.domain.normalization.*``
    for one sunset cycle.

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

from __future__ import annotations

from bioetl.domain.services.activity_aggregator import ActivityAggregator
from bioetl.domain.services.chemical_standardization import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
    ChemicalStandardizationResult,
    ChemicalStandardizationStatus,
    standardize_chemical_structure,
)
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig
from bioetl.domain.services.data_normalization_service import (
    DefaultDataNormalizationService,
)
from bioetl.domain.services.date_normalization import DateNormalizationService
from bioetl.domain.services.doi_normalization import DoiNormalizationService
from bioetl.domain.services.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.services.dq_serializer import DQReportSerializer
from bioetl.domain.services.identity_service import IdentityService
from bioetl.domain.services.normalization_config import NormalizationConfig
from bioetl.domain.services.normalization_service import NormalizationService
from bioetl.domain.services.organism_classification_service import (
    ClassificationStats,
    OrganismClassificationService,
)
from bioetl.domain.services.pmid_normalization import PmidNormalizationService
from bioetl.domain.services.text_normalization import TextNormalizationService
from bioetl.domain.services.text_similarity import jaccard_similarity, normalize_text
from bioetl.domain.services.unit_converter import UnitConverter
from bioetl.domain.services.value_validator import ValueValidator

# Alias for backward compatibility and shorter name
DataNormalizationService = DefaultDataNormalizationService

__all__ = [
    "CHEMICAL_STANDARDIZATION_POLICY_VERSION",
    "CHEMICAL_STANDARDIZATION_STATUSES",
    "ActivityAggregator",
    "ChemicalStandardizationResult",
    "ChemicalStandardizationStatus",
    "ClassificationStats",
    "DQMetricsCalculator",
    "DQMetricsInput",
    "DQReportSerializer",
    "DataNormalizationConfig",
    "DataNormalizationService",
    "DateNormalizationService",
    "DefaultDataNormalizationService",
    "DoiNormalizationService",
    "IdentityService",
    "NormalizationConfig",
    "NormalizationService",
    "OrganismClassificationService",
    "PmidNormalizationService",
    "TextNormalizationService",
    "UnitConverter",
    "ValueValidator",
    "jaccard_similarity",
    "normalize_text",
    "standardize_chemical_structure",
]
