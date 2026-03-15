"""Tests for canonical provider adapter entrypoints."""

from __future__ import annotations

from importlib import import_module


def test_pubmed_canonical_entrypoint_reexports_legacy_adapter() -> None:
    """Canonical PubMed client module should preserve the legacy adapter object."""
    canonical_cls = import_module(
        "bioetl.infrastructure.adapters.pubmed.client"
    ).PubMedAdapter
    legacy_cls = import_module(
        "bioetl.infrastructure.adapters.pubmed.pubmed_client"
    ).PubMedAdapter
    assert canonical_cls is legacy_cls


def test_pubmed_canonical_entrypoint_exposes_public_factory_alias() -> None:
    """Canonical PubMed client module should expose a public adapter factory."""
    canonical_module = import_module("bioetl.infrastructure.adapters.pubmed.client")
    canonical_factory = canonical_module.create_pubmed_adapter
    legacy_factory = import_module(
        "bioetl.infrastructure.adapters.pubmed.pubmed_client"
    )._create_pubmed_adapter

    assert canonical_factory is legacy_factory
    assert not hasattr(canonical_module, "_create_pubmed_adapter")


def test_semanticscholar_canonical_entrypoint_reexports_legacy_adapter() -> None:
    """Canonical Semantic Scholar client module should preserve the legacy adapter object."""
    canonical_cls = import_module(
        "bioetl.infrastructure.adapters.semanticscholar.client"
    ).SemanticScholarAdapter
    legacy_cls = import_module(
        "bioetl.infrastructure.adapters.semanticscholar.adapter"
    ).SemanticScholarAdapter
    assert canonical_cls is legacy_cls
