"""Normalization profile for the ChEMBL Compound Record Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.compound_record import CompoundRecordSchema

__all__ = [
    "CHEMBL_COMPOUND_RECORD_PROFILE",
    "CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS",
]

CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS = tuple(
    CompoundRecordSchema.to_schema().columns.keys()
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
_TITLE_FIELDS = frozenset({"compound_name"})
_INT_FIELDS = frozenset({"record_id", "src_id"})

CHEMBL_COMPOUND_RECORD_PROFILE = build_standard_profile(
    profile_name="chembl.compound_record",
    description="Canonical field-level normalization policy for the ChEMBL Compound Record Silver schema.",
    schema_fields=CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    null_fields=chembl_pseudo_null_fields("compound_record"),
)

CHEMBL_COMPOUND_RECORD_PROFILE.assert_covers_schema(
    CHEMBL_COMPOUND_RECORD_SCHEMA_FIELDS
)
