"""Normalization profile for the ChEMBL Cell Line Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.chembl import (
    CLO_ONTOLOGY_VERSION,
    EFO_ONTOLOGY_VERSION,
)
from bioetl.domain.normalization.profiles._profile_ontology_companion_normalizers import (
    build_obo_companion_iri_normalizer,
    build_obo_companion_mapping_status_normalizer,
    build_obo_companion_version_normalizer,
)
from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.domain.normalization.profiles.chembl_pseudo_nulls import (
    chembl_pseudo_null_fields,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_cellosaurus_id,
)
from bioetl.domain.schemas.chembl.cell_line import CellLineSchema
from bioetl.domain.schemas.constants import ONTOLOGY_MAPPING_STATUSES

from .chembl_policy_registry import chembl_ontology_family_fields
from ._chembl_reference_identifier_rules import chembl_reference_identifier_rules

__all__ = [
    "CHEMBL_CELL_LINE_PROFILE",
    "CHEMBL_CELL_LINE_SCHEMA_FIELDS",
]

CHEMBL_CELL_LINE_SCHEMA_FIELDS = tuple(CellLineSchema.to_schema().columns.keys())

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
_TITLE_FIELDS = frozenset({"cell_name", "cell_source_tissue"})
_INT_FIELDS = frozenset({"cell_source_taxonomy_id"})
_ONTOLOGY_ID_FIELDS = chembl_ontology_family_fields(
    "clo", entity="cell_line"
) | chembl_ontology_family_fields("efo", entity="cell_line")
_ENUM_FIELDS = {
    "clo_mapping_status": ONTOLOGY_MAPPING_STATUSES,
    "efo_mapping_status": ONTOLOGY_MAPPING_STATUSES,
}
_OBO_COMPANION_SPECS = {
    "clo": ("clo_id", "CLO_", CLO_ONTOLOGY_VERSION),
    "efo": ("efo_id", "EFO_", EFO_ONTOLOGY_VERSION),
}
_REFERENCE_IDENTIFIER_RULES = chembl_reference_identifier_rules("cell_line")
_SPECIAL_RULES = {
    **_REFERENCE_IDENTIFIER_RULES,
    "cellosaurus_id": (
        normalize_profile_cellosaurus_id,
        "Normalize Cellosaurus identifiers to canonical CVCL-prefixed form.",
    ),
    **{
        f"{family}_iri": (
            build_obo_companion_iri_normalizer(
                source_field=source_field,
                canonical_prefix=canonical_prefix,
                ontology_version=ontology_version,
            ),
            f"Resolve the {family.upper()} ontology companion bundle from sibling "
            "normalized identifiers and emit the canonical OBO IRI.",
        )
        for family, (
            source_field,
            canonical_prefix,
            ontology_version,
        ) in _OBO_COMPANION_SPECS.items()
    },
    **{
        f"{family}_mapping_status": (
            build_obo_companion_mapping_status_normalizer(
                source_field=source_field,
                canonical_prefix=canonical_prefix,
                ontology_version=ontology_version,
            ),
            f"Resolve the {family.upper()} ontology companion bundle from sibling "
            "normalized identifiers and emit the canonical mapping-status enum.",
        )
        for family, (
            source_field,
            canonical_prefix,
            ontology_version,
        ) in _OBO_COMPANION_SPECS.items()
    },
    **{
        f"{family}_ontology_version": (
            build_obo_companion_version_normalizer(
                source_field=source_field,
                canonical_prefix=canonical_prefix,
                ontology_version=ontology_version,
            ),
            f"Resolve the {family.upper()} ontology companion bundle from sibling "
            "normalized identifiers and emit the ontology version when a mapping "
            "context exists.",
        )
        for family, (
            source_field,
            canonical_prefix,
            ontology_version,
        ) in _OBO_COMPANION_SPECS.items()
    },
}

CHEMBL_CELL_LINE_PROFILE = build_standard_profile(
    profile_name="chembl.cell_line",
    description="Canonical field-level normalization policy for the ChEMBL Cell Line Silver schema.",
    schema_fields=CHEMBL_CELL_LINE_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    int_fields=_INT_FIELDS,
    ontology_id_fields=_ONTOLOGY_ID_FIELDS,
    enum_fields=_ENUM_FIELDS,
    special_rules=_SPECIAL_RULES,
    null_fields=chembl_pseudo_null_fields("cell_line"),
)

CHEMBL_CELL_LINE_PROFILE.assert_covers_schema(CHEMBL_CELL_LINE_SCHEMA_FIELDS)
