"""Normalization profile for the UniProt ID Mapping Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.infrastructure.schemas.silver_compounds import UNIPROT_ID_MAPPING_SCHEMA

__all__ = [
    "UNIPROT_IDMAPPING_PROFILE",
    "UNIPROT_IDMAPPING_SCHEMA_FIELDS",
]

UNIPROT_IDMAPPING_SCHEMA_FIELDS = tuple(UNIPROT_ID_MAPPING_SCHEMA.names)

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
_INT_FIELDS = frozenset({"annotation_score", "sequence_length", "sequence_mass", "taxonomy_id"})

UNIPROT_IDMAPPING_PROFILE = build_standard_profile(
    profile_name="uniprot.idmapping",
    description="Canonical field-level normalization policy for the UniProt ID Mapping Silver schema.",
    schema_fields=UNIPROT_IDMAPPING_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
)

UNIPROT_IDMAPPING_PROFILE.assert_covers_schema(UNIPROT_IDMAPPING_SCHEMA_FIELDS)
