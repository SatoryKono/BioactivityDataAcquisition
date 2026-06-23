#!/usr/bin/env python3
"""Normalize controlled vocabulary values in ChEMBL matrix workbooks."""

from __future__ import annotations

import argparse
import copy
import sys
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from xml.etree import ElementTree as ET

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import PROJECT_ROOT, ensure_repo_imports
else:
    from scripts.docs.matrix._bootstrap import PROJECT_ROOT, ensure_repo_imports

ensure_repo_imports()

from scripts.docs.common.xlsx import (  # noqa: E402
    MAIN_NS,
    NS,
    cell_text,
    column_index,
    load_shared_strings,
    set_cell_text,
    sheet_target_paths,
)

DEFAULT_INPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
DEFAULT_OUTPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
DEFAULT_MAPPING_OUTPUT: Final[Path] = (
    PROJECT_ROOT
    / "docs/reports/dictionaries/chembl_pipeline_silver_matrices_v12_canonical_mappings.yaml"
)
SILVER_FILTERS_LABEL: Final[str] = "Silver Filters"
FILTER_FAIL_SINK_LABEL: Final[str] = "Filter fail sink"
SILVER_NORMALISATION_LABEL: Final[str] = "Silver Normalisation"
SILVER_VALIDATION_LABEL: Final[str] = "Silver Validation"
VALIDATION_FAIL_ACTION_LABEL: Final[str] = "Validation fail action"
JSON_OBJECT_TYPE: Final[str] = "json/object"
JSON_ARRAY_TYPE: Final[str] = "json/array"
ENUM_NOT_NULL: Final[str] = "enum_constraint; not_null"
REQUIRED_RANGE: Final[str] = "required; range_constraint"
RUNTIME_DQ_MARKER: Final[str] = "runtime_contract; dq_marker"
PANDERA_PATTERN: Final[str] = "pandera:pattern"
RUNTIME_LINEAGE_METADATA: Final[str] = "runtime_contract; lineage_metadata"
CROSS_FIELD_PREFIX: Final[str] = "cross_field:"
KEY_NOT_NULL_PREFIX: Final[str] = "key_not_null:"
CANONICALIZED_SEMICOLON_HEADERS: Final[frozenset[str]] = frozenset(
    {
        SILVER_FILTERS_LABEL,
        SILVER_VALIDATION_LABEL,
        "Source_Field_Validation",
        SILVER_NORMALISATION_LABEL,
        "Source_Field_Normalisation",
        VALIDATION_FAIL_ACTION_LABEL,
    }
)
TARGET_COLUMNS: Final[tuple[str, ...]] = (
    "Source_Field_Type",
    "Type",
    "Source_Field_Nullable",
    "Nullable",
    "Required",
    SILVER_FILTERS_LABEL,
    FILTER_FAIL_SINK_LABEL,
    SILVER_NORMALISATION_LABEL,
    "Source_Field_Normalisation",
    SILVER_VALIDATION_LABEL,
    "Source_Field_Validation",
    VALIDATION_FAIL_ACTION_LABEL,
)
TYPE_MAP: Final[dict[str, str]] = {
    "string": "string",
    "text": "string",
    "integer": "integer",
    "int": "integer",
    "int64": "integer",
    "float": "float",
    "float64": "float",
    "double": "float",
    "boolean": "boolean",
    "bool": "boolean",
    "date": "date",
    "datetime": "datetime",
    "timestamp": "datetime",
    JSON_OBJECT_TYPE: JSON_OBJECT_TYPE,
    "object": JSON_OBJECT_TYPE,
    JSON_ARRAY_TYPE: JSON_ARRAY_TYPE,
    "array": JSON_ARRAY_TYPE,
    "derived": "derived",
    "runtime": "runtime",
    "not_mapped": "not_mapped",
    "unknown": "unknown",
    "unknown / config-only": "unknown",
}
NULLABLE_MAP: Final[dict[str, str]] = {
    "false": "false",
    "true": "true",
    "conditional": "conditional",
    "derived": "derived",
    "runtime-managed": "runtime-managed",
    "runtime_managed": "runtime-managed",
    "not_mapped": "not_mapped",
    "unknown": "unknown",
}
FILTER_FAIL_SINK_MAP: Final[dict[str, str]] = {
    "-": "not_applicable",
    "No dedicated reject table found; record skipped before Silver write": (
        "quarantine"
    ),
    "dropped_before_silver_write": "quarantine",
    "Excluded upstream by ChEMBL extraction parameters": "excluded_upstream",
}
SILVER_NORMALISATION_MAP: Final[dict[str, str]] = {
    "Passthrough / transformer-specific mapping not auto-traced in this sheet": (
        "passthrough"
    ),
    "Boolean flag": "boolean_flag",
    "Passthrough": "passthrough",
    "Enum/value normalized to string": "string_normalized",
    "Normalized to string": "string_normalized",
    "Runtime counter": "runtime_counter",
    "compute_content_hash()": "content_hash_generated",
    "compute_entity_id()": "entity_id_generated",
    "datetime -> ISO 8601 string": "datetime_to_iso8601",
    "Optional lineage normalization": "lineage_optional_normalized",
    "float_fields coercion": "float_coerced",
    "Nested flatten + safe_float": "nested_flattened; float_coerced",
    "Runtime-managed field": "runtime_managed",
    "int_fields coercion": "integer_coerced",
    "Declared in config/contract, but not populated by current transformer": (
        "not_populated"
    ),
    "Nullable integer carried as float64": "nullable_integer_as_float",
    "Nested flatten": "nested_flattened",
    "Fallback from two Bronze fields, then str()": "fallback_identifier_to_string",
    "JSON serialization": "json_serialized",
    "Nested flatten + rename": "nested_flattened; renamed",
    "PrimaryId converted to str": "identifier_to_string",
    "Rename assay_chembl_id -> assay_id": "renamed",
    "Rename document_chembl_id -> publication_id": "renamed",
    "Rename document_journal -> journal": "renamed",
    "Rename document_year -> publication_year; int coercion": "renamed; integer_coerced",
    "Rename parent_molecule_chembl_id -> parent_molecule_id": "renamed",
    "Rename target_chembl_id -> target_id": "renamed",
    "Runtime lineage injection before Silver write": "runtime_lineage_injected",
    "Runtime state annotation propagated into committed Silver schema": (
        "runtime_state_propagated"
    ),
    "validate_taxonomy_id + rename to target_taxonomy_id": (
        "taxonomy_id_validated; renamed"
    ),
}
SOURCE_FIELD_NORMALISATION_MAP: Final[dict[str, str]] = {
    "trim; blank_to_null": "trim; blank_to_null",
    "runtime_managed": "runtime-managed",
    "derived_from_transformer": "derived_from_transformer",
    "numeric_only; blank_to_null": "numeric_only; blank_to_null",
    "not_mapped": "not_mapped",
    "trim; blank_to_null; controlled_vocabulary": (
        "trim; blank_to_null; controlled_vocabulary"
    ),
    "trim; identifier_normalized": "trim; identifier_normalized",
    "derive_from_nested; trim; blank_to_null": (
        "derived_from_nested; trim; blank_to_null"
    ),
    "numeric_only": "numeric_only",
    "trim; blank_to_null; value_xor_text_value": (
        "trim; blank_to_null; value_xor_text_value"
    ),
    "derive_from_nested; trim; blank_to_null; identifier_normalized": (
        "derived_from_nested; trim; blank_to_null; identifier_normalized"
    ),
    "derive_from_nested; trim; controlled_vocabulary": (
        "derived_from_nested; trim; controlled_vocabulary"
    ),
    "numeric_only; value_xor_text_value; relation_required_if_value": (
        "numeric_only; value_xor_text_value; relation_required_if_value"
    ),
    "trim; blank_to_null; identifier_normalized": (
        "trim; blank_to_null; identifier_normalized"
    ),
    "trim; controlled_vocabulary": "trim; controlled_vocabulary",
}
SILVER_FILTERS_MAP: Final[dict[str, str]] = {
    "-": "none",
    "required; not null": "required; not_null",
    "required": "required",
    "IN {0}": "enum_constraint",
    "IN {0}; not null": ENUM_NOT_NULL,
    "IN {1}": "enum_constraint",
    "IN {=}; not null": ENUM_NOT_NULL,
    "IN {B, F}; not null": ENUM_NOT_NULL,
    "IN {B, F}; required": "enum_constraint; required",
    "IN {D}": "enum_constraint",
    "IN {IC50, Ki}; not null": ENUM_NOT_NULL,
    "IN {MOL}": "enum_constraint",
    "IN {SINGLE PROTEIN}": "enum_constraint",
    "IN {Small molecule}": "enum_constraint",
    "IN {journal-article}; required": "enum_constraint; required",
    "IN {nM}; not null": ENUM_NOT_NULL,
    "exclude_if_present": "exclude_if_present",
    "range >= 1950 and <= 2050": "range_constraint",
    "range >= 8 and <= 9": "range_constraint",
    "required; extraction-side fixed value = 1": "required; fixed_value=1",
    "required; range 1950..2050": REQUIRED_RANGE,
    "required; range 3..10": REQUIRED_RANGE,
    "required; range > 0": REQUIRED_RANGE,
    "required; range >=1": REQUIRED_RANGE,
}
SILVER_VALIDATION_MAP: Final[dict[str, str]] = {
    "-": "none",
    "runtime-managed field": "runtime_contract",
    "DQ marker field": RUNTIME_DQ_MARKER,
    "Internal identity/hash generation": "runtime_contract; generated_internal_field",
    "Pandera non-null string field": "pandera:string; not_null",
    "pattern": PANDERA_PATTERN,
    "Lineage metadata": RUNTIME_LINEAGE_METADATA,
    "No runtime validation because current ActivityTransformer does not populate this field": (
        "not_populated_by_transformer"
    ),
    "pattern; non-null": "pandera:pattern; not_null",
    "Pandera 0 or 1; non-null": "pandera:enum:{0,1}; not_null",
    "Pandera CHEMBL_ID_PATTERN; non-null": (
        "pandera:pattern:CHEMBL_ID_PATTERN; not_null"
    ),
    "Pandera non-null integer field": "pandera:integer; not_null",
    "cross-field: structure_completeness": f"{CROSS_FIELD_PREFIX}structure_completeness",
    "key_nullability: partition not nullable": f"{KEY_NOT_NULL_PREFIX}partition",
    "pattern; cross-field: record_linkage": f"{PANDERA_PATTERN}; {CROSS_FIELD_PREFIX}record_linkage",
    "pattern; cross-field: term_completeness": (
        f"{PANDERA_PATTERN}; {CROSS_FIELD_PREFIX}term_completeness"
    ),
    "pattern; key_nullability: merge not nullable": f"{PANDERA_PATTERN}; {KEY_NOT_NULL_PREFIX}merge",
    "range; min=0, max=-": "pandera:range:min=0",
    "range; min=0, max=1": "pandera:range:min=0,max=1",
    "range; min=1, max=-; cross-field: similarity_pair": (
        f"pandera:range:min=1; {CROSS_FIELD_PREFIX}similarity_pair"
    ),
    "range; min=1, max=-; key_nullability: merge not nullable": f"pandera:range:min=1; {KEY_NOT_NULL_PREFIX}merge",
    "CHEMBL_ID_PATTERN; non-null": "pandera:pattern:CHEMBL_ID_PATTERN; not_null",
    "Internal content-hash generation": "runtime_contract; content_hash_generated",
    "Internal identity generation": "runtime_contract; identity_generated",
    "Pandera 0 or 1": "pandera:enum:{0,1}",
    "Pandera ACTIVITY_STANDARD_TYPES; non-null": (
        "pandera:enum:ACTIVITY_STANDARD_TYPES; not_null"
    ),
    "Pandera BAO_ID_PATTERN; non-null": "pandera:pattern:BAO_ID_PATTERN; not_null",
    "Pandera CHEMBL_ID_PATTERN": "pandera:pattern:CHEMBL_ID_PATTERN",
    "Pandera STANDARD_RELATIONS enum; non-null": (
        "pandera:enum:STANDARD_RELATIONS; not_null"
    ),
    "Pandera UO_ID_PATTERN; non-null": "pandera:pattern:UO_ID_PATTERN; not_null",
    "Pandera enum {raw, normalized, validated}; non-null": (
        "pandera:enum:{raw,normalized,validated}; not_null"
    ),
    "Pandera non-null numeric field": "pandera:numeric; not_null",
    "Pandera non-null string field; quality conditional uses assay_type == B": (
        "pandera:string; not_null; quality:assay_type=B"
    ),
    "Pandera non-null taxonomy field": "pandera:taxonomy; not_null",
    "Pandera publication year bounds; non-null": (
        "pandera:publication_year_bounds; not_null"
    ),
    "Write-time lineage metadata required; non-null and non-blank": (
        "runtime_contract; write_time_lineage_required; not_null; non_blank"
    ),
    "cross-field: assay_identifiable; non-null": (
        "cross_field:assay_identifiable; not_null"
    ),
    "cross-field: target_identifiable; non-null": (
        "cross_field:target_identifiable; not_null"
    ),
    "custom; cross-field: structure_completeness": (
        "custom; cross_field:structure_completeness"
    ),
    "enum; allowed=B,F,A,T,P,U; non-null": ("pandera:enum:{B,F,A,T,P,U}; not_null"),
    "enum; allowed=D,H,M,N,S,U": "pandera:enum:{D,H,M,N,S,U}",
    (
        "enum; allowed=MESH_HEADING,KEYWORD,AUTHOR,INSTITUTION; "
        "cross-field: term_completeness; "
        "key_nullability: partition not nullable"
    ): (
        "pandera:enum:{MESH_HEADING,KEYWORD,AUTHOR,INSTITUTION}; cross_field:term_completeness; key_not_null:partition"
    ),
    "enum; allowed=MOL,SEQ,NONE,BOTH": "pandera:enum:{MOL,SEQ,NONE,BOTH}",
    "enum; allowed=PROTEIN,DNA,RNA": "pandera:enum:{PROTEIN,DNA,RNA}",
    (
        "enum; allowed=SINGLE PROTEIN,PROTEIN COMPLEX,PROTEIN FAMILY,"
        "SELECTIVITY GROUP,ORGANISM,TISSUE,CELL-LINE,SUBCELLULAR,UNKNOWN,"
        "CHIMERIC PROTEIN,PROTEIN-PROTEIN INTERACTION,NUCLEIC-ACID,METAL,"
        "LIPID,MACROMOLECULE,PHENOTYPE,ADMET; "
        "key_nullability: partition not nullable"
    ): (
        "pandera:enum:{SINGLE PROTEIN,PROTEIN COMPLEX,PROTEIN FAMILY,"
        "SELECTIVITY GROUP,ORGANISM,TISSUE,CELL-LINE,SUBCELLULAR,UNKNOWN,"
        "CHIMERIC PROTEIN,PROTEIN-PROTEIN INTERACTION,NUCLEIC-ACID,METAL,"
        "LIPID,MACROMOLECULE,PHENOTYPE,ADMET}; key_not_null:partition"
    ),
    (
        "enum; allowed=Small molecule,Protein,Antibody,Oligosaccharide,"
        "Oligonucleotide,Cell,Enzyme,Unknown; "
        "key_nullability: partition not nullable"
    ): (
        "pandera:enum:{Small molecule,Protein,Antibody,Oligosaccharide,"
        "Oligonucleotide,Cell,Enzyme,Unknown}; key_not_null:partition"
    ),
    "enum; allowed=journal-article,book,dataset,patent; non-null": (
        "pandera:enum:{journal-article,book,dataset,patent}; not_null"
    ),
    "key_nullability: merge not nullable": "key_not_null:merge",
    "not_null; max_length; pattern; cross-field: publication_identifiable": (
        "pandera:pattern; not_null; max_length; cross_field:publication_identifiable"
    ),
    "pattern; cross-field: component_identifiable": (
        "pandera:pattern; cross_field:component_identifiable"
    ),
    "pattern; cross-field: has_cross_reference": (
        "pandera:pattern; cross_field:has_cross_reference"
    ),
    "pattern; cross-field: param_linkage": "pandera:pattern; cross_field:param_linkage",
    "pattern; cross-field: publication_identifiable; key_nullability: merge not nullable": (
        "pandera:pattern; cross_field:publication_identifiable; key_not_null:merge"
    ),
    "pattern; key_nullability: partition not nullable": (
        "pandera:pattern; key_not_null:partition"
    ),
    "quality 0..15; Pandera 0..14; non-null": (
        "quality:0..15; pandera:range:min=0,max=14; not_null"
    ),
    "quality 0..1e9; IC50 conditional 0.001..100000; Pandera >= 0; non-null": (
        "quality:0..1e9; quality:IC50=0.001..100000; pandera:range:min=0; not_null"
    ),
    "quality enum; Pandera DATA_VALIDITY_COMMENTS enum": (
        "quality:enum; pandera:enum:DATA_VALIDITY_COMMENTS"
    ),
    "quality enum; required when standard_value present; non-null": (
        "quality:enum; quality:required_if=standard_value; not_null"
    ),
    "quality: required when assay_type == B; non-null": (
        "quality:required_if=assay_type=B; not_null"
    ),
    "quality: required; Pandera non-null": "quality:required; pandera:not_null",
    "range; min=0, max=-; range; min=0, max=10000000": (
        "pandera:range:min=0; pandera:range:min=0,max=10000000"
    ),
    "range; min=0, max=9": "pandera:range:min=0,max=9",
    "range; min=1, max=-": "pandera:range:min=1",
    "range; min=1, max=-; cross-field: component_identifiable; key_nullability: merge not nullable": (
        "pandera:range:min=1; cross_field:component_identifiable; key_not_null:merge"
    ),
    "range; min=1, max=-; cross-field: param_linkage; key_nullability: merge not nullable": (
        "pandera:range:min=1; cross_field:param_linkage; key_not_null:merge"
    ),
    "range; min=1, max=10000000": "pandera:range:min=1,max=10000000",
    "range; min=1, max=10000000000; cross-field: has_cross_reference": (
        "pandera:range:min=1,max=10000000000; cross_field:has_cross_reference"
    ),
    "range; min=1500, max=2100; range; min=1950, max=-": (
        "pandera:range:min=1500,max=2100; pandera:range:min=1950"
    ),
    "required; cross-field: assay_identifiable; key_nullability: merge not nullable": (
        "required; cross_field:assay_identifiable; key_not_null:merge"
    ),
    "required; cross-field: target_identifiable; key_nullability: merge not nullable": (
        "required; cross_field:target_identifiable; key_not_null:merge"
    ),
    "required; key_nullability: merge not nullable": "required; key_not_null:merge",
}
SOURCE_FIELD_VALIDATION_MAP: Final[dict[str, str]] = {
    "Provider nested/resource field; validate via upstream payload contract": (
        "provider_payload_contract"
    ),
    "Runtime-managed field; no provider-side validation": "runtime-managed",
    "Derived field; validated via upstream source fields": "derived_from_upstream",
    "No direct provider field in current pipeline mapping": "not_mapped",
    "Assay type should align with ChEMBL assay-type controlled vocabulary": (
        "provider_controlled_vocabulary"
    ),
    "Derived discriminator for keyword vs MeSH term origin": "derived_from_nested",
    "Derived from nested MeSH qualifier payload": "derived_from_nested",
    "Derived from nested document MeSH term payload": "derived_from_nested",
    "Derived from nested keyword or MeSH term text": "derived_from_nested",
    "Mandatory assay identifier in assay-parameter payload": (
        "mandatory_provider_identifier"
    ),
    "Mandatory similarity-record identifier": "mandatory_provider_identifier",
    "Mandatory upstream assay identifier for derived aggregation": (
        "mandatory_upstream_identifier"
    ),
    "Mandatory upstream publication/document identifier": (
        "mandatory_upstream_identifier"
    ),
    "Numeric VALUE when present; mutually exclusive with TEXT_VALUE": (
        "numeric_if_present; value_xor_text_value"
    ),
    "Optional assay organism string carried from upstream assay payload": (
        "optional_provider_field"
    ),
    "Optional assay subcellular-fraction text in upstream assay payload": (
        "optional_provider_field"
    ),
    "Optional assay-parameter identifier": "optional_provider_field",
    "Optional assay-parameter type": "optional_provider_field",
    "Optional assay-parameter units": "optional_provider_field",
    "Optional first PubMed identifier": "optional_provider_field",
    "Optional first document identifier in similarity record": (
        "optional_provider_field"
    ),
    "Optional free-text parameter comment": "optional_provider_field",
    "Optional molecule-based Tanimoto similarity score": "optional_provider_field",
    "Optional second PubMed identifier": "optional_provider_field",
    "Optional second document identifier in similarity record": (
        "optional_provider_field"
    ),
    "Optional standardized RELATION operator": "optional_provider_field",
    "Optional standardized assay-parameter type": "optional_provider_field",
    "Optional standardized numeric value": "optional_provider_field",
    "Optional standardized units": "optional_provider_field",
    "Optional target-based Tanimoto similarity score": "optional_provider_field",
    "Optional upstream target identifier carried from assay payload": (
        "optional_provider_field"
    ),
    "RELATION required when VALUE is present in assay-parameter payload": (
        "relation_required_if_value"
    ),
    "Use text field for non-numeric assay-parameter values": "text_value_for_non_numeric",
    "Use text field when no numeric standardized value is available": (
        "text_value_for_non_numeric_standardized"
    ),
}
VALIDATION_FAIL_ACTION_MAP: Final[dict[str, str]] = {
    "Record skipped before Silver write or late schema/write-stage failure": (
        "skip_record_or_schema_failure"
    ),
    "Batch/runtime failure only": "runtime_failure",
    "-": "not_applicable",
    "Currently remains empty unless transformer mapping is extended": "not_mapped",
    "Downstream DQ handling": "downstream_dq_handling",
    "TransformationError or record skipped before Silver write": (
        "transform_failure_or_skip_record"
    ),
    "Late schema/write-stage failure if invalid": "schema_validation_error",
    "Late write-time validation failure if missing, null, or blank": (
        "write_time_validation_error"
    ),
    "Record skipped before Silver write": "skip_record",
    "Transform failure if generation breaks": "transform_failure",
    "Transform failure if hash generation breaks": "transform_failure",
}
CANONICAL_HEADER_MAPS: Final[dict[str, dict[str, str]]] = {
    FILTER_FAIL_SINK_LABEL: FILTER_FAIL_SINK_MAP,
    SILVER_NORMALISATION_LABEL: SILVER_NORMALISATION_MAP,
    "Source_Field_Normalisation": SOURCE_FIELD_NORMALISATION_MAP,
    SILVER_FILTERS_LABEL: SILVER_FILTERS_MAP,
    "Source_Field_Validation": SOURCE_FIELD_VALIDATION_MAP,
    VALIDATION_FAIL_ACTION_LABEL: VALIDATION_FAIL_ACTION_MAP,
}
MAPPING_PAYLOAD_COLUMNS: Final[dict[str, dict[str, str]]] = {
    "Source_Field_Type": TYPE_MAP,
    "Type": TYPE_MAP,
    "Source_Field_Nullable": NULLABLE_MAP,
    "Nullable": NULLABLE_MAP,
    FILTER_FAIL_SINK_LABEL: FILTER_FAIL_SINK_MAP,
    SILVER_NORMALISATION_LABEL: SILVER_NORMALISATION_MAP,
    "Source_Field_Normalisation": SOURCE_FIELD_NORMALISATION_MAP,
    SILVER_FILTERS_LABEL: SILVER_FILTERS_MAP,
    SILVER_VALIDATION_LABEL: SILVER_VALIDATION_MAP,
    "Source_Field_Validation": SOURCE_FIELD_VALIDATION_MAP,
    VALIDATION_FAIL_ACTION_LABEL: VALIDATION_FAIL_ACTION_MAP,
}


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize controlled vocabulary values in ChEMBL matrix workbooks."
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT, help="Input workbook."
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="Output workbook."
    )
    parser.add_argument(
        "--mapping-output",
        type=Path,
        default=DEFAULT_MAPPING_OUTPUT,
        help="YAML file for applied canonical mappings.",
    )
    return parser


def _normalize_required(value: str) -> str:
    lowered = " ".join(value.strip().split()).lower()
    if not lowered:
        return "optional"
    if lowered == "optional":
        return "optional"
    parts = [part.strip() for part in lowered.split(",") if part.strip()]
    ordered = [label for label in ("runtime", "filters", "schema") if label in parts]
    if ordered and len(ordered) == len(parts):
        return ", ".join(ordered)
    return lowered


def _coarsen_silver_validation(value: str) -> str:
    direct_matches = {
        "none": "none",
        "not_populated_by_transformer": "not_populated_by_transformer",
        "runtime_contract": "runtime_contract",
    }
    if value in direct_matches:
        return direct_matches[value]

    runtime_contract_match = _coarsen_runtime_contract_validation(value)
    if runtime_contract_match is not None:
        return runtime_contract_match

    prefixed_match = _coarsen_prefixed_validation(value)
    if prefixed_match is not None:
        return prefixed_match

    pandera_match = _coarsen_pandera_validation(value)
    if pandera_match is not None:
        return pandera_match

    return value


def _coarsen_quality_validation(value: str) -> str:
    if "required_if" in value or "required;" in value:
        return "quality_rule; required"
    if "enum" in value:
        return "quality_rule; enum"
    return "quality_rule"


def _coarsen_cross_field_validation(value: str) -> str:
    if "not_null" in value:
        return "cross_field_rule; not_null"
    return "cross_field_rule"


def _coarsen_required_validation(value: str) -> str:
    if CROSS_FIELD_PREFIX in value:
        return "required_rule; cross_field_rule"
    if KEY_NOT_NULL_PREFIX in value:
        return "required_rule; key_not_null"
    return "required_rule"


def _coarsen_runtime_contract_validation(value: str) -> str | None:
    runtime_contract_prefixes = (
        ("runtime_contract; write_time_lineage_required", "write_time_contract"),
        ("runtime_contract; dq_marker", RUNTIME_DQ_MARKER),
        ("runtime_contract; lineage_metadata", RUNTIME_LINEAGE_METADATA),
        ("runtime_contract;", "runtime_contract; generated_field"),
    )
    for prefix, normalized in runtime_contract_prefixes:
        if value.startswith(prefix):
            return normalized
    return None


def _coarsen_prefixed_validation(value: str) -> str | None:
    if value.startswith("quality:"):
        return _coarsen_quality_validation(value)
    if value.startswith("custom;"):
        return "custom_rule"
    if value.startswith(CROSS_FIELD_PREFIX):
        return _coarsen_cross_field_validation(value)
    if value.startswith("required;"):
        return _coarsen_required_validation(value)
    if value.startswith(KEY_NOT_NULL_PREFIX):
        return "key_not_null"
    return None


def _coarsen_pandera_validation(value: str) -> str | None:
    for prefix in (PANDERA_PATTERN, "pandera:enum", "pandera:range"):
        normalized = _coarsen_pandera_family(value, prefix)
        if normalized is not None:
            return normalized
    if value.startswith("pandera:") and "not_null" in value:
        return "pandera:not_null"
    if value.startswith("pandera:"):
        return "pandera:typed_rule"
    return None


def _coarsen_pandera_family(value: str, prefix: str) -> str | None:
    if not value.startswith(prefix):
        return None
    if CROSS_FIELD_PREFIX in value:
        return f"{prefix}; cross_field_rule"
    if KEY_NOT_NULL_PREFIX in value:
        return f"{prefix}; key_not_null"
    if "not_null" in value:
        return f"{prefix}; not_null"
    return prefix


def _canonicalize(header: str, raw_value: str) -> str:
    value = (
        " ".join(raw_value.strip().split())
        if header not in CANONICALIZED_SEMICOLON_HEADERS
        else "; ".join(part.strip() for part in raw_value.split(";") if part.strip())
    )

    if header in {"Source_Field_Type", "Type"}:
        return TYPE_MAP.get(value.lower(), value)
    if header in {"Source_Field_Nullable", "Nullable"}:
        return NULLABLE_MAP.get(value.lower(), value.lower())
    if header == "Required":
        return _normalize_required(value)
    mapped_value = _canonicalize_with_lookup(header, raw_value, value)
    if mapped_value is not None:
        return mapped_value
    if header == "Silver Validation":
        mapped = SILVER_VALIDATION_MAP.get(
            raw_value, SILVER_VALIDATION_MAP.get(value, value)
        )
        return _coarsen_silver_validation(mapped)
    return value


def _canonicalize_with_lookup(header: str, raw_value: str, value: str) -> str | None:
    mapping = CANONICAL_HEADER_MAPS.get(header)
    if mapping is None:
        return None
    return mapping.get(raw_value, mapping.get(value, value))


def _mapping_payload() -> dict[str, object]:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "columns": MAPPING_PAYLOAD_COLUMNS,
        "notes": {
            "Required": "normalized via ordered runtime/filters/schema vocabulary",
        },
    }


def _build_temp_output_path(input_path: Path, output_path: Path) -> Path:
    if input_path != output_path:
        return output_path
    return output_path.with_name(f".{output_path.stem}.tmp{output_path.suffix}")


def _header_by_index(
    first_row: ET.Element, shared_strings: list[str]
) -> dict[int, str]:
    return {
        column_index(cell.attrib["r"]): cell_text(cell, shared_strings)
        for cell in first_row.findall("a:c", NS)
    }


def _normalize_sheet_rows(
    rows: list[ET.Element],
    shared_strings: list[str],
    applied_counter: dict[str, Counter[str]],
) -> None:
    header_by_index = _header_by_index(rows[0], shared_strings)
    for row in rows[1:]:
        for cell in row.findall("a:c", NS):
            index = column_index(cell.attrib["r"])
            header = header_by_index.get(index)
            if header not in TARGET_COLUMNS:
                continue
            raw = cell_text(cell, shared_strings)
            canonical = _canonicalize(header, raw)
            applied_counter[header][canonical] += 1
            if canonical != raw:
                set_cell_text(cell, canonical)


def _write_normalized_workbook(
    input_path: Path,
    temp_output_path: Path,
) -> dict[str, Counter[str]]:
    with zipfile.ZipFile(input_path) as zin:
        shared_strings = load_shared_strings(zin)
        sheet_targets = sheet_target_paths(zin)
        applied_counter: dict[str, Counter[str]] = {
            column: Counter() for column in TARGET_COLUMNS
        }

        with zipfile.ZipFile(
            temp_output_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename not in sheet_targets:
                    zout.writestr(copy.copy(info), data)
                    continue

                root = ET.fromstring(data)
                sheet_data = root.find("a:sheetData", NS)
                rows = [] if sheet_data is None else sheet_data.findall("a:row", NS)
                if not rows:
                    zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))
                    continue

                _normalize_sheet_rows(rows, shared_strings, applied_counter)
                zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))

    return applied_counter


def _write_mapping_output(
    mapping_output: Path, applied_counter: dict[str, Counter[str]]
) -> None:
    payload = _mapping_payload()
    payload["applied_value_counts"] = {
        column: dict(counter.most_common())
        for column, counter in applied_counter.items()
    }
    mapping_output.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def main() -> int:
    args = _arg_parser().parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    mapping_output = args.mapping_output.resolve()
    temp_output_path = _build_temp_output_path(input_path, output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_output.parent.mkdir(parents=True, exist_ok=True)
    applied_counter = _write_normalized_workbook(input_path, temp_output_path)

    if temp_output_path != output_path:
        temp_output_path.replace(output_path)

    _write_mapping_output(mapping_output, applied_counter)
    print(
        {
            "input": str(input_path),
            "output": str(output_path),
            "mapping_output": str(mapping_output),
            "normalized_columns": len(TARGET_COLUMNS),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
