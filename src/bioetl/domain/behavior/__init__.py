"""Canonical pure domain behavior surface with lazy exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.behavior.activity_aggregator import (
        ActivityAggregator as ActivityAggregator,
    )
    from bioetl.domain.behavior.author_normalization_service import (
        AuthorNormalizer as AuthorNormalizer,
    )
    from bioetl.domain.behavior.chemical_standardization import (
        CHEMICAL_STANDARDIZATION_POLICY_VERSION as CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    )
    from bioetl.domain.behavior.chemical_standardization import (
        CHEMICAL_STANDARDIZATION_STATUSES as CHEMICAL_STANDARDIZATION_STATUSES,
    )
    from bioetl.domain.behavior.chemical_standardization import (
        ChemicalStandardizationResult as ChemicalStandardizationResult,
    )
    from bioetl.domain.behavior.chemical_standardization import (
        ChemicalStandardizationStatus as ChemicalStandardizationStatus,
    )
    from bioetl.domain.behavior.chemical_standardization import (
        standardize_chemical_structure as standardize_chemical_structure,
    )
    from bioetl.domain.behavior.composite_validation_layer import (
        CompositeValidator as CompositeValidator,
    )
    from bioetl.domain.behavior.data_normalization_config import (
        DataNormalizationConfig as DataNormalizationConfig,
    )
    from bioetl.domain.behavior.data_normalization_service import (
        DefaultDataNormalizer as DefaultDataNormalizer,
    )
    from bioetl.domain.behavior.dq_metrics_calculator import (
        DQMetricsCalculator as DQMetricsCalculator,
    )
    from bioetl.domain.behavior.dq_metrics_calculator import (
        DQMetricsInput as DQMetricsInput,
    )
    from bioetl.domain.behavior.dq_serializer import (
        DQReportSerializer as DQReportSerializer,
    )
    from bioetl.domain.behavior.identity_service import (
        EntityIdentityGenerator as EntityIdentityGenerator,
    )
    from bioetl.domain.behavior.merged_metadata_explainability import (
        MergedMetadataExplainer as MergedMetadataExplainer,
    )
    from bioetl.domain.behavior.normalization_config import (
        NormalizationConfig as NormalizationConfig,
    )
    from bioetl.domain.behavior.normalization_service import (
        BioactivityNormalizer as BioactivityNormalizer,
    )
    from bioetl.domain.behavior.organism_classification_service import (
        ClassificationStats as ClassificationStats,
    )
    from bioetl.domain.behavior.organism_classification_service import (
        OrganismClassifier as OrganismClassifier,
    )
    from bioetl.domain.behavior.phased_migration_support import (
        PhasedMigrationCoordinator as PhasedMigrationCoordinator,
    )
    from bioetl.domain.behavior.preflight_governance import (
        PreflightGovernor as PreflightGovernor,
    )
    from bioetl.domain.behavior.text_similarity import (
        jaccard_similarity as jaccard_similarity,
    )
    from bioetl.domain.behavior.text_similarity import (
        normalize_text as normalize_text,
    )
    from bioetl.domain.behavior.unit_converter import UnitConverter as UnitConverter
    from bioetl.domain.behavior.value_validator import (
        ValueValidator as ValueValidator,
    )

_PUBLIC_EXPORTS = {
    "CHEMICAL_STANDARDIZATION_POLICY_VERSION": (
        "bioetl.domain.behavior.chemical_standardization",
        "CHEMICAL_STANDARDIZATION_POLICY_VERSION",
    ),
    "CHEMICAL_STANDARDIZATION_STATUSES": (
        "bioetl.domain.behavior.chemical_standardization",
        "CHEMICAL_STANDARDIZATION_STATUSES",
    ),
    "ActivityAggregator": (
        "bioetl.domain.behavior.activity_aggregator",
        "ActivityAggregator",
    ),
    "AuthorNormalizer": (
        "bioetl.domain.behavior.author_normalization_service",
        "AuthorNormalizer",
    ),
    "BioactivityNormalizer": (
        "bioetl.domain.behavior.normalization_service",
        "BioactivityNormalizer",
    ),
    "ChemicalStandardizationResult": (
        "bioetl.domain.behavior.chemical_standardization",
        "ChemicalStandardizationResult",
    ),
    "ChemicalStandardizationStatus": (
        "bioetl.domain.behavior.chemical_standardization",
        "ChemicalStandardizationStatus",
    ),
    "ClassificationStats": (
        "bioetl.domain.behavior.organism_classification_service",
        "ClassificationStats",
    ),
    "CompositeValidator": (
        "bioetl.domain.behavior.composite_validation_layer",
        "CompositeValidator",
    ),
    "DQMetricsCalculator": (
        "bioetl.domain.behavior.dq_metrics_calculator",
        "DQMetricsCalculator",
    ),
    "DQMetricsInput": (
        "bioetl.domain.behavior.dq_metrics_calculator",
        "DQMetricsInput",
    ),
    "DQReportSerializer": (
        "bioetl.domain.behavior.dq_serializer",
        "DQReportSerializer",
    ),
    "DataNormalizationConfig": (
        "bioetl.domain.behavior.data_normalization_config",
        "DataNormalizationConfig",
    ),
    "DefaultDataNormalizer": (
        "bioetl.domain.behavior.data_normalization_service",
        "DefaultDataNormalizer",
    ),
    "EntityIdentityGenerator": (
        "bioetl.domain.behavior.identity_service",
        "EntityIdentityGenerator",
    ),
    "MergedMetadataExplainer": (
        "bioetl.domain.behavior.merged_metadata_explainability",
        "MergedMetadataExplainer",
    ),
    "NormalizationConfig": (
        "bioetl.domain.behavior.normalization_config",
        "NormalizationConfig",
    ),
    "OrganismClassifier": (
        "bioetl.domain.behavior.organism_classification_service",
        "OrganismClassifier",
    ),
    "PhasedMigrationCoordinator": (
        "bioetl.domain.behavior.phased_migration_support",
        "PhasedMigrationCoordinator",
    ),
    "PreflightGovernor": (
        "bioetl.domain.behavior.preflight_governance",
        "PreflightGovernor",
    ),
    "UnitConverter": (
        "bioetl.domain.behavior.unit_converter",
        "UnitConverter",
    ),
    "ValueValidator": (
        "bioetl.domain.behavior.value_validator",
        "ValueValidator",
    ),
    "jaccard_similarity": (
        "bioetl.domain.behavior.text_similarity",
        "jaccard_similarity",
    ),
    "normalize_text": (
        "bioetl.domain.behavior.text_similarity",
        "normalize_text",
    ),
    "standardize_chemical_structure": (
        "bioetl.domain.behavior.chemical_standardization",
        "standardize_chemical_structure",
    ),
}

__all__ = list(_PUBLIC_EXPORTS)


def __getattr__(name: str) -> object:  # pragma: no cover
    if TYPE_CHECKING:
        raise AttributeError
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
