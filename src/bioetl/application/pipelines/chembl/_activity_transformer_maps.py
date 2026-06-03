"""Shared mapping constants for ``activity_transformer``."""

from __future__ import annotations

from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    float_fields,
    int_fields,
    simple_fields,
)
from bioetl.domain.transformations import safe_float
from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.taxonomy_id import validate_taxonomy_id

_LIGAND_EFFICIENCY_FIELDS: JsonDict = {
    "bei": safe_float,
    "le": safe_float,
    "lle": safe_float,
    "sei": safe_float,
}

_ACTION_TYPE_FIELDS: JsonDict = {
    "action_type": None,
    "description": None,
    "parent_type": None,
}

_ONTOLOGY_COMPANION_DEFAULTS: JsonDict = {
    "bao_endpoint_iri": None,
    "bao_endpoint_mapping_status": None,
    "bao_format_iri": None,
    "bao_format_mapping_status": None,
    "bao_ontology_version": None,
    "uo_unit_iri": None,
    "uo_unit_mapping_status": None,
    "uo_ontology_version": None,
    "qudt_unit_iri": None,
    "qudt_unit_mapping_status": None,
    "qudt_ontology_version": None,
}

_IDENTIFIERS = FieldGroup(
    name="identifiers",
    fields=(
        FieldSpec("target_chembl_id", target="target_id"),
        FieldSpec("assay_chembl_id", target="assay_id"),
        FieldSpec("document_chembl_id", target="publication_id"),
        *int_fields("record_id", "src_id"),
    ),
)

_MOLECULE_TARGET_ASSAY = FieldGroup(
    name="molecule_target_assay",
    fields=(
        *simple_fields(
            "canonical_smiles",
            "molecule_pref_name",
            "target_pref_name",
            "target_organism",
        ),
        FieldSpec("parent_molecule_chembl_id", target="parent_molecule_id"),
        FieldSpec(
            "target_tax_id",
            target="target_taxonomy_id",
            converter=validate_taxonomy_id,
        ),
        *simple_fields(
            "assay_type",
            "assay_description",
            "assay_variant_accession",
            "assay_variant_mutation",
            "bao_endpoint",
            "bao_format",
            "bao_label",
        ),
    ),
)

_RAW_VALUES = FieldGroup(
    name="raw_values",
    fields=(
        FieldSpec("type", target="activity_type"),
        FieldSpec("relation", target="activity_relation"),
        FieldSpec("value", target="activity_value", converter=safe_float),
        *simple_fields("units", "text_value"),
        *float_fields("upper_value"),
    ),
)

_STANDARD_VALUES = FieldGroup(
    name="standard_values",
    fields=(
        *simple_fields(
            "standard_type",
            "standard_units",
            "standard_relation",
            "standard_text_value",
        ),
        *float_fields("standard_value", "standard_upper_value", "pchembl_value"),
        *int_fields("standard_flag"),
    ),
)

_UNIT_FIELDS = FieldGroup(
    name="units",
    fields=simple_fields("qudt_units", "uo_units"),
)

_QUALITY_ANNOTATIONS = FieldGroup(
    name="quality_annotations",
    fields=(
        FieldSpec("document_journal", target="journal"),
        *simple_fields(
            "activity_comment",
            "data_validity_comment",
            "data_validity_description",
        ),
        FieldSpec("document_year", target="publication_year"),
        *int_fields(
            "potential_duplicate",
            "toid",
            "manual_curation_flag",
            "original_activity_id",
        ),
    ),
)

_ACTIVITY_GROUPS: tuple[FieldGroup, ...] = (
    _IDENTIFIERS,
    _MOLECULE_TARGET_ASSAY,
    _RAW_VALUES,
    _STANDARD_VALUES,
    _UNIT_FIELDS,
    _QUALITY_ANNOTATIONS,
)

__all__ = [
    "_ACTION_TYPE_FIELDS",
    "_ACTIVITY_GROUPS",
    "_LIGAND_EFFICIENCY_FIELDS",
    "_ONTOLOGY_COMPANION_DEFAULTS",
]
