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
    ``bioetl.domain.normalization.*``. Canonical names are exported directly;
    selected legacy names remain as compatibility aliases during ADR-041 migration.

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
    AuthorNormalizationService,
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
    CompositeValidationService,
    CompositeValidator,
)
from bioetl.domain.services.data_normalization_config import DataNormalizationConfig
from bioetl.domain.services.data_normalization_service import (
    DefaultDataNormalizationService,
    DefaultDataNormalizer,
)
from bioetl.domain.services.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.services.dq_serializer import DQReportSerializer
from bioetl.domain.services.identity_service import (
    EntityIdentityGenerator,
    IdentityService,
)
from bioetl.domain.services.merged_metadata_explainability import (
    MergedMetadataExplainabilityService,
    MergedMetadataExplainer,
)
from bioetl.domain.services.normalization_config import NormalizationConfig
from bioetl.domain.services.normalization_service import (
    BioactivityNormalizer,
    NormalizationService,
)
from bioetl.domain.services.organism_classification_service import (
    ClassificationStats,
    OrganismClassificationService,
    OrganismClassifier,
)
from bioetl.domain.services.phased_migration_support import (
    PhasedMigrationCoordinator,
    PhasedMigrationSupportService,
)
from bioetl.domain.services.preflight_governance import (
    PreflightGovernanceService,
    PreflightGovernor,
)
from bioetl.domain.services.text_similarity import jaccard_similarity, normalize_text
from bioetl.domain.services.unit_converter import UnitConverter
from bioetl.domain.services.value_validator import ValueValidator

# Deprecated compatibility aliases retained during ADR-041 migration.
DataNormalizationService = DefaultDataNormalizer

__all__ = [
    "CHEMICAL_STANDARDIZATION_POLICY_VERSION",
    "CHEMICAL_STANDARDIZATION_STATUSES",
    "ActivityAggregator",
    "AuthorNormalizationService",
    "AuthorNormalizer",
    "BioactivityNormalizer",
    "ChemicalStandardizationResult",
    "ChemicalStandardizationStatus",
    "ClassificationStats",
    "CompositeValidationService",
    "CompositeValidator",
    "DQMetricsCalculator",
    "DQMetricsInput",
    "DQReportSerializer",
    "DataNormalizationConfig",
    "DataNormalizationService",
    "DefaultDataNormalizationService",
    "DefaultDataNormalizer",
    "EntityIdentityGenerator",
    "IdentityService",
    "MergedMetadataExplainabilityService",
    "MergedMetadataExplainer",
    "NormalizationConfig",
    "NormalizationService",
    "OrganismClassificationService",
    "OrganismClassifier",
    "PhasedMigrationCoordinator",
    "PhasedMigrationSupportService",
    "PreflightGovernanceService",
    "PreflightGovernor",
    "UnitConverter",
    "ValueValidator",
    "jaccard_similarity",
    "normalize_text",
    "standardize_chemical_structure",
]
