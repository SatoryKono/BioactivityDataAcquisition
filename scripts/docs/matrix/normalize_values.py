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
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.docs.common.xlsx import (
    MAIN_NS,
    NS,
    cell_text,
    column_index,
    load_shared_strings,
    set_cell_text,
    sheet_target_paths,
)

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
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
TARGET_COLUMNS: Final[tuple[str, ...]] = (
    "Source_Field_Type",
    "Type",
    "Source_Field_Nullable",
    "Nullable",
    "Required",
    "Silver Filters",
    "Filter fail sink",
    "Silver Normalisation",
    "Source_Field_Normalisation",
    "Silver Validation",
    "Source_Field_Validation",
    "Validation fail action",
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
    "json/object": "json/object",
    "object": "json/object",
    "json/array": "json/array",
    "array": "json/array",
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
    "IN {0}; not null": "enum_constraint; not_null",
    "IN {1}": "enum_constraint",
    "IN {=}; not null": "enum_constraint; not_null",
    "IN {B, F}; not null": "enum_constraint; not_null",
    "IN {B, F}; required": "enum_constraint; required",
    "IN {D}": "enum_constraint",
    "IN {IC50, Ki}; not null": "enum_constraint; not_null",
    "IN {MOL}": "enum_constraint",
    "IN {SINGLE PROTEIN}": "enum_constraint",
    "IN {Small molecule}": "enum_constraint",
    "IN {journal-article}; required": "enum_constraint; required",
    "IN {nM}; not null": "enum_constraint; not_null",
    "exclude_if_present": "exclude_if_present",
    "range >= 1950 and <= 2050": "range_constraint",
    "range >= 8 and <= 9": "range_constraint",
    "required; extraction-side fixed value = 1": "required; fixed_value=1",
    "required; range 1950..2050": "required; range_constraint",
    "required; range 3..10": "required; range_constraint",
    "required; range > 0": "required; range_constraint",
    "required; range >=1": "required; range_constraint",
}
SILVER_VALIDATION_MAP: Final[dict[str, str]] = {
    "-": "none",
    "runtime-managed field": "runtime_contract",
    "DQ marker field": "runtime_contract; dq_marker",
    "Internal identity/hash generation": "runtime_contract; generated_internal_field",
    "Pandera non-null string field": "pandera:string; not_null",
    "pattern": "pandera:pattern",
    "Lineage metadata": "runtime_contract; lineage_metadata",
    "No runtime validation because current ActivityTransformer does not populate this field": (
        "not_populated_by_transformer"
    ),
    "pattern; non-null": "pandera:pattern; not_null",
    "Pandera 0 or 1; non-null": "pandera:enum:{0,1}; not_null",
    "Pandera CHEMBL_ID_PATTERN; non-null": (
        "pandera:pattern:CHEMBL_ID_PATTERN; not_null"
    ),
    "Pandera non-null integer field": "pandera:integer; not_null",
    "cross-field: structure_completeness": "cross_field:structure_completeness",
    "key_nullability: partition not nullable": "key_not_null:partition",
    "pattern; cross-field: record_linkage": "pandera:pattern; cross_field:record_linkage",
    "pattern; cross-field: term_completeness": (
        "pandera:pattern; cross_field:term_completeness"
    ),
    "pattern; key_nullability: merge not nullable": "pandera:pattern; key_not_null:merge",
    "range; min=0, max=-": "pandera:range:min=0",
    "range; min=0, max=1": "pandera:range:min=0,max=1",
    "range; min=1, max=-; cross-field: similarity_pair": (
        "pandera:range:min=1; cross_field:similarity_pair"
    ),
    "range; min=1, max=-; key_nullability: merge not nullable": (
        "pandera:range:min=1; key_not_null:merge"
    ),
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
    "enum; allowed=MESH_HEADING,KEYWORD,AUTHOR,INSTITUTION; cross-field: term_completeness; key_nullability: partition not nullable": (
        "pandera:enum:{MESH_HEADING,KEYWORD,AUTHOR,INSTITUTION}; cross_field:term_completeness; key_not_null:partition"
    ),
    "enum; allowed=MOL,SEQ,NONE,BOTH": "pandera:enum:{MOL,SEQ,NONE,BOTH}",
    "enum; allowed=PROTEIN,DNA,RNA": "pandera:enum:{PROTEIN,DNA,RNA}",
    "enum; allowed=SINGLE PROTEIN,PROTEIN COMPLEX,PROTEIN FAMILY,SELECTIVITY GROUP,ORGANISM,TISSUE,CELL-LINE,SUBCELLULAR,UNKNOWN,CHIMERIC PROTEIN,PROTEIN-PROTEIN INTERACTION,NUCLEIC-ACID,METAL,LIPID,MACROMOLECULE,PHENOTYPE,ADMET; key_nullability: partition not nullable": (
        "pandera:enum:{SINGLE PROTEIN,PROTEIN COMPLEX,PROTEIN FAMILY,SELECTIVITY GROUP,ORGANISM,TISSUE,CELL-LINE,SUBCELLULAR,UNKNOWN,CHIMERIC PROTEIN,PROTEIN-PROTEIN INTERACTION,NUCLEIC-ACID,METAL,LIPID,MACROMOLECULE,PHENOTYPE,ADMET}; key_not_null:partition"
    ),
    "enum; allowed=Small molecule,Protein,Antibody,Oligosaccharide,Oligonucleotide,Cell,Enzyme,Unknown; key_nullability: partition not nullable": (
        "pandera:enum:{Small molecule,Protein,Antibody,Oligosaccharide,Oligonucleotide,Cell,Enzyme,Unknown}; key_not_null:partition"
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
    if value == "none":
        return "none"
    if value == "not_populated_by_transformer":
        return "not_populated_by_transformer"
    if value.startswith("runtime_contract; write_time_lineage_required"):
        return "write_time_contract"
    if value == "runtime_contract":
        return "runtime_contract"
    if value.startswith("runtime_contract; dq_marker"):
        return "runtime_contract; dq_marker"
    if value.startswith("runtime_contract; lineage_metadata"):
        return "runtime_contract; lineage_metadata"
    if value.startswith("runtime_contract;"):
        return "runtime_contract; generated_field"
    if value.startswith("quality:"):
        if "required_if" in value or "required;" in value:
            return "quality_rule; required"
        if "enum" in value:
            return "quality_rule; enum"
        return "quality_rule"
    if value.startswith("custom;"):
        return "custom_rule"
    if value.startswith("cross_field:"):
        if "not_null" in value:
            return "cross_field_rule; not_null"
        return "cross_field_rule"
    if value.startswith("required;"):
        if "cross_field:" in value:
            return "required_rule; cross_field_rule"
        if "key_not_null:" in value:
            return "required_rule; key_not_null"
        return "required_rule"
    if value.startswith("key_not_null:"):
        return "key_not_null"
    if value.startswith("pandera:pattern"):
        if "cross_field:" in value:
            return "pandera:pattern; cross_field_rule"
        if "key_not_null:" in value:
            return "pandera:pattern; key_not_null"
        if "not_null" in value:
            return "pandera:pattern; not_null"
        return "pandera:pattern"
    if value.startswith("pandera:enum"):
        if "cross_field:" in value:
            return "pandera:enum; cross_field_rule"
        if "key_not_null:" in value:
            return "pandera:enum; key_not_null"
        if "not_null" in value:
            return "pandera:enum; not_null"
        return "pandera:enum"
    if value.startswith("pandera:range"):
        if "cross_field:" in value:
            return "pandera:range; cross_field_rule"
        if "key_not_null:" in value:
            return "pandera:range; key_not_null"
        if "not_null" in value:
            return "pandera:range; not_null"
        return "pandera:range"
    if value.startswith("pandera:") and "not_null" in value:
        return "pandera:not_null"
    if value.startswith("pandera:"):
        return "pandera:typed_rule"
    return value


def _canonicalize(header: str, raw_value: str) -> str:
    value = (
        " ".join(raw_value.strip().split())
        if header
        not in {
            "Silver Filters",
            "Silver Validation",
            "Source_Field_Validation",
            "Silver Normalisation",
            "Source_Field_Normalisation",
            "Validation fail action",
        }
        else "; ".join(part.strip() for part in raw_value.split(";") if part.strip())
    )

    if header in {"Source_Field_Type", "Type"}:
        return TYPE_MAP.get(value.lower(), value)
    if header in {"Source_Field_Nullable", "Nullable"}:
        return NULLABLE_MAP.get(value.lower(), value.lower())
    if header == "Required":
        return _normalize_required(value)
    if header == "Filter fail sink":
        return FILTER_FAIL_SINK_MAP.get(
            raw_value, FILTER_FAIL_SINK_MAP.get(value, value)
        )
    if header == "Silver Normalisation":
        return SILVER_NORMALISATION_MAP.get(
            raw_value, SILVER_NORMALISATION_MAP.get(value, value)
        )
    if header == "Source_Field_Normalisation":
        return SOURCE_FIELD_NORMALISATION_MAP.get(
            raw_value, SOURCE_FIELD_NORMALISATION_MAP.get(value, value)
        )
    if header == "Silver Filters":
        return SILVER_FILTERS_MAP.get(raw_value, SILVER_FILTERS_MAP.get(value, value))
    if header == "Silver Validation":
        mapped = SILVER_VALIDATION_MAP.get(
            raw_value, SILVER_VALIDATION_MAP.get(value, value)
        )
        return _coarsen_silver_validation(mapped)
    if header == "Source_Field_Validation":
        return SOURCE_FIELD_VALIDATION_MAP.get(
            raw_value, SOURCE_FIELD_VALIDATION_MAP.get(value, value)
        )
    if header == "Validation fail action":
        return VALIDATION_FAIL_ACTION_MAP.get(
            raw_value, VALIDATION_FAIL_ACTION_MAP.get(value, value)
        )
    return value


def _mapping_payload() -> dict[str, object]:
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "columns": {
            "Source_Field_Type": TYPE_MAP,
            "Type": TYPE_MAP,
            "Source_Field_Nullable": NULLABLE_MAP,
            "Nullable": NULLABLE_MAP,
            "Filter fail sink": FILTER_FAIL_SINK_MAP,
            "Silver Normalisation": SILVER_NORMALISATION_MAP,
            "Source_Field_Normalisation": SOURCE_FIELD_NORMALISATION_MAP,
            "Silver Filters": SILVER_FILTERS_MAP,
            "Silver Validation": SILVER_VALIDATION_MAP,
            "Source_Field_Validation": SOURCE_FIELD_VALIDATION_MAP,
            "Validation fail action": VALIDATION_FAIL_ACTION_MAP,
        },
        "notes": {
            "Required": "normalized via ordered runtime/filters/schema vocabulary",
        },
    }


def main() -> int:
    args = _arg_parser().parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    mapping_output = args.mapping_output.resolve()
    temp_output_path = (
        output_path.with_name(f".{output_path.stem}.tmp{output_path.suffix}")
        if input_path == output_path
        else output_path
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mapping_output.parent.mkdir(parents=True, exist_ok=True)

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
                rows = root.find("a:sheetData", NS).findall("a:row", NS)
                if not rows:
                    zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))
                    continue

                header_by_index: dict[int, str] = {}
                for cell in rows[0].findall("a:c", NS):
                    header_by_index[column_index(cell.attrib["r"])] = cell_text(
                        cell, shared_strings
                    )

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

                zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))

    if temp_output_path != output_path:
        temp_output_path.replace(output_path)

    payload = _mapping_payload()
    payload["applied_value_counts"] = {
        column: dict(counter.most_common())
        for column, counter in applied_counter.items()
    }
    mapping_output.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
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
