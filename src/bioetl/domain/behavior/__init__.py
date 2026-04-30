"""Canonical pure domain behavior surface."""

from __future__ import annotations

from bioetl.domain.behavior.activity_aggregator import ActivityAggregator
from bioetl.domain.behavior.author_normalization_service import AuthorNormalizer
from bioetl.domain.behavior.chemical_standardization import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
    ChemicalStandardizationResult,
    ChemicalStandardizationStatus,
    standardize_chemical_structure,
)
from bioetl.domain.behavior.composite_validation_layer import CompositeValidator
from bioetl.domain.behavior.data_normalization_config import DataNormalizationConfig
from bioetl.domain.behavior.data_normalization_service import DefaultDataNormalizer
from bioetl.domain.behavior.dq_metrics_calculator import (
    DQMetricsCalculator,
    DQMetricsInput,
)
from bioetl.domain.behavior.dq_serializer import DQReportSerializer
from bioetl.domain.behavior.identity_service import EntityIdentityGenerator
from bioetl.domain.behavior.merged_metadata_explainability import (
    MergedMetadataExplainer,
)
from bioetl.domain.behavior.normalization_config import NormalizationConfig
from bioetl.domain.behavior.normalization_service import BioactivityNormalizer
from bioetl.domain.behavior.organism_classification_service import (
    ClassificationStats,
    OrganismClassifier,
)
from bioetl.domain.behavior.phased_migration_support import PhasedMigrationCoordinator
from bioetl.domain.behavior.preflight_governance import PreflightGovernor
from bioetl.domain.behavior.text_similarity import jaccard_similarity, normalize_text
from bioetl.domain.behavior.unit_converter import UnitConverter
from bioetl.domain.behavior.value_validator import ValueValidator

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
