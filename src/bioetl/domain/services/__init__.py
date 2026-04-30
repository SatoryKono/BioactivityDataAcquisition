"""Domain behavior surfaces for bioactivity data processing.

This package provides specialized services for domain operations:

- EntityIdentityGenerator: Entity ID and content hash generation (RULES.md §2.8)
- UnitConverter: Conversion between concentration units (nM, µM, mM)
- ValueValidator: Validation of bioactivity value ranges
- ActivityAggregator: Aggregation of multiple measurements
- AuthorNormalizer: Author and affiliation normalization
- CompositeValidator: Structural and deep-preflight composite validation
- MergedMetadataExplainer: Explainability metadata for merged composite output
- BioactivityNormalizer: Orchestrator facade combining bioactivity normalization
- DefaultDataNormalizer: Text and data normalization (DOI, PMID, authors, HTML)
- OrganismClassifier: Organism cellularity classification for assay filtering
- PhasedMigrationCoordinator: Compatibility/migration phase coordination

Services are pure domain logic (no I/O) per RULES.md §1.1.

Note:
    Identifier/date/text normalization now lives in
    ``bioetl.domain.normalization.*``. Canonical names are exported directly.

Usage:
    >>> from bioetl.domain.services import EntityIdentityGenerator
    >>> identity = EntityIdentityGenerator()
    >>> entity_id = identity.compute_entity_id("chembl", "activity", "12345", {})
    >>> content_hash = identity.compute_content_hash("chembl", {"value": 100})

    >>> from bioetl.domain.services import BioactivityNormalizer, NormalizationConfig
    >>> config = NormalizationConfig()
    >>> service = BioactivityNormalizer(config)
    >>> result = service.normalize_activity(100.0, "nM", "IC50")

    >>> from bioetl.domain.services import DefaultDataNormalizer
    >>> data_normalizer = DefaultDataNormalizer()
    >>> data_normalizer.normalize_doi("10.1038/NATURE12373")
    '10.1038/nature12373'
"""

from __future__ import annotations

from bioetl.domain.services.activity_aggregator import ActivityAggregator
from bioetl.domain.services.author_normalization_service import (
    AuthorNormalizer,
)
from bioetl.domain.services.chemical_standardization import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
    ChemicalStandardizationResult,
    ChemicalStandardizationStatus,
    standardize_chemical_structure,
)
from bioetl.domain.services.composite_validation_layer import (
    CompositeValidator,
)
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig
from bioetl.domain.services.data_normalization_service import (
    DefaultDataNormalizer,
)
from bioetl.domain.services.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.services.dq_serializer import DQReportSerializer
from bioetl.domain.services.identity_service import (
    EntityIdentityGenerator,
)
from bioetl.domain.services.merged_metadata_explainability import (
    MergedMetadataExplainer,
)
from bioetl.domain.services.normalization_config import NormalizationConfig
from bioetl.domain.services.normalization_service import (
    BioactivityNormalizer,
)
from bioetl.domain.services.organism_classification_service import (
    ClassificationStats,
    OrganismClassifier,
)
from bioetl.domain.services.phased_migration_support import (
    PhasedMigrationCoordinator,
)
from bioetl.domain.services.preflight_governance import (
    PreflightGovernor,
)
from bioetl.domain.services.text_similarity import jaccard_similarity, normalize_text
from bioetl.domain.services.unit_converter import UnitConverter
from bioetl.domain.services.value_validator import ValueValidator

__all__ = [
    "CHEMICAL_STANDARDIZATION_POLICY_VERSION",
    "CHEMICAL_STANDARDIZATION_STATUSES",
    "ActivityAggregator",
    "AuthorNormalizer",
    "BioactivityNormalizer",
    "ChemicalStandardizationResult",
    "ChemicalStandardizationStatus",
    "ClassificationStats",
    "CompositeValidator",
    "DQMetricsCalculator",
    "DQMetricsInput",
    "DQReportSerializer",
    "DataNormalizationConfig",
    "DefaultDataNormalizer",
    "EntityIdentityGenerator",
    "MergedMetadataExplainer",
    "NormalizationConfig",
    "OrganismClassifier",
    "PhasedMigrationCoordinator",
    "PreflightGovernor",
    "UnitConverter",
    "ValueValidator",
    "jaccard_similarity",
    "normalize_text",
    "standardize_chemical_structure",
]
