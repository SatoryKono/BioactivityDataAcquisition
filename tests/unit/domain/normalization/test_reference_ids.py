"""Tests for governed provider reference identifier canonicalization."""

from __future__ import annotations

from bioetl.domain.normalization.reference_ids import (
    reference_identifier_families,
    reference_identifier_family,
)


def _legacy_transport_url(secure_url: str) -> str:
    return "http" + secure_url.removeprefix("https")


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


def test_reference_identifier_registry_normalizes_legacy_transport_aliases() -> None:
    hex_id = "0123456789abcdef0123456789abcdef01234567"
    cases = (
        (
            "go",
            _legacy_transport_url("https://purl.obolibrary.org/obo/GO_0005524"),
            "GO:0005524",
        ),
        (
            "interpro",
            _legacy_transport_url(
                "https://www.ebi.ac.uk/interpro/entry/interpro/IPR000001"
            ),
            "IPR000001",
        ),
        (
            "pfam",
            _legacy_transport_url("https://pfam.xfam.org/family/PF00001"),
            "PF00001",
        ),
        (
            "reactome",
            _legacy_transport_url("https://reactome.org/content/detail/r-hsa-164843"),
            "R-HSA-164843",
        ),
        (
            "pdb",
            _legacy_transport_url("https://www.rcsb.org/structure/1abc"),
            "1ABC",
        ),
        (
            "orcid",
            _legacy_transport_url("https://orcid.org/0000-0001-2345-6789"),
            "0000-0001-2345-6789",
        ),
        (
            "ror",
            _legacy_transport_url("https://ror.org/0ABCDEF12/"),
            "https://ror.org/0abcdef12",
        ),
        ("openalex_author", _legacy_transport_url("https://openalex.org/a10"), "A10"),
        (
            "semantic_scholar_paper",
            _legacy_transport_url(f"https://www.semanticscholar.org/paper/{hex_id}"),
            hex_id,
        ),
        (
            "semantic_scholar_author",
            _legacy_transport_url(f"https://www.semanticscholar.org/author/{hex_id}"),
            hex_id,
        ),
    )

    for family_name, raw_value, expected in cases:
        normalizer = reference_identifier_family(family_name).normalizer

        assert normalizer is not None
        assert normalizer(raw_value) == expected


def test_uniprot_reference_identifier_registry_canonicalizes_uppercase_accessions() -> (
    None
):
    normalizer = reference_identifier_family("uniprot_accession").normalizer

    assert normalizer is not None
    assert normalizer(" p12345 ") == "P12345"
    assert normalizer("q9y6k9") == "Q9Y6K9"


def test_semantic_scholar_corpus_id_registry_preserves_numeric_scalar_contract() -> (
    None
):
    corpus = reference_identifier_family("semantic_scholar_corpus")

    assert corpus.storage_representation == "numeric_scalar"
    assert corpus.collection_semantics == "scalar"
    assert corpus.normalizer is None
