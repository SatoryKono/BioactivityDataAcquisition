# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for canonical provider adapter entrypoints."""

from __future__ import annotations

from importlib import import_module

import pytest


pytestmark = pytest.mark.unit


def test_pubmed_package_root_reexports_canonical_adapter() -> None:
    """PubMed package root should expose canonical adapter objects."""
    package_module = import_module("bioetl.infrastructure.adapters.pubmed")
    canonical_cls = import_module(
        "bioetl.infrastructure.adapters.pubmed.adapter"
    ).PubMedAdapter
    assert package_module.PubMedAdapter is canonical_cls

    with pytest.raises(ModuleNotFoundError):
        import_module("bioetl.infrastructure.adapters.pubmed.pubmed_client")


def test_pubmed_canonical_adapter_module_exposes_public_factory_alias() -> None:
    """Canonical PubMed adapter module should expose a public adapter factory."""
    package_module = import_module("bioetl.infrastructure.adapters.pubmed")
    canonical_module = import_module("bioetl.infrastructure.adapters.pubmed.adapter")
    canonical_factory = canonical_module.create_pubmed_adapter

    assert package_module.create_pubmed_adapter is canonical_factory
    assert hasattr(canonical_module, "_create_pubmed_adapter")
    assert canonical_factory is canonical_module._create_pubmed_adapter


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
