"""Governed registry metadata for provider reference identifier families."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

ReferenceNormalizer = Callable[[object], object]


@dataclass(frozen=True)
class ReferenceIdentifierFamily:
    """Registry metadata for provider reference identifiers."""

    name: str
    storage_representation: str
    collection_semantics: str
    normalizer: ReferenceNormalizer | None
    description: str


_REFERENCE_IDENTIFIER_FAMILY_SPECS: tuple[tuple[str, str, str, str, str], ...] = (
    ("orcid", "string", "set_like", "orcid", "ORCID author/person identifiers."),
    ("issn", "string", "set_like", "issn", "ISSN journal/source identifiers."),
    (
        "ror",
        "string",
        "set_like",
        "ror",
        "ROR institution identifiers stored as canonical ROR URLs.",
    ),
    (
        "openalex_author",
        "string",
        "set_like",
        "openalex_author",
        "OpenAlex author IDs with A-prefix canonical form.",
    ),
    (
        "openalex_institution",
        "string",
        "set_like",
        "openalex_institution",
        "OpenAlex institution IDs with I-prefix canonical form.",
    ),
    (
        "openalex_topic",
        "json_object_or_array",
        "set_like",
        "openalex_topic",
        "OpenAlex topic IDs embedded in topic JSON payloads.",
    ),
    (
        "openalex_work",
        "string",
        "scalar",
        "openalex_work",
        "OpenAlex work IDs with W-prefix canonical form.",
    ),
    (
        "semantic_scholar_paper",
        "string",
        "scalar_or_set_like",
        "semantic_scholar_paper",
        "Semantic Scholar paper/author hash identifiers.",
    ),
    (
        "semantic_scholar_author",
        "string",
        "set_like",
        "semantic_scholar_author",
        "Semantic Scholar author hash identifiers.",
    ),
    (
        "semantic_scholar_corpus",
        "numeric_scalar",
        "scalar",
        "",
        "Semantic Scholar corpusId is numeric, not a string-like reference ID.",
    ),
    (
        "uniprot_accession",
        "string",
        "scalar_or_set_like",
        "uniprot_accession",
        "UniProt accession identifiers.",
    ),
    (
        "go",
        "json_array",
        "set_like",
        "go",
        "Gene Ontology cross-reference identifiers.",
    ),
    (
        "interpro",
        "json_array",
        "set_like",
        "interpro",
        "InterPro cross-reference identifiers.",
    ),
    ("pfam", "json_array", "set_like", "pfam", "Pfam cross-reference identifiers."),
    (
        "reactome",
        "json_array",
        "set_like",
        "reactome",
        "Reactome pathway cross-reference identifiers.",
    ),
    (
        "pdb",
        "json_array",
        "set_like",
        "pdb",
        "PDB structure cross-reference identifiers.",
    ),
    (
        "chembl",
        "string",
        "scalar_or_set_like",
        "chembl",
        "ChEMBL identifiers used by non-ChEMBL provider references.",
    ),
    (
        "drugbank",
        "string",
        "set_like",
        "drugbank",
        "DrugBank identifiers used by UniProt cross-references.",
    ),
)


def build_reference_identifier_families(
    normalizers: Mapping[str, ReferenceNormalizer | None],
) -> tuple[ReferenceIdentifierFamily, ...]:
    """Build governed family metadata from stable normalizer keys."""
    return tuple(
        ReferenceIdentifierFamily(
            name=name,
            storage_representation=storage_representation,
            collection_semantics=collection_semantics,
            normalizer=normalizers.get(normalizer_key),
            description=description,
        )
        for (
            name,
            storage_representation,
            collection_semantics,
            normalizer_key,
            description,
        ) in _REFERENCE_IDENTIFIER_FAMILY_SPECS
    )
