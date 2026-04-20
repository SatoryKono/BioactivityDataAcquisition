#!/usr/bin/env python3
"""Populate exact Silver normalization detail strings in the ChEMBL matrix workbook."""

from __future__ import annotations

import argparse
import copy
import sys
import zipfile
from pathlib import Path
from typing import Final
from xml.etree import ElementTree as ET

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import PROJECT_ROOT, ensure_repo_imports
else:
    from scripts.docs.matrix._bootstrap import PROJECT_ROOT, ensure_repo_imports

ensure_repo_imports()

from scripts.docs.common.xlsx import (
    MAIN_NS,
    NS,
    cell_text,
    column_index,
    column_letters,
    load_shared_strings,
    set_cell_text,
    sheet_target_name_map,
    update_dimension,
)

DEFAULT_INPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
DEFAULT_OUTPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
DETAIL_HEADER: Final[str] = "Silver Normalisation Detail"
DETAIL_ID_HEADER: Final[str] = "Silver Normalisation Detail ID"
MAX_DETAIL_LENGTH: Final[int] = 100
_NO_EXTRA_CHEMBL_REWRITE: Final[str] = "no extra ChEMBL-specific rewrite"
_SOURCE_NORMALIZATION_DETAILS: Final[dict[str, str]] = {
    "trim; blank_to_null": "trim; blank->null",
    "runtime-managed": "runtime-managed",
    "derived_from_transformer": "derived in transformer",
    "numeric_only; blank_to_null": "numeric only; blank->null",
    "trim; identifier_normalized": "trim; id normalized",
    "trim; blank_to_null; controlled_vocabulary": "trim; blank->null; enum source",
    "numeric_only": "numeric only",
    "trim; blank_to_null; value_xor_text_value": "trim; blank->null; value xor text",
    "derived_from_nested; trim; blank_to_null": "nested extract; trim; blank->null",
    "numeric_only; value_xor_text_value; relation_required_if_value": (
        "numeric only; value xor text; relation if value"
    ),
    "derived_from_nested; trim; blank_to_null; identifier_normalized": (
        "nested extract; trim; blank->null; id norm"
    ),
    "derived_from_nested; trim; controlled_vocabulary": (
        "nested extract; trim; enum source"
    ),
    "trim; blank_to_null; identifier_normalized": "trim; blank->null; id normalized",
    "trim; controlled_vocabulary": "trim; enum source",
}

_TOKEN_DETAILS: Final[dict[str, str]] = {
    "passthrough": "scalar passthrough",
    "invalid_type_to_null": "invalid type -> null",
    "string_normalized": "normalized string",
    "boolean_flag": "normalized boolean flag",
    "entity_id_generated": "entity_id generated",
    "content_hash_generated": "content hash generated",
    "datetime_to_iso8601": "datetime -> ISO 8601",
    "runtime_counter": "runtime counter",
    "lineage_optional_normalized": "optional lineage normalized",
    "renamed": "renamed to canonical column",
    "nested_flattened": "nested field flattened",
    "float_coerced": "safe_float coercion",
    "integer_coerced": "safe_int/INT coercion",
    "nullable_integer_as_float": "nullable int via float path",
    "identifier_to_string": "identifier -> string",
    "fallback_identifier_to_string": "fallback identifier -> string",
    "taxonomy_id_validated": "taxonomy id validated",
    "proposed_null_then_quarantine": "null first; quarantine later",
    "json_serialized": "JSON serialized",
    "runtime_lineage_injected": "runtime lineage injected",
    "runtime_state_propagated": "runtime state propagated",
    "runtime_managed": "runtime-managed field",
}
_SHEET_COLUMN_OVERRIDES: Final[dict[tuple[str, str], str]] = {
    ("chembl_publication", "title"): "normalize_title(): html strip; NFC; ws collapse",
    ("chembl_publication", "abstract"): "normalize_abstract(): html strip; NFC; ws collapse",
    ("chembl_publication", "authors"): "normalize_author_list(): parse -> JSON",
    ("chembl_publication", "author_keys"): "normalize_author_keys(): Surname_F pipe-joined",
    ("chembl_publication", "publication_type"): "doc_type -> canonical kebab-case type",
    ("chembl_publication", "publication_year"): "publication_year via INT coercion",
    ("chembl_publication", "creation_date"): "nested chembl_release.creation_date passthrough",
    ("chembl_assay", "bao_format"): "trim; blank->null; BAO id -> canonical BAO_########",
    ("chembl_assay", "bao_label"): "canonical from BAO format when known; else trim; lower",
    ("chembl_assay", "assay_organism"): "trim; blank->null; ws collapse; drop trailing strain notes",
    ("chembl_activity", "standard_units"): "trim; blank->null; shared unit aliases -> canonical symbol",
    ("chembl_activity", "uo_units"): "trim; blank->null; UO id -> canonical UO_########",
    ("chembl_activity", "qudt_units"): "trim; blank->null; preserve full URI",
    ("chembl_activity", "target_taxonomy_id"): "target_tax_id -> target_taxonomy_id; validate",
    ("chembl_target", "organism_class"): "derived via organism classifier; taxonomy first",
    ("chembl_target", "organism"): "trim; blank->null; ws collapse; drop trailing strain notes",
    ("chembl_target", "taxonomy_id"): "TaxonomyId.from_raw(): trim; int; invalid->null",
    ("chembl_molecule", "canonical_smiles"): "SMILES.from_raw(canonical=True); trim; empty->null",
    ("chembl_molecule", "inchi_key"): "InChIKey.from_raw(): trim; upper; pattern check",
}
_SHEET_COLUMN_SET_OVERRIDES: Final[dict[tuple[str, frozenset[str]], str]] = {
    (
        "chembl_publication",
        frozenset({"publication_doi", "doi"}),
    ): "DOI: strip prefix; trim; lower; invalid->null",
    (
        "chembl_publication",
        frozenset({"publication_pmid", "pmid"}),
    ): "PMID: digits only; int->str; invalid->null",
    (
        "chembl_publication",
        frozenset({"page_first", "page_last"}),
    ): "renamed page field; trimmed text passthrough",
    (
        "chembl_activity",
        frozenset({"bao_endpoint", "bao_format"}),
    ): "trim; blank->null; BAO id -> canonical BAO_########",
}
_COLUMN_ONLY_OVERRIDES: Final[dict[str, str]] = {
    "bao_label": "BAO label passthrough",
    "author_orcids": _NO_EXTRA_CHEMBL_REWRITE,
    "affiliation_list": _NO_EXTRA_CHEMBL_REWRITE,
    "publication_type_unified": _NO_EXTRA_CHEMBL_REWRITE,
    "publication_date": _NO_EXTRA_CHEMBL_REWRITE,
}


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Populate exact per-row Silver normalization detail strings in the "
            "canonical ChEMBL matrix workbook."
        )
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT, help="Input workbook."
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="Output workbook."
    )
    return parser


def _append_or_update_cell(
    row: ET.Element,
    col_index: int,
    value: str,
    template_cell: ET.Element | None,
) -> None:
    ref = f"{column_letters(col_index)}{row.attrib['r']}"
    for cell in row.findall("a:c", NS):
        if column_index(cell.attrib["r"]) == col_index:
            set_cell_text(cell, value)
            return

    cell = ET.Element(f"{{{MAIN_NS}}}c")
    cell.set("r", ref)
    if template_cell is not None and "s" in template_cell.attrib:
        cell.set("s", template_cell.attrib["s"])
    set_cell_text(cell, value)
    row.append(cell)


def _source_clause(source_norm: str) -> str | None:
    return _SOURCE_NORMALIZATION_DETAILS.get(source_norm)


def _split_tokens(value: str) -> list[str]:
    return [token.strip() for token in value.split(";") if token.strip()]


def _token_clauses(tokens: list[str], row: dict[str, str]) -> list[str]:
    clauses: list[str] = []
    source_field = row.get("Source Field", "")
    silver_column = row.get("Silver column", "")

    for token in tokens:
        if (
            token == "renamed"
            and source_field
            and silver_column
            and source_field != silver_column
        ):
            clauses.append(f"`{source_field}` -> `{silver_column}`")
            continue
        clause = _TOKEN_DETAILS.get(token)
        if clause:
            clauses.append(clause)
    return clauses


def _sheet_set_override(sheet_name: str, silver_column: str) -> str | None:
    for (candidate_sheet, columns), detail in _SHEET_COLUMN_SET_OVERRIDES.items():
        if sheet_name == candidate_sheet and silver_column in columns:
            return detail
    return None


def _override_detail(sheet_name: str, row: dict[str, str]) -> str | None:
    silver_column = row.get("Silver column", "")
    return (
        _sheet_set_override(sheet_name, silver_column)
        or _SHEET_COLUMN_OVERRIDES.get((sheet_name, silver_column))
        or _COLUMN_ONLY_OVERRIDES.get(silver_column)
    )


def _build_detail(sheet_name: str, row: dict[str, str]) -> str:
    override = _override_detail(sheet_name, row)
    if override is not None:
        return override

    parts: list[str] = []
    source_norm = row.get("Source_Field_Normalisation", "")
    silver_norm = row.get("Silver Normalisation", "")

    source_clause = _source_clause(source_norm)
    if source_clause:
        parts.append(source_clause)

    token_clauses = _token_clauses(_split_tokens(silver_norm), row)
    parts.extend(token_clauses)

    if not parts:
        return "no extra normalization rule recorded"
    detail = "; ".join(parts)
    if len(detail) <= MAX_DETAIL_LENGTH:
        return detail
    compact_parts = [part.replace("normalized", "norm") for part in parts]
    detail = "; ".join(compact_parts)
    if len(detail) <= MAX_DETAIL_LENGTH:
        return detail
    return detail[: MAX_DETAIL_LENGTH - 3].rstrip(" ;") + "..."


def _collect_sheet_details(
    archive: zipfile.ZipFile,
    *,
    shared_strings: list[str],
    sheet_targets: dict[str, str],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Collect per-row detail strings and global IDs in first-seen order."""
    detail_rows_by_sheet: dict[str, list[str]] = {}
    detail_ids: dict[str, int] = {}
    next_id = 1

    for sheet_path, sheet_name in sheet_targets.items():
        root = ET.fromstring(archive.read(sheet_path))
        sheet_data = root.find("a:sheetData", NS)
        rows = sheet_data.findall("a:row", NS)
        if not rows:
            detail_rows_by_sheet[sheet_name] = []
            continue

        header_map = {
            column_index(cell.attrib["r"]): cell_text(cell, shared_strings)
            for cell in rows[0].findall("a:c", NS)
        }

        details: list[str] = []
        for row in rows[1:]:
            row_map = {
                header_map[column_index(cell.attrib["r"])]: cell_text(
                    cell, shared_strings
                )
                for cell in row.findall("a:c", NS)
                if column_index(cell.attrib["r"]) in header_map
            }
            detail = _build_detail(sheet_name, row_map)
            details.append(detail)
            if detail not in detail_ids:
                detail_ids[detail] = next_id
                next_id += 1

        detail_rows_by_sheet[sheet_name] = details

    return detail_rows_by_sheet, detail_ids


def main() -> int:
    args = _arg_parser().parse_args()
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output_path = (
        output_path.with_name(f".{output_path.stem}.tmp{output_path.suffix}")
        if input_path == output_path
        else output_path
    )

    with zipfile.ZipFile(input_path) as zin:
        shared_strings = load_shared_strings(zin)
        sheet_targets = sheet_target_name_map(zin)
        detail_rows_by_sheet, detail_ids = _collect_sheet_details(
            zin,
            shared_strings=shared_strings,
            sheet_targets=sheet_targets,
        )

        with zipfile.ZipFile(
            temp_output_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as zout:
            for info in zin.infolist():
                data = zin.read(info.filename)
                if info.filename not in sheet_targets:
                    zout.writestr(copy.copy(info), data)
                    continue
                sheet_name = sheet_targets[info.filename]

                root = ET.fromstring(data)
                sheet_data = root.find("a:sheetData", NS)
                rows = sheet_data.findall("a:row", NS)
                if not rows:
                    zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))
                    continue

                header_row = rows[0]
                header_map = {
                    column_index(cell.attrib["r"]): cell_text(cell, shared_strings)
                    for cell in header_row.findall("a:c", NS)
                }
                ordered_indexes = sorted(header_map)
                max_col_index = max(ordered_indexes)
                detail_col_index = next(
                    (
                        index
                        for index, header in header_map.items()
                        if header == DETAIL_HEADER
                    ),
                    max_col_index + 1,
                )
                detail_id_col_index = next(
                    (
                        index
                        for index, header in header_map.items()
                        if header == DETAIL_ID_HEADER
                    ),
                    max(max_col_index, detail_col_index) + 1,
                )

                note_template = next(
                    (
                        cell
                        for cell in header_row.findall("a:c", NS)
                        if column_index(cell.attrib["r"]) == max_col_index
                    ),
                    None,
                )
                _append_or_update_cell(
                    header_row,
                    detail_col_index,
                    DETAIL_HEADER,
                    note_template,
                )
                _append_or_update_cell(
                    header_row,
                    detail_id_col_index,
                    DETAIL_ID_HEADER,
                    note_template,
                )

                sheet_details = detail_rows_by_sheet.get(sheet_name, [])
                for row_index, row in enumerate(rows[1:]):
                    row_map = {
                        header_map[column_index(cell.attrib["r"])]: cell_text(
                            cell, shared_strings
                        )
                        for cell in row.findall("a:c", NS)
                        if column_index(cell.attrib["r"]) in header_map
                    }
                    if row_index < len(sheet_details):
                        detail = sheet_details[row_index]
                    else:
                        detail = _build_detail(sheet_name, row_map)
                    detail_id = str(detail_ids[detail])
                    template_cell = next(
                        (
                            cell
                            for cell in row.findall("a:c", NS)
                            if column_index(cell.attrib["r"]) == max_col_index
                        ),
                        None,
                    )
                    _append_or_update_cell(row, detail_col_index, detail, template_cell)
                    _append_or_update_cell(
                        row,
                        detail_id_col_index,
                        detail_id,
                        template_cell,
                    )

                update_dimension(
                    root,
                    len(rows),
                    max(max_col_index, detail_col_index, detail_id_col_index),
                )
                zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))

    if temp_output_path != output_path:
        temp_output_path.replace(output_path)

    print(
        {
            "input": str(input_path),
            "output": str(output_path),
            "detail_header": DETAIL_HEADER,
            "detail_id_header": DETAIL_ID_HEADER,
            "unique_detail_count": len(detail_ids),
            "max_detail_length": MAX_DETAIL_LENGTH,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
