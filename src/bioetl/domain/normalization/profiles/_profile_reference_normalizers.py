"""Reference-oriented profile normalizers shared by schema profiles."""

from __future__ import annotations

from bioetl.domain.mapping.publication_type_mapping import normalize_publication_type
from bioetl.domain.normalization.reference_ids import (
    normalize_go_reference_id,
    normalize_interpro_reference_id,
    normalize_json_array_reference_ids,
    normalize_json_object_reference_id,
    normalize_json_string_reference_ids,
    normalize_openalex_reference_id,
    normalize_pdb_reference_id,
    normalize_pfam_reference_id,
    normalize_reactome_reference_id,
    normalize_ror_reference_id,
)
from bioetl.domain.normalization.text import normalize_string

__all__ = [
    "normalize_profile_openalex_ror_ids",
    "normalize_profile_openalex_topic",
    "normalize_profile_openalex_topics",
    "normalize_profile_pdb_references",
    "normalize_profile_pfam_references",
    "normalize_profile_publication_type",
    "normalize_profile_publication_type_raw",
    "normalize_profile_reactome_references",
    "normalize_profile_uniprot_go_references",
    "normalize_profile_uniprot_interpro_references",
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


def normalize_profile_publication_type(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> object:
    """Normalize publication type through the canonical mapping and enum gate."""
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    if cleaned is None:
        return None
    normalized = normalize_publication_type(cleaned)
    if normalized is None:
        return None
    return normalized if normalized in allowed_values else None


def normalize_profile_publication_type_raw(value: object) -> object:
    """Normalize raw provider publication-type tokens without mapping to canonical taxonomy."""
    if not isinstance(value, str):
        return None
    cleaned = normalize_string(value)
    return cleaned.upper() if cleaned is not None else None
