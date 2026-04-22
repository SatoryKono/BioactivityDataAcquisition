"""Normalization profile for the ChEMBL Subcellular Fraction Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.schemas.chembl.subcellular_fraction import (
    SubcellularFractionSchema,
)

__all__ = [
    "CHEMBL_SUBCELLULAR_FRACTION_PROFILE",
    "CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS",
]

CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS = tuple(
    SubcellularFractionSchema.to_schema().columns.keys()
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
_TITLE_FIELDS = frozenset({"subcellular_fraction"})
_INT_FIELDS = frozenset({"assay_count"})

CHEMBL_SUBCELLULAR_FRACTION_PROFILE = build_standard_profile(
    profile_name="chembl.subcellular_fraction",
    description="Canonical field-level normalization policy for the ChEMBL Subcellular Fraction Silver schema.",
    schema_fields=CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    null_fields=chembl_pseudo_null_fields("subcellular_fraction"),
)

CHEMBL_SUBCELLULAR_FRACTION_PROFILE.assert_covers_schema(
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA_FIELDS
)
