"""Registry - unified registry for pipeline factories and transformers.

Consolidated from pipeline_factories.py and transformer_factory.py.
Provides:
- Pipeline factory instances (chembl_activity_factory, etc.)
- Transformer registry and factory functions
- Registration functions for pipelines and transformers

Instance-level registry support (2025-12):
- register_all_pipelines() accepts optional registry parameter
- Default behavior uses global registry for backward compatibility
- Tests can use isolated registries for parallel execution

Usage:
    >>> from bioetl.composition.factories.registry import register_all_pipelines
    >>> register_all_pipelines()  # Call once at application startup

    # For test isolation:
    >>> from bioetl.composition.registry import create_registry
    >>> registry = create_registry()
    >>> register_all_pipelines(registry=registry)

    # Transformer usage:
    >>> from bioetl.composition.factories.registry import create_transformer
    >>> transformer = create_transformer("chembl", "activity")
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.application.pipelines.chembl.assay import ChEMBLAssayPipeline
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.document import ChEMBLDocumentPipeline
from bioetl.application.pipelines.chembl.document_transformer import DocumentTransformer
from bioetl.application.pipelines.chembl.molecule import ChEMBLMoleculePipeline
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.target import ChEMBLTargetPipeline
from bioetl.application.pipelines.chembl.target_component import (
    ChEMBLTargetComponentPipeline,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.pubchem.compound import PubChemCompoundPipeline
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer
from bioetl.composition.factories.pipeline_factory import GenericPipelineFactory
from bioetl.composition.registry import PipelineRegistry, get_default_registry
from bioetl.infrastructure.schemas.gold import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    UniProtProteinGoldSchema,
)
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_DOCUMENT_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort, TracingPort

from bioetl.application.core.base_transformer import BaseTransformer

# =============================================================================
# Transformer Registry (from transformer_factory.py)
# =============================================================================

# Mapping of (provider, entity_type) to transformer class
_TRANSFORMER_REGISTRY: dict[tuple[str, str], type[BaseTransformer]] = {}


def register_transformer(
    provider: str,
    entity_type: str,
    transformer_class: type[BaseTransformer],
) -> None:
    """Register a transformer class for a provider/entity combination.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        transformer_class: The transformer class to register.

    """
    _TRANSFORMER_REGISTRY[(provider, entity_type)] = transformer_class


def create_transformer(
    provider: str,
    entity_type: str,
    tracer: TracingPort | None = None,
    metrics: MetricsPort | None = None,
) -> BaseTransformer:
    """Create a transformer instance for the given provider and entity type.

    This is the main factory function for creating transformers via DI.
    Uses the transformer registry to find the appropriate class.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        tracer: Optional tracing port for distributed tracing (O1 observability).
        metrics: Optional metrics port for duration/error tracking (O1 observability).

    Returns:
        Configured transformer instance with observability.

    Raises:
        KeyError: If no transformer is registered for the provider/entity combination.

    Example:
        >>> transformer = create_transformer("chembl", "activity")
        >>> isinstance(transformer, ActivityTransformer)
        True

    """
    key = (provider, entity_type)
    if key not in _TRANSFORMER_REGISTRY:
        raise KeyError(
            f"No transformer registered for provider='{provider}', "
            f"entity_type='{entity_type}'. "
            f"Available: {list(_TRANSFORMER_REGISTRY.keys())}"
        )

    transformer_class = _TRANSFORMER_REGISTRY[key]
    return transformer_class(provider=provider, tracer=tracer, metrics=metrics)


def get_transformer_class(
    provider: str,
    entity_type: str,
) -> type[BaseTransformer] | None:
    """Get transformer class without instantiating.

    Args:
        provider: Provider name.
        entity_type: Entity type.

    Returns:
        Transformer class if registered, None otherwise.

    """
    return _TRANSFORMER_REGISTRY.get((provider, entity_type))


def register_all_transformers() -> None:
    """Register all known transformers.

    Called during application startup to populate the registry.
    Idempotent - safe to call multiple times.
    """
    # ChEMBL transformers
    register_transformer("chembl", "activity", ActivityTransformer)
    register_transformer("chembl", "assay", AssayTransformer)
    register_transformer("chembl", "document", DocumentTransformer)
    register_transformer("chembl", "molecule", MoleculeTransformer)
    register_transformer("chembl", "target", TargetTransformer)
    register_transformer("chembl", "target_component", TargetComponentTransformer)

    # PubChem transformers
    register_transformer("pubchem", "compound", PubChemCompoundTransformer)

    # UniProt transformers
    register_transformer("uniprot", "protein", UniProtProteinTransformer)

    # PubMed transformers
    register_transformer("pubmed", "publications", PubMedPublicationTransformer)


# =============================================================================
# Pipeline Factory Instances (from pipeline_factories.py)
# =============================================================================

# Thread-safe registration state
_registration_lock = threading.Lock()
_factories_registered = False

# ChEMBL Activity Pipeline
chembl_activity_factory = GenericPipelineFactory(
    pipeline_name="chembl_activity",
    pipeline_class=ChEMBLActivityPipeline,
    provider="chembl",
    silver_schema=CHEMBL_ACTIVITY_SCHEMA,
    gold_schema=ChEMBLActivityGoldSchema,
    transformer_class=ActivityTransformer,
)

# ChEMBL Assay Pipeline
chembl_assay_factory = GenericPipelineFactory(
    pipeline_name="chembl_assay",
    pipeline_class=ChEMBLAssayPipeline,
    provider="chembl",
    silver_schema=CHEMBL_ASSAY_SCHEMA,
    gold_schema=ChEMBLAssayGoldSchema,
    transformer_class=AssayTransformer,
)

# ChEMBL Document Pipeline
chembl_document_factory = GenericPipelineFactory(
    pipeline_name="chembl_document",
    pipeline_class=ChEMBLDocumentPipeline,
    provider="chembl",
    silver_schema=CHEMBL_DOCUMENT_SCHEMA,
    gold_schema=ChEMBLDocumentGoldSchema,
    transformer_class=DocumentTransformer,
)

# ChEMBL Target Pipeline
chembl_target_factory = GenericPipelineFactory(
    pipeline_name="chembl_target",
    pipeline_class=ChEMBLTargetPipeline,
    provider="chembl",
    silver_schema=CHEMBL_TARGET_SCHEMA,
    gold_schema=ChEMBLTargetGoldSchema,
    transformer_class=TargetTransformer,
)

# ChEMBL Target Component Pipeline
chembl_target_component_factory = GenericPipelineFactory(
    pipeline_name="chembl_target_component",
    pipeline_class=ChEMBLTargetComponentPipeline,
    provider="chembl",
    silver_schema=CHEMBL_TARGET_COMPONENT_SCHEMA,
    gold_schema=ChEMBLTargetComponentGoldSchema,
    transformer_class=TargetComponentTransformer,
)

# ChEMBL Molecule Pipeline
chembl_molecule_factory = GenericPipelineFactory(
    pipeline_name="chembl_molecule",
    pipeline_class=ChEMBLMoleculePipeline,
    provider="chembl",
    silver_schema=CHEMBL_MOLECULE_SCHEMA,
    gold_schema=ChEMBLMoleculeGoldSchema,
    transformer_class=MoleculeTransformer,
)

# PubChem Compound Pipeline
pubchem_compound_factory = GenericPipelineFactory(
    pipeline_name="pubchem_compound",
    pipeline_class=PubChemCompoundPipeline,
    provider="pubchem",
    silver_schema=PUBCHEM_COMPOUND_SCHEMA,
    gold_schema=PubChemCompoundGoldSchema,
    transformer_class=PubChemCompoundTransformer,
)

# UniProt Protein Pipeline
uniprot_protein_factory = GenericPipelineFactory(
    pipeline_name="uniprot_protein",
    pipeline_class=UniProtProteinPipeline,
    provider="uniprot",
    silver_schema=UNIPROT_PROTEIN_SCHEMA,
    gold_schema=UniProtProteinGoldSchema,
    transformer_class=UniProtProteinTransformer,
)

# PubMed Publications Pipeline
pubmed_publications_factory = GenericPipelineFactory(
    pipeline_name="pubmed_publications",
    pipeline_class=PubMedPublicationsPipeline,
    provider="pubmed",
    silver_schema=PUBMED_PUBLICATION_SCHEMA,
    gold_schema=PubMedPublicationGoldSchema,
    transformer_class=PubMedPublicationTransformer,
)


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

    Args:
        registry: Target registry instance.
    """
    registry.register_factory(chembl_activity_factory)
    registry.register_factory(chembl_assay_factory)
    registry.register_factory(chembl_document_factory)
    registry.register_factory(chembl_target_factory)
    registry.register_factory(chembl_target_component_factory)
    registry.register_factory(chembl_molecule_factory)
    registry.register_factory(pubchem_compound_factory)
    registry.register_factory(uniprot_protein_factory)
    registry.register_factory(pubmed_publications_factory)


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


__all__ = [
    "chembl_activity_factory",
    "chembl_assay_factory",
    "chembl_document_factory",
    "chembl_molecule_factory",
    "chembl_target_component_factory",
    "chembl_target_factory",
    "create_transformer",
    "get_transformer_class",
    "is_registered",
    "pubchem_compound_factory",
    "pubmed_publications_factory",
    "register_all_pipelines",
    "register_all_transformers",
    "register_transformer",
    "reset_registration",
    "uniprot_protein_factory",
]
