"""Reference-oriented profile normalizers shared by schema profiles."""

from __future__ import annotations

from bioetl.domain.normalization.json import (
    deserialize_json_value,
    serialize_json_canonical,
)
from bioetl.domain.normalization.profiles._profile_publication_normalizers import (
    normalize_profile_publication_type,
    normalize_profile_publication_type_raw,
    normalize_profile_semantic_scholar_publication_type_raw,
)
from bioetl.domain.normalization.reference_ids import (
    normalize_chembl_reference_id,
    normalize_drugbank_reference_id,
    normalize_go_reference_id,
    normalize_interpro_reference_id,
    normalize_issn_reference_id,
    normalize_json_array_reference_ids,
    normalize_json_object_reference_id,
    normalize_json_string_reference_ids,
    normalize_mesh_reference_id,
    normalize_ncbi_taxonomy_reference_id,
    normalize_openalex_reference_id,
    normalize_orcid_reference_id,
    normalize_pdb_reference_id,
    normalize_pfam_reference_id,
    normalize_reactome_reference_id,
    normalize_ror_reference_id,
    normalize_semantic_scholar_reference_id,
    normalize_uniprot_accession_reference_id,
    normalize_uniprot_mixed_mapping_reference_id,
)
from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "normalize_profile_chembl_id",
    "normalize_profile_chembl_ids",
    "normalize_profile_drugbank_ids",
    "normalize_profile_issn_id",
    "normalize_profile_issn_ids",
    "normalize_profile_mesh_id",
    "normalize_profile_ncbi_taxonomy_id",
    "normalize_profile_openalex_author_ids",
    "normalize_profile_openalex_institution_ids",
    "normalize_profile_openalex_ror_ids",
    "normalize_profile_openalex_topic",
    "normalize_profile_openalex_topics",
    "normalize_profile_openalex_work_id",
    "normalize_profile_orcid_ids",
    "normalize_profile_pdb_references",
    "normalize_profile_pfam_references",
    "normalize_profile_publication_type",
    "normalize_profile_publication_type_raw",
    "normalize_profile_reactome_references",
    "normalize_profile_semantic_scholar_id",
    "normalize_profile_semantic_scholar_ids",
    "normalize_profile_semantic_scholar_publication_type_raw",
    "normalize_profile_uniprot_accession",
    "normalize_profile_uniprot_accessions",
    "normalize_profile_uniprot_accessions_ordered",
    "normalize_profile_uniprot_go_references",
    "normalize_profile_uniprot_interpro_references",
    "normalize_profile_uniprot_mixed_mappings",
]


def normalize_profile_uniprot_go_references(value: object) -> object:
    """Canonicalize UniProt GO reference arrays while preserving provider payloads."""
    return normalize_json_array_reference_ids(
        value,
        id_normalizer=normalize_go_reference_id,
    )


def normalize_profile_uniprot_interpro_references(value: object) -> object:
    """Canonicalize UniProt InterPro cross-reference arrays."""
    return normalize_json_array_reference_ids(
        value,
        id_normalizer=normalize_interpro_reference_id,
    )


def normalize_profile_pfam_references(value: object) -> object:
    """Canonicalize UniProt Pfam cross-reference arrays."""
    return normalize_json_array_reference_ids(
        value,
        id_normalizer=normalize_pfam_reference_id,
    )


def normalize_profile_reactome_references(value: object) -> object:
    """Canonicalize UniProt Reactome cross-reference arrays."""
    return normalize_json_array_reference_ids(
        value,
        id_normalizer=normalize_reactome_reference_id,
    )


def normalize_profile_pdb_references(value: object) -> object:
    """Canonicalize UniProt PDB cross-reference arrays."""
    return normalize_json_array_reference_ids(
        value,
        id_normalizer=normalize_pdb_reference_id,
    )


def normalize_profile_orcid_ids(value: object) -> object:
    """Canonicalize ORCID identifier JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=normalize_orcid_reference_id,
    )


def normalize_profile_issn_id(value: object) -> object:
    """Canonicalize one ISSN value."""
    return normalize_issn_reference_id(value)


def normalize_profile_issn_ids(value: object) -> object:
    """Canonicalize ISSN identifier JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=normalize_issn_reference_id,
    )


def normalize_profile_openalex_author_ids(value: object) -> object:
    """Canonicalize OpenAlex author identifier JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=lambda item: normalize_openalex_reference_id(
            item,
            prefix="A",
        ),
    )


def normalize_profile_openalex_institution_ids(value: object) -> object:
    """Canonicalize OpenAlex institution identifier JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=lambda item: normalize_openalex_reference_id(
            item,
            prefix="I",
        ),
    )


def normalize_profile_openalex_work_id(value: object) -> object:
    """Canonicalize one OpenAlex work identifier value."""
    return normalize_openalex_reference_id(value, prefix="W")


def normalize_profile_semantic_scholar_ids(value: object) -> object:
    """Canonicalize Semantic Scholar identifier JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=normalize_semantic_scholar_reference_id,
    )


def normalize_profile_semantic_scholar_id(value: object) -> object:
    """Canonicalize one Semantic Scholar identifier value."""
    return normalize_semantic_scholar_reference_id(value)


def normalize_profile_uniprot_accession(value: object) -> object:
    """Canonicalize one UniProt accession value."""
    return normalize_uniprot_accession_reference_id(value)


def normalize_profile_uniprot_accessions_ordered(value: object) -> object:
    """Canonicalize UniProt accession JSON arrays while preserving source order."""
    parsed = _deserialize_normalized_json_list(value)
    if parsed is None:
        return None if isinstance(value, str) else value
    return serialize_json_canonical(
        [normalize_uniprot_accession_reference_id(item) for item in parsed]
    )


def _deserialize_normalized_json_list(value: object) -> list[object] | None:
    """Return one normalized JSON list payload or None when unavailable."""
    if not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None
    try:
        parsed = deserialize_json_value(normalized)
    except ValueError:
        return None
    return parsed if isinstance(parsed, list) else None


def normalize_profile_uniprot_accessions(value: object) -> object:
    """Canonicalize UniProt accession JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=normalize_uniprot_accession_reference_id,
    )


def normalize_profile_uniprot_mixed_mappings(value: object) -> object:
    """Canonicalize mixed UniProt mapping arrays across governed ID families."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=normalize_uniprot_mixed_mapping_reference_id,
    )


def normalize_profile_chembl_id(value: object) -> object:
    """Canonicalize one ChEMBL identifier value."""
    return normalize_chembl_reference_id(value)


def normalize_profile_ncbi_taxonomy_id(value: object) -> object:
    """Canonicalize one NCBI Taxonomy identifier value."""
    return normalize_ncbi_taxonomy_reference_id(value)


def normalize_profile_mesh_id(value: object) -> object:
    """Canonicalize one MeSH descriptor identifier value."""
    return normalize_mesh_reference_id(value)


def normalize_profile_chembl_ids(value: object) -> object:
    """Canonicalize ChEMBL identifier JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=normalize_chembl_reference_id,
    )


def normalize_profile_drugbank_ids(value: object) -> object:
    """Canonicalize DrugBank identifier JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=normalize_drugbank_reference_id,
    )


def normalize_profile_openalex_ror_ids(value: object) -> object:
    """Canonicalize OpenAlex institution ROR ID JSON arrays."""
    return normalize_json_string_reference_ids(
        value,
        item_normalizer=normalize_ror_reference_id,
    )


def normalize_profile_openalex_topics(value: object) -> object:
    """Canonicalize OpenAlex topic JSON arrays by topic ID."""
    return normalize_json_array_reference_ids(
        value,
        id_normalizer=lambda item: normalize_openalex_reference_id(item, prefix="T"),
    )


def normalize_profile_openalex_topic(value: object) -> object:
    """Canonicalize one OpenAlex primary-topic JSON object by topic ID."""
    return normalize_json_object_reference_id(
        value,
        id_normalizer=lambda item: normalize_openalex_reference_id(item, prefix="T"),
    )
