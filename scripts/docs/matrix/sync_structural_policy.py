#!/usr/bin/env python3
"""Sync ChEMBL matrix workbook rows with current structural Silver policy semantics."""

from __future__ import annotations

import argparse
import copy
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Final
from xml.etree import ElementTree as ET

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import PROJECT_ROOT, ensure_repo_imports
else:
    from scripts.docs.matrix._bootstrap import PROJECT_ROOT, ensure_repo_imports

ensure_repo_imports(include_src=True)

from scripts.docs.common.xlsx import (
    MAIN_NS,
    NS,
    cell_text,
    column_index,
    load_shared_strings,
    set_cell_text,
    sheet_target_paths,
)
from scripts.docs.matrix.structural_contract import (
    DEFAULT_CONTRACT_EXPORT,
    INVALID_TYPE_TO_NULL,
    NOT_APPLICABLE,
    PROPOSED_NULL_THEN_QUARANTINE,
    QUARANTINE,
    QUARANTINE_FILTER_REJECTION,
    SET_NULL_AND_WARN,
    STRUCTURAL_BOOLEAN_VOCABULARY_VALIDATION,
    STRUCTURAL_CUSTOM_EMPTY_SEMANTICS_VALIDATION,
    STRUCTURAL_NO_STRING_COERCION_VALIDATION,
    STRUCTURAL_OPTIONAL_NONNULLABLE_VALIDATION,
    STRUCTURAL_PRESENCE_GUARD,
    STRUCTURAL_PRESENCE_VALIDATION,
    STRUCTURAL_TYPE_GUARD,
    STRUCTURAL_TYPE_STRICT_VALIDATION,
    STRUCTURAL_TYPE_TO_NULL_WARN_VALIDATION,
    MatrixStructuralContractRow,
    contract_lookup_key,
    index_runtime_contract_rows,
    load_runtime_contract_export,
    resolve_required_display,
    write_runtime_contract_export,
)

DEFAULT_INPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
DEFAULT_OUTPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
SYSTEM_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_dq_warn",
        "_dq_error",
        "_state",
        "entity_id",
        "content_hash",
    }
)
REQUIRED_FILTER_TOKENS: Final[frozenset[str]] = frozenset({"required", "not_null"})
PROPOSE_NULL_WARN_ERROR_THEN_QUARANTINE: Final[str] = (
    "propose_null_warn_error_then_quarantine"
)
NONE_TOKEN: Final[str] = "none"
NOT_APPLICABLE_TOKEN: Final[str] = "not_applicable"
EMPTY_SEMANTICS_TOKENS: Final[frozenset[str]] = frozenset(
    {NONE_TOKEN, NOT_APPLICABLE_TOKEN}
)
STRUCTURAL_FILTER_TOKENS: Final[frozenset[str]] = frozenset(
    {STRUCTURAL_PRESENCE_GUARD, STRUCTURAL_TYPE_GUARD}
)
STRUCTURAL_VALIDATION_TOKENS: Final[frozenset[str]] = frozenset(
    {
        STRUCTURAL_PRESENCE_VALIDATION,
        STRUCTURAL_TYPE_STRICT_VALIDATION,
        STRUCTURAL_TYPE_TO_NULL_WARN_VALIDATION,
        STRUCTURAL_OPTIONAL_NONNULLABLE_VALIDATION,
        STRUCTURAL_CUSTOM_EMPTY_SEMANTICS_VALIDATION,
        STRUCTURAL_NO_STRING_COERCION_VALIDATION,
        STRUCTURAL_BOOLEAN_VOCABULARY_VALIDATION,
    }
)
STRUCTURAL_NORMALISATION_TOKENS: Final[frozenset[str]] = frozenset(
    {INVALID_TYPE_TO_NULL, PROPOSED_NULL_THEN_QUARANTINE}
)
STRUCTURAL_ACTION_TOKENS: Final[frozenset[str]] = frozenset(
    {
        SET_NULL_AND_WARN,
        QUARANTINE_FILTER_REJECTION,
        PROPOSE_NULL_WARN_ERROR_THEN_QUARANTINE,
    }
)
SILVER_FILTERS_HEADER: Final[str] = "Silver Filters"
FILTER_FAIL_SINK_HEADER: Final[str] = "Filter fail sink"
SILVER_NORMALISATION_HEADER: Final[str] = "Silver Normalisation"
SILVER_VALIDATION_HEADER: Final[str] = "Silver Validation"
VALIDATION_FAIL_ACTION_HEADER: Final[str] = "Validation fail action"
HEADERS_TO_UPDATE: Final[tuple[str, ...]] = (
    "Type",
    "Nullable",
    "Required",
    SILVER_FILTERS_HEADER,
    FILTER_FAIL_SINK_HEADER,
    SILVER_NORMALISATION_HEADER,
    SILVER_VALIDATION_HEADER,
    VALIDATION_FAIL_ACTION_HEADER,
)


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Sync the canonical ChEMBL matrix workbook with the current structural "
            "Silver policy semantics."
        )
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT, help="Input workbook."
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="Output workbook."
    )
    parser.add_argument(
        "--contract-export",
        type=Path,
        default=DEFAULT_CONTRACT_EXPORT,
        help="Runtime structural contract export JSON.",
    )
    parser.add_argument(
        "--refresh-contract-export",
        action="store_true",
        help="Rebuild the runtime structural contract export before syncing.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with status 1 if the workbook would change, without rewriting it.",
    )
    return parser


def _parse_tokens(
    value: str,
    *,
    drop: frozenset[str] | None = None,
) -> list[str]:
    blocked = drop or frozenset()
    return [
        part.strip()
        for part in value.split(";")
        if part.strip() and part.strip() not in blocked
    ]


def _join_tokens(
    prefix: list[str], existing: list[str], *, drop: frozenset[str] | None = None
) -> str:
    seen: set[str] = set()
    ordered: list[str] = []
    blocked = drop or frozenset()
    for token in [*prefix, *existing]:
        if token in blocked or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return "; ".join(ordered) if ordered else NONE_TOKEN


def _prepend_action(existing_value: str, action: str) -> str:
    existing_tokens = _parse_tokens(existing_value)
    return _join_tokens([action], existing_tokens, drop=EMPTY_SEMANTICS_TOKENS)


def _resolve_runtime_contract(
    row: dict[str, str],
    contract_index: dict[tuple[str, str, str], MatrixStructuralContractRow],
) -> MatrixStructuralContractRow | None:
    """Resolve workbook row to runtime structural contract export row."""
    source_db = row.get("Source DB", "")
    source_table = row.get("Source Table", "")
    silver_column = row.get("Silver column", "")
    if not source_db or not source_table or not silver_column:
        return None
    return contract_index.get(
        contract_lookup_key(source_db, source_table, silver_column)
    )


def _update_row(
    row: dict[str, str],
    *,
    contract_index: dict[tuple[str, str, str], MatrixStructuralContractRow],
) -> dict[str, str]:
    silver_column = row.get("Silver column", "")
    if not silver_column or silver_column in SYSTEM_FIELDS:
        return {header: row.get(header, "") for header in HEADERS_TO_UPDATE}

    contract = _resolve_runtime_contract(row, contract_index)
    if contract is not None and not contract.is_framework_field:
        filters_prefix = list(contract.silver_filter_tokens)
        validation_prefix = list(contract.silver_validation_tokens)
        normalization_prefix = list(contract.silver_normalisation_tokens)
        fail_action_prefix = list(contract.validation_fail_action_prefixes)
        fail_sink_override = contract.filter_fail_sink
        type_value = contract.logical_type
        nullable_value = str(contract.nullable).lower()
        required_value = resolve_required_display(
            row.get("Required", ""),
            optional=contract.optional,
        )
    else:
        filters_prefix = []
        validation_prefix = []
        normalization_prefix = []
        fail_action_prefix = []
        fail_sink_override = row.get(FILTER_FAIL_SINK_HEADER, "") or NOT_APPLICABLE
        type_value = row.get("Type", "")
        nullable_value = row.get("Nullable", "")
        required_value = row.get("Required", "")

    filters = _parse_tokens(
        row.get(SILVER_FILTERS_HEADER, ""),
        drop=EMPTY_SEMANTICS_TOKENS | REQUIRED_FILTER_TOKENS | STRUCTURAL_FILTER_TOKENS,
    )
    validation = _parse_tokens(
        row.get(SILVER_VALIDATION_HEADER, ""),
        drop=EMPTY_SEMANTICS_TOKENS | STRUCTURAL_VALIDATION_TOKENS,
    )
    normalization = _parse_tokens(
        row.get(SILVER_NORMALISATION_HEADER, ""),
        drop=EMPTY_SEMANTICS_TOKENS | STRUCTURAL_NORMALISATION_TOKENS,
    )
    fail_action = row.get(VALIDATION_FAIL_ACTION_HEADER, "")
    fail_sink = row.get(FILTER_FAIL_SINK_HEADER, "")
    fail_action_tokens = _parse_tokens(
        fail_action,
        drop=EMPTY_SEMANTICS_TOKENS | STRUCTURAL_ACTION_TOKENS,
    )

    filters_value = _join_tokens(filters_prefix, filters)
    validation_value = _join_tokens(validation_prefix, validation)
    normalization_value = _join_tokens(normalization_prefix, normalization)
    fail_action_value = _join_tokens(
        fail_action_prefix,
        fail_action_tokens,
        drop=EMPTY_SEMANTICS_TOKENS,
    )
    fail_sink_value = (
        fail_sink_override
        if fail_sink_override != NOT_APPLICABLE
        else (fail_sink or NOT_APPLICABLE)
    )

    return {
        "Type": type_value,
        "Nullable": nullable_value,
        "Required": required_value,
        SILVER_FILTERS_HEADER: filters_value,
        FILTER_FAIL_SINK_HEADER: fail_sink_value,
        SILVER_NORMALISATION_HEADER: normalization_value,
        SILVER_VALIDATION_HEADER: validation_value,
        VALIDATION_FAIL_ACTION_HEADER: fail_action_value,
    }


def main() -> int:
    """Main function to sync the workbook with structural policy."""
    args = _arg_parser().parse_args()
    input_path, output_path, contract_export_path = _resolve_paths(args)
    _prepare_output_directory(output_path)
    contract_rows = _load_contract_rows(args, contract_export_path)
    contract_index = index_runtime_contract_rows(contract_rows)
    temp_output_path = _determine_temp_output_path(input_path, output_path, args.check)

    change_counter = _process_workbook(input_path, temp_output_path, contract_index)

    if args.check:
        return _handle_check_mode(
            temp_output_path,
            change_counter,
            input_path,
            contract_export_path,
            contract_rows,
        )

    _finalize_output(temp_output_path, output_path)
    _print_summary(
        input_path,
        output_path,
        contract_export_path,
        contract_rows,
        change_counter,
    )
    return 0


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    """Resolve input, output, and contract export paths."""
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    contract_export_path = args.contract_export.resolve()
    return input_path, output_path, contract_export_path


def _prepare_output_directory(output_path: Path) -> None:
    """Prepare the output directory."""
    output_path.parent.mkdir(parents=True, exist_ok=True)


def _load_contract_rows(args: argparse.Namespace, contract_export_path: Path) -> list:
    """Load or refresh the contract rows."""
    if args.refresh_contract_export or not contract_export_path.exists():
        return write_runtime_contract_export(contract_export_path)
    return load_runtime_contract_export(contract_export_path)


def _determine_temp_output_path(
    input_path: Path, output_path: Path, check: bool
) -> Path:
    """Determine the temporary output path."""
    if input_path == output_path or check:
        return output_path.with_name(f".{output_path.stem}.tmp{output_path.suffix}")
    return output_path


def _process_workbook(
    input_path: Path,
    temp_output_path: Path,
    contract_index: dict[tuple[str, str, str], MatrixStructuralContractRow],
) -> Counter[str]:
    """Process the workbook and apply updates."""
    change_counter: Counter[str] = Counter()

    with zipfile.ZipFile(input_path) as zin:
        shared_strings = load_shared_strings(zin)
        sheet_targets = sheet_target_paths(zin)

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

                header_by_index, index_by_header = _extract_headers(
                    rows, shared_strings
                )

                for row in rows[1:]:
                    row_map = _build_row_map(row, header_by_index, shared_strings)
                    updated = _update_row(row_map, contract_index=contract_index)
                    _apply_updates(
                        row, updated, index_by_header, shared_strings, change_counter
                    )

                zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))

    return change_counter


def _extract_headers(
    rows: list, shared_strings: dict
) -> tuple[dict[int, str], dict[str, int]]:
    """Extract headers from the first row."""
    header_by_index: dict[int, str] = {}
    for cell in rows[0].findall("a:c", NS):
        header_by_index[column_index(cell.attrib["r"])] = cell_text(
            cell, shared_strings
        )
    index_by_header = {header: index for index, header in header_by_index.items()}
    return header_by_index, index_by_header


def _build_row_map(
    row: ET.Element, header_by_index: dict[int, str], shared_strings: dict
) -> dict[str, str]:
    """Build a map of header to cell value for a row."""
    return {
        header_by_index[column_index(cell.attrib["r"])]: cell_text(cell, shared_strings)
        for cell in row.findall("a:c", NS)
        if column_index(cell.attrib["r"]) in header_by_index
    }


def _apply_updates(
    row: ET.Element,
    updated: dict[str, str],
    index_by_header: dict[str, int],
    shared_strings: dict,
    change_counter: Counter[str],
) -> None:
    """Apply updates to the row cells."""
    for header, new_value in updated.items():
        index = index_by_header.get(header)
        if index is None:
            continue
        target_cell = None
        for cell in row.findall("a:c", NS):
            if column_index(cell.attrib["r"]) == index:
                target_cell = cell
                break
        if target_cell is None:
            continue
        raw_value = cell_text(target_cell, shared_strings)
        if raw_value == new_value:
            continue
        set_cell_text(target_cell, new_value)
        change_counter[header] += 1


def _handle_check_mode(
    temp_output_path: Path,
    change_counter: Counter[str],
    input_path: Path,
    contract_export_path: Path,
    contract_rows: list,
) -> int:
    """Handle check mode by printing changes and exiting."""
    if temp_output_path.exists():
        temp_output_path.unlink()
    payload = {
        "input": str(input_path),
        "contract_export": str(contract_export_path),
        "contract_rows": len(contract_rows),
        "updated_headers": dict(change_counter),
    }
    print(payload)
    return 1 if change_counter else 0


def _finalize_output(temp_output_path: Path, output_path: Path) -> None:
    """Finalize the output by moving the temp file to the output path."""
    if temp_output_path != output_path:
        temp_output_path.replace(output_path)


def _print_summary(
    input_path: Path,
    output_path: Path,
    contract_export_path: Path,
    contract_rows: list,
    change_counter: Counter[str],
) -> None:
    """Print a summary of the changes."""
    print(
        {
            "input": str(input_path),
            "output": str(output_path),
            "contract_export": str(contract_export_path),
            "contract_rows": len(contract_rows),
            "updated_headers": dict(change_counter),
        }
    )


if __name__ == "__main__":
    raise SystemExit(main())
