# src/bioetl/composition/factories/transformer_factory.py
"""Transformer Factory for DI-based transformer creation.

This module provides factory functions for creating transformers,
enabling Dependency Injection instead of creating transformers inside pipelines.

Usage:
    >>> from bioetl.composition.factories.transformer_factory import create_transformer
    >>> transformer = create_transformer("chembl", "activity")
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from importlib import import_module
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.ports import (
        DataNormalizationPort,
        MetricsPort,
        PiiHasherPort,
        TracingPort,
    )
    from bioetl.domain.services import IdentityService

# Mapping of (provider, entity_type) to transformer class
_TRANSFORMER_REGISTRY: dict[tuple[str, str], type[BaseTransformer]] = {}


@dataclass(frozen=True, slots=True)
class TransformerRegistrationSpec:
    """Declarative transformer registration entry."""

    provider: str
    entity_type: str
    module_path: str
    class_name: str


_TransformerSpecRow = tuple[str, str, str, str]
_TRANSFORMER_SPECS: Final[tuple[_TransformerSpecRow, ...]] = (
    (
        "chembl",
        "activity",
        "bioetl.application.pipelines.chembl.activity_transformer",
        "ActivityTransformer",
    ),
    (
        "chembl",
        "assay",
        "bioetl.application.pipelines.chembl.assay_transformer",
        "AssayTransformer",
    ),
    (
        "chembl",
        "assay_parameters",
        "bioetl.application.pipelines.chembl.assay_parameters_transformer",
        "AssayParametersTransformer",
    ),
    (
        "chembl",
        "cell_line",
        "bioetl.application.pipelines.chembl.cell_line_transformer",
        "CellLineTransformer",
    ),
    (
        "chembl",
        "compound_record",
        "bioetl.application.pipelines.chembl.compound_record_transformer",
        "CompoundRecordTransformer",
    ),
    (
        "chembl",
        "document",
        "bioetl.application.pipelines.chembl.publication_transformer",
        "PublicationTransformer",
    ),
    (
        "chembl",
        "document_similarity",
        "bioetl.application.pipelines.chembl.publication_similarity_transformer",
        "PublicationSimilarityTransformer",
    ),
    (
        "chembl",
        "document_term",
        "bioetl.application.pipelines.chembl.publication_term_transformer",
        "PublicationTermTransformer",
    ),
    (
        "chembl",
        "molecule",
        "bioetl.application.pipelines.chembl.molecule_transformer",
        "MoleculeTransformer",
    ),
    (
        "chembl",
        "subcellular_fraction",
        "bioetl.application.pipelines.chembl.subcellular_fraction_transformer",
        "SubcellularFractionTransformer",
    ),
    (
        "chembl",
        "protein_class",
        "bioetl.application.pipelines.chembl.protein_class_transformer",
        "ProteinClassTransformer",
    ),
    (
        "chembl",
        "target",
        "bioetl.application.pipelines.chembl.target_transformer",
        "TargetTransformer",
    ),
    (
        "chembl",
        "target_component",
        "bioetl.application.pipelines.chembl.target_component_transformer",
        "TargetComponentTransformer",
    ),
    (
        "pubchem",
        "compound",
        "bioetl.application.pipelines.pubchem.transformer",
        "PubChemCompoundTransformer",
    ),
    (
        "uniprot",
        "protein",
        "bioetl.application.pipelines.uniprot.transformer",
        "UniProtProteinTransformer",
    ),
    (
        "uniprot",
        "idmapping",
        "bioetl.application.pipelines.uniprot.idmapping_transformer",
        "IDMappingTransformer",
    ),
    (
        "pubmed",
        "publication",
        "bioetl.application.pipelines.pubmed.transformer",
        "PubMedPublicationTransformer",
    ),
    (
        "crossref",
        "publication",
        "bioetl.application.pipelines.crossref.transformer",
        "CrossRefPublicationTransformer",
    ),
    (
        "openalex",
        "publication",
        "bioetl.application.pipelines.openalex.transformer",
        "OpenAlexPublicationTransformer",
    ),
    (
        "semanticscholar",
        "publication",
        "bioetl.application.pipelines.semanticscholar.transformer",
        "SemanticScholarPublicationTransformer",
    ),
)
_BUILTIN_TRANSFORMER_SPECS: Final[tuple[TransformerRegistrationSpec, ...]] = tuple(
    TransformerRegistrationSpec(*spec) for spec in _TRANSFORMER_SPECS
)


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
    silver_filters: SilverFilterConfig | None = None,
    gold_filters: GoldFilterConfig | None = None,
    identity_service: IdentityService | None = None,
    pii_hasher: PiiHasherPort | None = None,
    data_normalizer: DataNormalizationPort | None = None,
) -> BaseTransformer:
    """Create a transformer instance for the given provider and entity type.

    This is the main factory function for creating transformers via DI.
    Uses the transformer registry to find the appropriate class.

    Args:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        entity_type: Entity type (e.g., 'activity', 'compound').
        tracer: Optional tracing port for distributed tracing (O1 observability).
        metrics: Optional metrics port for duration/error tracking (O1 observability).
        silver_filters: Optional domain-level filter configuration for Silver layer.
        gold_filters: Optional filter configuration for Gold layer.
        identity_service: Service for computing entity IDs and content hashes.
            Defaults to a new IdentityService instance in BaseTransformer.
        pii_hasher: Optional PII hasher for hashing author names and other PII.
            Defaults to NoOpPiiHasher (no hashing) in BaseTransformer.
        data_normalizer: Optional data normalization service for text normalization
            (DOI, PMID, authors, HTML). Defaults to DataNormalizationService.

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
    return transformer_class(
        provider=provider,
        entity_type=entity_type,
        tracer=tracer,
        metrics=metrics,
        silver_filters=silver_filters,
        gold_filters=gold_filters,
        identity_service=identity_service,
        pii_hasher=pii_hasher,
        data_normalizer=data_normalizer,
    )


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


def _load_transformer_class(module_path: str, class_name: str) -> type:
    """Load transformer class by dotted module path and class name.

    Args:
        module_path: Dotted Python module path (e.g.,
            'bioetl.application.pipelines.chembl.activity_transformer').
        class_name: Name of the transformer class within the module.

    Returns:
        Transformer class type loaded from the module.

    Raises:
        TypeError: If the resolved attribute is not a class.
    """
    module = import_module(module_path)
    transformer_class = getattr(module, class_name)
    if not isinstance(transformer_class, type):
        raise TypeError(
            f"Expected class for {module_path}.{class_name}, "
            f"got {type(transformer_class).__name__}"
        )
    return transformer_class


def get_builtin_transformer_specs() -> tuple[TransformerRegistrationSpec, ...]:
    """Return declarative specs for built-in transformer registrations."""
    return _BUILTIN_TRANSFORMER_SPECS


def register_transformer_spec(
    spec: TransformerRegistrationSpec,
    *,
    load_transformer_class_fn: Callable[[str, str], type[BaseTransformer]]
    | None = None,
) -> None:
    """Register one transformer from a declarative module/class specification."""
    loader = (
        _load_transformer_class
        if load_transformer_class_fn is None
        else load_transformer_class_fn
    )
    register_transformer(
        spec.provider,
        spec.entity_type,
        loader(spec.module_path, spec.class_name),
    )


def register_all_transformers(
    specs: Iterable[TransformerRegistrationSpec] | None = None,
    *,
    load_transformer_class_fn: Callable[[str, str], type[BaseTransformer]]
    | None = None,
) -> None:
    """Register all known transformers.

    Called during application startup to populate the registry.
    Idempotent - safe to call multiple times.
    """
    spec_iter = get_builtin_transformer_specs() if specs is None else specs
    for spec in spec_iter:
        register_transformer_spec(
            spec,
            load_transformer_class_fn=load_transformer_class_fn,
        )


__all__ = [
    "TransformerRegistrationSpec",
    "create_transformer",
    "get_builtin_transformer_specs",
    "get_transformer_class",
    "register_all_transformers",
    "register_transformer",
    "register_transformer_spec",
]
