"""Legacy import bridge for ``bioetl.domain.services``.

First-party code must use ``bioetl.domain.behavior``. This package remains only
to keep old public imports resolving until the registered compatibility sunset.
"""

from __future__ import annotations

import sys
from importlib import import_module

from bioetl.domain.behavior import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
    ActivityAggregator,
    AuthorNormalizer,
    BioactivityNormalizer,
    ChemicalStandardizationResult,
    ChemicalStandardizationStatus,
    ClassificationStats,
    CompositeValidator,
    DataNormalizationConfig,
    DefaultDataNormalizer,
    DQMetricsCalculator,
    DQMetricsInput,
    DQReportSerializer,
    EntityIdentityGenerator,
    MergedMetadataExplainer,
    NormalizationConfig,
    OrganismClassifier,
    PhasedMigrationCoordinator,
    PreflightGovernor,
    UnitConverter,
    ValueValidator,
    jaccard_similarity,
    normalize_text,
    standardize_chemical_structure,
)

_COMPAT_SUBMODULES = (
    "_author_helpers",
    "_dq_serializer_html",
    "_preflight_governance_helpers",
    "_preflight_governance_types",
    "activity_aggregator",
    "aggregation_validator",
    "author_normalization_service",
    "chemical_standardization",
    "composite_metadata_cv",
    "composite_metadata_helpers",
    "composite_validation_helpers",
    "composite_validation_layer",
    "cross_validation_helpers",
    "cross_validation_validator",
    "data_normalization_config",
    "data_normalization_service",
    "dataset_content_identity",
    "dq_metrics_calculator",
    "dq_policy_resolver",
    "dq_serializer",
    "identity_service",
    "merged_metadata_explainability",
    "normalization_config",
    "normalization_service",
    "organism_classification_service",
    "organism_classification_service_filtering",
    "organism_classification_service_models",
    "phased_migration_support",
    "preflight_governance",
    "preflight_governance_reporting",
    "schema_classifier",
    "schema_classifier_helpers",
    "schema_metadata_extractor",
    "staged_enforcement",
    "text_similarity",
    "unit_converter",
    "validation_helpers",
    "validation_result_envelopes",
    "value_validator",
    "value_validator_rules",
)

for _name in _COMPAT_SUBMODULES:
    sys.modules[f"{__name__}.{_name}"] = import_module(
        f"bioetl.domain.behavior.{_name}"
    )

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
