"""Tests for governed provider reference identifier canonicalization."""

from __future__ import annotations

from bioetl.domain.normalization.reference_ids import (
    reference_identifier_families,
    reference_identifier_family,
)


def test_reference_identifier_registry_covers_non_chembl_provider_families() -> None:
    registry = {family.name: family for family in reference_identifier_families()}

    assert {
        "chembl",
        "drugbank",
        "go",
        "interpro",
        "issn",
        "openalex_author",
        "openalex_institution",
        "openalex_topic",
        "openalex_work",
        "orcid",
        "pdb",
        "pfam",
        "reactome",
        "ror",
        "semantic_scholar_author",
        "semantic_scholar_corpus",
        "semantic_scholar_paper",
        "uniprot_accession",
    } <= registry.keys()

    openalex_author = registry["openalex_author"]
    assert openalex_author.normalizer is not None
    assert openalex_author.normalizer("https://openalex.org/a10") == "A10"

    reactome = registry["reactome"]
    assert reactome.normalizer is not None
    assert reactome.normalizer("https://reactome.org/content/detail/r-hsa-164843") == (
        "R-HSA-164843"
    )


def test_semantic_scholar_corpus_id_registry_preserves_numeric_scalar_contract() -> (
    None
):
    corpus = reference_identifier_family("semantic_scholar_corpus")

    assert corpus.storage_representation == "numeric_scalar"
    assert corpus.collection_semantics == "scalar"
    assert corpus.normalizer is None
