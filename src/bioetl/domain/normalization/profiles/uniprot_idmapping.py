"""Normalization profile for the UniProt ID Mapping Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_chembl_id,
    normalize_profile_uniprot_accession,
    normalize_profile_uniprot_accessions,
)
from bioetl.domain.schemas.constants import UNIPROT_MAPPING_STATUSES
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema

__all__ = [
    "UNIPROT_IDMAPPING_PROFILE",
    "UNIPROT_IDMAPPING_SCHEMA_FIELDS",
]

UNIPROT_IDMAPPING_SCHEMA_FIELDS = tuple(IDMappingSchema.to_schema().columns.keys())

_META_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_dq_error",
        "_dq_warn",
    }
)
_TITLE_FIELDS = frozenset({"protein_name"})
_INT_FIELDS = frozenset(
    {"annotation_score", "sequence_length", "sequence_mass", "taxonomy_id"}
)
_JSON_STRING_FIELDS = frozenset({"all_mappings"})
_SET_LIKE_FIELDS = frozenset({"all_mappings"})
_BOOLEAN_FIELDS = frozenset({"reviewed"})
_ENUM_FIELDS = {"mapping_status": frozenset(UNIPROT_MAPPING_STATUSES)}
_SPECIAL_RULES = {
    "all_mappings": (
        normalize_profile_uniprot_accessions,
        "Canonicalize UniProt accession identifiers inside a set-like canonical JSON array.",
    ),
    "target_id": (
        normalize_profile_chembl_id,
        "Canonicalize ChEMBL target identifier through the shared ID registry.",
    ),
    "uniprot_accession": (
        normalize_profile_uniprot_accession,
        "Canonicalize UniProt accession identifier through the shared ID registry.",
    ),
}

UNIPROT_IDMAPPING_PROFILE = build_standard_profile(
    profile_name="uniprot.idmapping",
    description="Canonical field-level normalization policy for the UniProt ID Mapping Silver schema.",
    schema_fields=UNIPROT_IDMAPPING_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    set_like_fields=_SET_LIKE_FIELDS,
    json_string_fields=_JSON_STRING_FIELDS,
    boolean_fields=_BOOLEAN_FIELDS,
    enum_fields=_ENUM_FIELDS,
    special_rules=_SPECIAL_RULES,
)

UNIPROT_IDMAPPING_PROFILE.assert_covers_schema(UNIPROT_IDMAPPING_SCHEMA_FIELDS)
