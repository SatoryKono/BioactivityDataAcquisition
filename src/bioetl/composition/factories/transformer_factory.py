# src/bioetl/composition/factories/transformer_factory.py
"""Transformer Factory for DI-based transformer creation.

This module provides factory functions for creating transformers,
enabling Dependency Injection instead of creating transformers inside pipelines.

Usage:
    >>> from bioetl.composition.factories.transformer_factory import create_transformer
    >>> transformer = create_transformer("chembl", "activity")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.domain.ports import MetricsPort, TracingPort

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
    # Import here to avoid circular imports
    from bioetl.application.pipelines.chembl.activity_transformer import (
        ActivityTransformer,
    )
    from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
    from bioetl.application.pipelines.chembl.document_term_transformer import (
        DocumentTermTransformer,
    )
    from bioetl.application.pipelines.chembl.document_transformer import (
        DocumentTransformer,
    )
    from bioetl.application.pipelines.chembl.molecule_transformer import (
        MoleculeTransformer,
    )
    from bioetl.application.pipelines.chembl.target_component_transformer import (
        TargetComponentTransformer,
    )
    from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
    from bioetl.application.pipelines.pubchem.transformer import (
        PubChemCompoundTransformer,
    )
    from bioetl.application.pipelines.pubmed.transformer import (
        PubMedPublicationTransformer,
    )
    from bioetl.application.pipelines.uniprot.transformer import (
        UniProtProteinTransformer,
    )

    # ChEMBL transformers
    register_transformer("chembl", "activity", ActivityTransformer)
    register_transformer("chembl", "assay", AssayTransformer)
    register_transformer("chembl", "document", DocumentTransformer)
    register_transformer("chembl", "document_term", DocumentTermTransformer)
    register_transformer("chembl", "molecule", MoleculeTransformer)
    register_transformer("chembl", "target", TargetTransformer)
    register_transformer("chembl", "target_component", TargetComponentTransformer)

    # PubChem transformers
    register_transformer("pubchem", "compound", PubChemCompoundTransformer)

    # UniProt transformers
    register_transformer("uniprot", "protein", UniProtProteinTransformer)

    # PubMed transformers
    register_transformer("pubmed", "publications", PubMedPublicationTransformer)


__all__ = [
    "create_transformer",
    "get_transformer_class",
    "register_all_transformers",
    "register_transformer",
]
