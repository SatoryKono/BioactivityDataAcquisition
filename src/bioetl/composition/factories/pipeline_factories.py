# src/bioetl/composition/factories/pipeline_factories.py
"""Consolidated pipeline factory definitions.

This module creates all pipeline factories using the GenericPipelineFactory
pattern with GenericPipeline as the unified pipeline class.

All pipeline-specific behavior is encapsulated in:
- YAML configs (configs/entities/{provider}/{entity}.yaml)
- Transformer classes (injected via DI)
- Silver/Gold schemas

Thread-safety: Registration uses a module-level lock to prevent TOCTOU race conditions.

Instance-level registry support (2025-12):
- register_all_pipelines() accepts optional registry parameter
- Default behavior uses global registry for backward compatibility
- Tests can use isolated registries for parallel execution

Refactored (2025-12):
- All pipelines now use GenericPipeline instead of provider-specific subclasses
- Pipeline definitions consolidated into PIPELINE_CONFIGS for loop-based registration
- Document → Publication naming unified (ADR-024)

Usage:
    >>> from bioetl.composition.factories.pipeline_factories import register_all_pipelines
    >>> register_all_pipelines()  # Call once at application startup

    # For test isolation:
    >>> from bioetl.composition.registry import create_registry
    >>> registry = create_registry()
    >>> register_all_pipelines(registry=registry)
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING, Any, NamedTuple

# Transformers (all DI-injected)
from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.application.pipelines.chembl.assay_parameters_transformer import (
    AssayParametersTransformer,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.cell_line_transformer import (
    CellLineTransformer,
)
from bioetl.application.pipelines.chembl.compound_record_transformer import (
    CompoundRecordTransformer,
)
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)
from bioetl.application.pipelines.chembl.publication_similarity_transformer import (
    PublicationSimilarityTransformer,
)
from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
)
from bioetl.application.pipelines.chembl.publication_transformer import (
    PublicationTransformer,
)
from bioetl.application.pipelines.chembl.subcellular_fraction_transformer import (
    SubcellularFractionTransformer,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.chembl.tissue_transformer import TissueTransformer
from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)
from bioetl.application.pipelines.generic import GenericPipeline
from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)
from bioetl.application.pipelines.uniprot.idmapping_transformer import (
    IDMappingTransformer,
)
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.composition.factories.data_source_factory import DataSourceRegistry
from bioetl.composition.factories.pipeline_factory import GenericPipelineFactory
from bioetl.composition.registry import PipelineRegistry, get_default_registry

# Gold schemas (required for all pipelines)
# Imported from domain.contracts package for clean separation of data contracts
from bioetl.domain.contracts import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLDocumentSimilarityGoldSchema,
    ChEMBLDocumentTermGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTissueGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)

# Pandera Silver schemas (DataFrameModel classes for validation)
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.assay_parameters import AssayParametersSchema
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.protein_classification import (
    ProteinClassificationSchema,
)
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.chembl.publication_similarity import (
    PublicationSimilaritySchema,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.target_component import TargetComponentSchema
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.pubchem.compound import PubchemMoleculeSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema
from bioetl.infrastructure.config import load_pipeline_contract_policy

# Silver schemas (optional PyArrow schemas)
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_CELL_LINE_SCHEMA,
    CHEMBL_COMPOUND_RECORD_SCHEMA,
    CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    CHEMBL_DOCUMENT_TERM_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_PROTEIN_CLASS_SCHEMA,
    CHEMBL_PUBLICATION_SCHEMA,
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CHEMBL_TISSUE_SCHEMA,
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_ID_MAPPING_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.composition.factories.data_source_factory import DataSourceCreator


# =============================================================================
# Pipeline Configuration Registry
# =============================================================================


class PipelineFactoryConfig(NamedTuple):
    """Configuration for creating a pipeline factory.

    This is a value object that holds all metadata needed to create a
    GenericPipelineFactory instance.

    Attributes:
        pipeline_name: Unique identifier for the pipeline (e.g., "chembl_activity")
        provider: Data provider name (e.g., "chembl", "pubchem").
            Used for transformer metadata (content hash, entity ID, tracing).
        transformer_class: Transformer class for Bronze→Silver transformation
        silver_schema: PyArrow schema for Silver layer validation
        gold_schema: Pandera schema for Gold layer validation (required)
        pandera_silver_schema: Pandera DataFrameModel class for Silver validation.
            If provided, PanderaSilverValidator is created and injected into
            SilverWriter for pre-write validation.
        data_source_provider: Override provider name for DataSourceRegistry lookup.
            When set, data source is created using this provider name instead of
            ``provider``. Use when the ProviderRegistry key differs from the
            transformer provider (e.g., "uniprot_idmapping" vs "uniprot").
    """

    pipeline_name: str
    provider: str
    entity_type: str
    transformer_class: type[BaseTransformer]
    silver_schema: pa.Schema | None
    gold_schema: Any  # Any: Pandera DataFrameModel (no common base type)
    pandera_silver_schema: Any = None  # Any: Pandera DataFrameModel...
    data_source_provider: str | None = None


# Consolidated pipeline definitions - single source of truth
PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    # ChEMBL pipelines
    PipelineFactoryConfig(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        transformer_class=ActivityTransformer,
        silver_schema=CHEMBL_ACTIVITY_SCHEMA,
        gold_schema=ChEMBLActivityGoldSchema,
        pandera_silver_schema=ActivitySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_assay",
        provider="chembl",
        entity_type="assay",
        transformer_class=AssayTransformer,
        silver_schema=CHEMBL_ASSAY_SCHEMA,
        gold_schema=ChEMBLAssayGoldSchema,
        pandera_silver_schema=AssaySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_assay_parameters",
        provider="chembl",
        entity_type="assay_parameters",
        transformer_class=AssayParametersTransformer,
        silver_schema=CHEMBL_ASSAY_PARAMETERS_SCHEMA,
        gold_schema=ChEMBLAssayParametersGoldSchema,
        pandera_silver_schema=AssayParametersSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_cell_line",
        provider="chembl",
        entity_type="cell_line",
        transformer_class=CellLineTransformer,
        silver_schema=CHEMBL_CELL_LINE_SCHEMA,
        gold_schema=ChEMBLCellLineGoldSchema,
        pandera_silver_schema=CellLineSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_compound_record",
        provider="chembl",
        entity_type="compound_record",
        transformer_class=CompoundRecordTransformer,
        silver_schema=CHEMBL_COMPOUND_RECORD_SCHEMA,
        gold_schema=ChEMBLCompoundRecordGoldSchema,
        pandera_silver_schema=CompoundRecordSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication",
        provider="chembl",
        entity_type="publication",
        transformer_class=PublicationTransformer,
        silver_schema=CHEMBL_PUBLICATION_SCHEMA,
        gold_schema=ChEMBLDocumentGoldSchema,
        pandera_silver_schema=ChemblPublicationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication_similarity",
        provider="chembl",
        entity_type="publication_similarity",
        transformer_class=PublicationSimilarityTransformer,
        silver_schema=CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
        gold_schema=ChEMBLDocumentSimilarityGoldSchema,
        pandera_silver_schema=PublicationSimilaritySchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_publication_term",
        provider="chembl",
        entity_type="publication_term",
        transformer_class=PublicationTermTransformer,
        silver_schema=CHEMBL_DOCUMENT_TERM_SCHEMA,
        gold_schema=ChEMBLDocumentTermGoldSchema,
        pandera_silver_schema=PublicationTermSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_molecule",
        provider="chembl",
        entity_type="molecule",
        transformer_class=MoleculeTransformer,
        silver_schema=CHEMBL_MOLECULE_SCHEMA,
        gold_schema=ChEMBLMoleculeGoldSchema,
        pandera_silver_schema=MoleculeSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target",
        provider="chembl",
        entity_type="target",
        transformer_class=TargetTransformer,
        silver_schema=CHEMBL_TARGET_SCHEMA,
        gold_schema=ChEMBLTargetGoldSchema,
        pandera_silver_schema=TargetSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_target_component",
        provider="chembl",
        entity_type="target_component",
        transformer_class=TargetComponentTransformer,
        silver_schema=CHEMBL_TARGET_COMPONENT_SCHEMA,
        gold_schema=ChEMBLTargetComponentGoldSchema,
        pandera_silver_schema=TargetComponentSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_protein_class",
        provider="chembl",
        entity_type="protein_class",
        transformer_class=ProteinClassTransformer,
        silver_schema=CHEMBL_PROTEIN_CLASS_SCHEMA,
        gold_schema=ChEMBLProteinClassGoldSchema,
        pandera_silver_schema=ProteinClassificationSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_tissue",
        provider="chembl",
        entity_type="tissue",
        transformer_class=TissueTransformer,
        silver_schema=CHEMBL_TISSUE_SCHEMA,
        gold_schema=ChEMBLTissueGoldSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="chembl_subcellular_fraction",
        provider="chembl",
        entity_type="subcellular_fraction",
        transformer_class=SubcellularFractionTransformer,
        silver_schema=CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
        gold_schema=ChEMBLSubcellularFractionGoldSchema,
    ),
    # PubChem pipeline
    PipelineFactoryConfig(
        pipeline_name="pubchem_compound",
        provider="pubchem",
        entity_type="compound",
        transformer_class=PubChemCompoundTransformer,
        silver_schema=PUBCHEM_COMPOUND_SCHEMA,
        gold_schema=PubChemCompoundGoldSchema,
        pandera_silver_schema=PubchemMoleculeSchema,
    ),
    # UniProt pipelines
    PipelineFactoryConfig(
        pipeline_name="uniprot_protein",
        provider="uniprot",
        entity_type="protein",
        transformer_class=UniProtProteinTransformer,
        silver_schema=UNIPROT_PROTEIN_SCHEMA,
        gold_schema=UniProtProteinGoldSchema,
        pandera_silver_schema=UniprotTargetSchema,
    ),
    PipelineFactoryConfig(
        pipeline_name="uniprot_idmapping",
        provider="uniprot",
        entity_type="idmapping",
        transformer_class=IDMappingTransformer,
        silver_schema=UNIPROT_ID_MAPPING_SCHEMA,
        gold_schema=UniProtIDMappingGoldSchema,
        pandera_silver_schema=IDMappingSchema,
        data_source_provider="uniprot_idmapping",
    ),
    # PubMed pipeline
    PipelineFactoryConfig(
        pipeline_name="pubmed_publication",
        provider="pubmed",
        entity_type="publication",
        transformer_class=PubMedPublicationTransformer,
        silver_schema=PUBMED_PUBLICATION_SCHEMA,
        gold_schema=PubMedPublicationGoldSchema,
        pandera_silver_schema=PubMedPublicationSchema,
    ),
    # CrossRef pipeline
    PipelineFactoryConfig(
        pipeline_name="crossref_publication",
        provider="crossref",
        entity_type="publication",
        transformer_class=CrossRefPublicationTransformer,
        silver_schema=CROSSREF_PUBLICATION_SCHEMA,
        gold_schema=CrossRefPublicationGoldSchema,
        pandera_silver_schema=PublicationEnrichedSchema,
    ),
    # OpenAlex pipeline
    PipelineFactoryConfig(
        pipeline_name="openalex_publication",
        provider="openalex",
        entity_type="publication",
        transformer_class=OpenAlexPublicationTransformer,
        silver_schema=OPENALEX_PUBLICATION_SCHEMA,
        gold_schema=OpenAlexPublicationGoldSchema,
        pandera_silver_schema=OpenAlexPublicationSchema,
    ),
    # Semantic Scholar pipeline
    PipelineFactoryConfig(
        pipeline_name="semanticscholar_publication",
        provider="semanticscholar",
        entity_type="publication",
        transformer_class=SemanticScholarPublicationTransformer,
        silver_schema=SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
        gold_schema=SemanticScholarPublicationGoldSchema,
        pandera_silver_schema=SemanticScholarPublicationSchema,
    ),
)


def _schema_columns(
    schema_class: Any,  # Any: factory wiring; concrete types resolved at runtime
) -> set[str]:  # Any: factory wiring; concrete types resolved at runtime
    """Extract column names from a Pandera DataFrameModel class."""
    try:
        schema = schema_class.to_schema()
    except (
        AttributeError,
        TypeError,
        ValueError,
        RuntimeError,
        ImportError,
    ) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Failed to materialize schema {schema_class}: {exc}") from exc
    return set(schema.columns.keys())


def _resolve_silver_columns(config: PipelineFactoryConfig) -> set[str]:
    """Resolve Silver column names from config's schema sources."""
    if config.pandera_silver_schema is not None:
        return _schema_columns(config.pandera_silver_schema)
    if config.silver_schema is not None:
        return set(config.silver_schema.names)
    raise ValueError(
        f"No Silver schema available for {config.provider}/{config.entity_type}"
    )


def _validate_contract_policy(config: PipelineFactoryConfig) -> None:
    """Preflight check that policy keys exist in Silver and Gold contracts."""
    policy = load_pipeline_contract_policy(config.provider, config.entity_type)

    silver_columns = _resolve_silver_columns(config)
    gold_columns = _schema_columns(config.gold_schema)

    required_keys = set(policy.primary_key) | set(policy.merge_keys)
    missing_in_silver = sorted(required_keys - silver_columns)
    missing_in_gold = sorted(required_keys - gold_columns)

    details: list[str] = []
    if missing_in_silver:
        details.append(f"silver missing {missing_in_silver}")
    if missing_in_gold:
        details.append(f"gold missing {missing_in_gold}")
    if details:
        raise ValueError(
            f"Invalid contract policy for {config.provider}/{config.entity_type}: "
            + ", ".join(details)
        )


def _create_factory(
    config: PipelineFactoryConfig,
) -> GenericPipelineFactory[GenericPipeline]:
    """Create a GenericPipelineFactory from configuration.

    Args:
        config: Pipeline factory configuration

    Returns:
        Configured GenericPipelineFactory instance
    """
    _validate_contract_policy(config)

    # Resolve data source creator: use data_source_provider override if set
    data_source_creator: DataSourceCreator | None = None
    if config.data_source_provider:
        data_source_creator = DataSourceRegistry.get(config.data_source_provider)

    return GenericPipelineFactory(
        pipeline_name=config.pipeline_name,
        pipeline_class=GenericPipeline,
        provider=config.provider,
        silver_schema=config.silver_schema,
        gold_schema=config.gold_schema,
        pandera_silver_schema=config.pandera_silver_schema,
        transformer_class=config.transformer_class,
        data_source_creator=data_source_creator,
    )


# =============================================================================
# Factory Instances (created from PIPELINE_CONFIGS)
# =============================================================================

# Create all factories using loop over configurations
_factories: dict[str, GenericPipelineFactory[GenericPipeline]] = {
    config.pipeline_name: _create_factory(config) for config in PIPELINE_CONFIGS
}

# Export individual factories for backward compatibility
chembl_activity_factory = _factories["chembl_activity"]
chembl_assay_factory = _factories["chembl_assay"]
chembl_assay_parameters_factory = _factories["chembl_assay_parameters"]
chembl_cell_line_factory = _factories["chembl_cell_line"]
chembl_compound_record_factory = _factories["chembl_compound_record"]
chembl_publication_factory = _factories["chembl_publication"]
chembl_publication_similarity_factory = _factories["chembl_publication_similarity"]
chembl_publication_term_factory = _factories["chembl_publication_term"]
chembl_molecule_factory = _factories["chembl_molecule"]
chembl_target_factory = _factories["chembl_target"]
chembl_target_component_factory = _factories["chembl_target_component"]
chembl_tissue_factory = _factories["chembl_tissue"]
chembl_subcellular_fraction_factory = _factories["chembl_subcellular_fraction"]
chembl_protein_class_factory = _factories["chembl_protein_class"]
pubchem_compound_factory = _factories["pubchem_compound"]
uniprot_protein_factory = _factories["uniprot_protein"]
uniprot_idmapping_factory = _factories["uniprot_idmapping"]
pubmed_publication_factory = _factories["pubmed_publication"]
crossref_publication_factory = _factories["crossref_publication"]
openalex_publication_factory = _factories["openalex_publication"]
semanticscholar_publication_factory = _factories["semanticscholar_publication"]


# =============================================================================
# Registration Functions
# =============================================================================

# Thread-safe registration state
_registration_lock = threading.Lock()
_factories_registered = False


def register_all_pipelines(registry: PipelineRegistry | None = None) -> None:
    """Explicitly register all pipeline factories with PipelineRegistry.

    This function is idempotent and thread-safe - calling it multiple times
    or from multiple threads has no effect after the first successful call.

    Uses double-checked locking pattern to minimize lock contention while
    ensuring thread-safe initialization.

    When called with a custom registry, idempotency check is skipped
    (each registry instance is independent).

    Args:
        registry: Optional PipelineRegistry instance. If None, uses the
            default global registry. Pass a custom registry for test isolation.

    Should be called once at application startup (e.g., in cli.py or bootstrap.py).
    """
    global _factories_registered

    # For custom registries, register directly without idempotency check
    if registry is not None:
        _register_factories_to(registry)
        return

    # Default registry: use idempotency guard
    # Fast path: already registered (no lock needed)
    if _factories_registered:
        return

    # Slow path: acquire lock and double-check
    with _registration_lock:
        # Double-check after acquiring lock (TOCTOU prevention)
        if _factories_registered:
            return

        default_registry = get_default_registry()
        _register_factories_to(default_registry)

        _factories_registered = True


def _register_factories_to(registry: PipelineRegistry) -> None:
    """Register all factory instances to the given registry.

    Internal helper for register_all_pipelines().
    Uses loop over _factories dict for DRY registration.

    Args:
        registry: Target registry instance.
    """
    for factory in _factories.values():
        registry.register_factory(factory)


def is_registered() -> bool:
    """Check if factories have been registered.

    Thread-safe check of registration state.

    Returns:
        True if register_all_pipelines() has been called.
    """
    # Reading a bool is atomic in Python, no lock needed for read
    return _factories_registered


def reset_registration() -> None:
    """Reset registration state (for testing only).

    Thread-safe reset of registration flag. Also clears the default PipelineRegistry.
    WARNING: Only use in tests. Not for production.

    Note: For isolated tests, prefer creating a new registry instance with
    create_registry() rather than using reset_registration().
    """
    global _factories_registered
    with _registration_lock:
        get_default_registry().clear()
        _factories_registered = False


def get_factory(pipeline_name: str) -> GenericPipelineFactory[GenericPipeline]:
    """Get a pipeline factory by name.

    Convenience function for accessing factories without going through registry.

    Args:
        pipeline_name: Name of the pipeline (e.g., "chembl_activity")

    Returns:
        GenericPipelineFactory instance

    Raises:
        KeyError: If pipeline_name is not found
    """
    if pipeline_name not in _factories:
        available = sorted(_factories.keys())
        raise KeyError(f"Unknown pipeline: {pipeline_name}. Available: {available}")
    return _factories[pipeline_name]


def list_available_pipelines() -> list[str]:
    """List all available pipeline names.

    Returns:
        Sorted list of pipeline names
    """
    return sorted(_factories.keys())


_PIPELINE_FACTORY_API = (
    get_factory,
    list_available_pipelines,
    reset_registration,
)

__all__ = [
    "PIPELINE_CONFIGS",
    "PipelineFactoryConfig",
    "chembl_activity_factory",
    "chembl_assay_factory",
    "chembl_assay_parameters_factory",
    "chembl_cell_line_factory",
    "chembl_compound_record_factory",
    "chembl_molecule_factory",
    "chembl_protein_class_factory",
    "chembl_publication_factory",
    "chembl_publication_similarity_factory",
    "chembl_publication_term_factory",
    "chembl_subcellular_fraction_factory",
    "chembl_target_component_factory",
    "chembl_target_factory",
    "chembl_tissue_factory",
    "crossref_publication_factory",
    "get_factory",
    "is_registered",
    "list_available_pipelines",
    "openalex_publication_factory",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_pipelines",
    "reset_registration",
    "semanticscholar_publication_factory",
    "uniprot_idmapping_factory",
    "uniprot_protein_factory",
]
