"""Tests for canonical provider adapter entrypoints."""

from __future__ import annotations

from importlib import import_module


def test_pubmed_package_root_reexports_canonical_adapter() -> None:
    """PubMed package root should expose canonical adapter objects."""
    package_module = import_module("bioetl.infrastructure.adapters.pubmed")
    canonical_cls = import_module(
        "bioetl.infrastructure.adapters.pubmed.adapter"
    ).PubMedAdapter
    legacy_module_cls = import_module(
        "bioetl.infrastructure.adapters.pubmed.pubmed_client"
    ).PubMedAdapter
    assert package_module.PubMedAdapter is canonical_cls is legacy_module_cls


def test_pubmed_canonical_adapter_module_exposes_public_factory_alias() -> None:
    """Canonical PubMed adapter module should expose a public adapter factory."""
    package_module = import_module("bioetl.infrastructure.adapters.pubmed")
    canonical_module = import_module("bioetl.infrastructure.adapters.pubmed.adapter")
    canonical_factory = canonical_module.create_pubmed_adapter
    legacy_factory = import_module(
        "bioetl.infrastructure.adapters.pubmed.pubmed_client"
    )._create_pubmed_adapter

    assert package_module.create_pubmed_adapter is canonical_factory
    assert canonical_factory is legacy_factory
    assert hasattr(canonical_module, "_create_pubmed_adapter")


def test_semanticscholar_package_root_reexports_canonical_adapter() -> None:
    """Semantic Scholar package root should expose the canonical adapter object."""
    package_module = import_module("bioetl.infrastructure.adapters.semanticscholar")
    canonical_cls = import_module(
        "bioetl.infrastructure.adapters.semanticscholar.adapter"
    ).SemanticScholarAdapter
    assert package_module.SemanticScholarAdapter is canonical_cls


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
    assert not hasattr(package_module, "CrossRefQueryPlanner")
    assert not hasattr(package_module, "CrossRefResponseMapper")


def test_uniprot_package_root_stays_adapter_first() -> None:
    """UniProt package root should not expose the adjunct ID mapping client surface."""
    package_module = import_module("bioetl.infrastructure.adapters.uniprot")

    assert hasattr(package_module, "UniProtAdapter")
    assert not hasattr(package_module, "UniProtIDMappingClient")
    assert not hasattr(package_module, "IDMappingJobError")
    assert not hasattr(package_module, "IDMappingTimeoutError")
