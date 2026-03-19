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


def test_openalex_package_root_does_not_reexport_private_factory() -> None:
    """OpenAlex package root should expose the adapter, not the private factory helper."""
    package_module = import_module("bioetl.infrastructure.adapters.openalex")

    assert hasattr(package_module, "OpenAlexAdapter")
    assert not hasattr(package_module, "_create_openalex_adapter")


def test_crossref_package_root_stays_adapter_first() -> None:
    """CrossRef package root should not expose decomposed helper components."""
    package_module = import_module("bioetl.infrastructure.adapters.crossref")

    assert hasattr(package_module, "CrossRefAdapter")
    assert not hasattr(package_module, "CrossRefFetchFlow")
    assert not hasattr(package_module, "CrossRefQueryBuilder")
    assert not hasattr(package_module, "CrossRefResponseMapper")


def test_uniprot_package_root_stays_adapter_first() -> None:
    """UniProt package root should not expose the adjunct ID mapping client surface."""
    package_module = import_module("bioetl.infrastructure.adapters.uniprot")

    assert hasattr(package_module, "UniProtAdapter")
    assert not hasattr(package_module, "UniProtIDMappingClient")
    assert not hasattr(package_module, "IDMappingJobError")
    assert not hasattr(package_module, "IDMappingTimeoutError")
