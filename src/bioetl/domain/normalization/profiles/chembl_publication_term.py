"""Normalization profile for the ChEMBL Publication Term Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.schemas.chembl.publication_term import PublicationTermSchema

__all__ = [
    "CHEMBL_PUBLICATION_TERM_PROFILE",
    "CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS",
]

CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS = tuple(
    PublicationTermSchema.to_schema().columns.keys()
)

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
_TITLE_FIELDS = frozenset({"term"})
_ENUM_FIELDS = {
    "term_type": frozenset({"MESH_HEADING", "MESH_QUALIFIER", "KEYWORD", "CONCEPT"}),
}
_NULL_FIELDS = frozenset({"mesh_id", "qualifier"})

CHEMBL_PUBLICATION_TERM_PROFILE = build_standard_profile(
    profile_name="chembl.publication_term",
    description="Canonical field-level normalization policy for the ChEMBL Publication Term Silver schema.",
    schema_fields=CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    enum_fields=_ENUM_FIELDS,
    null_fields=_NULL_FIELDS,
)

CHEMBL_PUBLICATION_TERM_PROFILE.assert_covers_schema(
    CHEMBL_PUBLICATION_TERM_SCHEMA_FIELDS
)
