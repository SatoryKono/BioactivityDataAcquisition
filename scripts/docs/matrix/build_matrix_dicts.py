#!/usr/bin/env python3
"""Generate value inventory and sheet-level dictionaries for ChEMBL matrix workbooks."""

from __future__ import annotations

import argparse
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
    from scripts.docs.matrix._bootstrap import PROJECT_ROOT, ensure_repo_imports
else:
    from scripts.docs.matrix._bootstrap import PROJECT_ROOT, ensure_repo_imports

ensure_repo_imports()

from scripts.docs.common.xlsx import (  # noqa: E402
    NS,
    cell_text,
    column_index,
    iter_sheet_targets,
    load_shared_strings,
)

DEFAULT_WORKBOOK: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
DEFAULT_OUTPUT_DIR: Final[Path] = PROJECT_ROOT / "docs/reports/dictionaries"
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
    "Silver Normalisation Detail",
    "Silver Normalisation Detail ID",
)
DETAIL_COLUMN: Final[str] = "Silver Normalisation Detail"
DETAIL_ID_COLUMN: Final[str] = "Silver Normalisation Detail ID"
COMPLEX_REVIEW_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "Silver Filters",
        "Silver Validation",
        "Source_Field_Validation",
        "Validation fail action",
    }
)
JSON_OBJECT_TYPE: Final[str] = "json/object"
JSON_ARRAY_TYPE: Final[str] = "json/array"
TYPE_CANONICAL: Final[dict[str, str]] = {
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
}
NULLABLE_CANONICAL: Final[dict[str, str]] = {
    "false": "false",
    "true": "true",
    "conditional": "conditional",
    "derived": "derived",
    "runtime-managed": "runtime-managed",
    "runtime_managed": "runtime-managed",
    "not_mapped": "not_mapped",
    "unknown": "unknown",
}


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate per-sheet value inventory and sheet dictionaries for "
            "chembl pipeline matrix workbooks."
        )
    )
    parser.add_argument(
        "--workbook",
        type=Path,
        default=DEFAULT_WORKBOOK,
        help="Input workbook path.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated YAML artifacts.",
    )
    return parser


def _read_workbook(path: Path) -> dict[str, list[dict[str, str]]]:
    with zipfile.ZipFile(path) as archive:
        shared_strings = load_shared_strings(archive)
        workbook_rows: dict[str, list[dict[str, str]]] = {}
        for sheet_name, target in iter_sheet_targets(archive):
            root = ET.fromstring(archive.read(target))
            rows = root.find("a:sheetData", NS).findall("a:row", NS)
            if not rows:
                workbook_rows[sheet_name] = []
                continue

            header_map = {
                column_index(cell.attrib["r"]): cell_text(cell, shared_strings)
                for cell in rows[0].findall("a:c", NS)
            }
            ordered_indexes = sorted(header_map)
            headers = [header_map[index] for index in ordered_indexes]

            data_rows: list[dict[str, str]] = []
            for row in rows[1:]:
                row_map = {
                    column_index(cell.attrib["r"]): cell_text(cell, shared_strings)
                    for cell in row.findall("a:c", NS)
                }
                data_rows.append(
                    {
                        header: row_map.get(index, "")
                        for index, header in zip(ordered_indexes, headers, strict=True)
                    }
                )
            workbook_rows[sheet_name] = data_rows
    return workbook_rows


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.strip().split())


def _normalize_semicolons(value: str) -> str:
    parts = [part.strip() for part in value.split(";")]
    return "; ".join(part for part in parts if part)


def _canonical_required(value: str) -> tuple[str, str]:
    lowered = _normalize_whitespace(value).lower()
    if not lowered:
        return "optional", "blank_to_optional"
    if lowered == "optional":
        return "optional", "identity"

    tokens = [token.strip() for token in lowered.split(",") if token.strip()]
    ordered = [label for label in ("runtime", "filters", "schema") if label in tokens]
    if ordered and len(ordered) == len(tokens):
        return ", ".join(ordered), "ordered_required_labels"
    return lowered, "whitespace_normalized"


def _propose_value(column: str, raw_value: str) -> tuple[str, str, str]:
    normalized = _normalize_whitespace(raw_value)
    if not normalized:
        return "", "blank", "auto"

    lowered = normalized.lower()
    if column in {"Source_Field_Type", "Type"}:
        return TYPE_CANONICAL.get(lowered, lowered), "type_canonical", "auto"
    if column in {"Source_Field_Nullable", "Nullable"}:
        return NULLABLE_CANONICAL.get(lowered, lowered), "nullable_canonical", "auto"
    if column == "Required":
        canonical, rule = _canonical_required(normalized)
        return canonical, rule, "auto"

    semicolon_normalized = _normalize_semicolons(normalized)
    rule = "semicolon_spacing" if semicolon_normalized != raw_value else "identity"
    review_status = "needs_review" if column in COMPLEX_REVIEW_COLUMNS else "auto"
    return semicolon_normalized, rule, review_status


def _inventory_for_rows(rows: list[dict[str, str]]) -> dict[str, object]:
    columns: dict[str, object] = {}
    for column in TARGET_COLUMNS:
        counter = Counter(row.get(column, "") for row in rows)
        columns[column] = {
            "unique_count": len(counter),
            "blank_count": counter.get("", 0),
            "values": [
                {"raw_value": value, "occurrence_count": count}
                for value, count in sorted(
                    counter.items(), key=lambda item: (-item[1], item[0])
                )
            ],
        }
    return columns


def _sheet_dictionary(rows: list[dict[str, str]]) -> dict[str, object]:
    dictionary: dict[str, object] = {}
    for column in TARGET_COLUMNS:
        counter = Counter(row.get(column, "") for row in rows)
        entries = []
        for raw_value, occurrence_count in sorted(
            counter.items(), key=lambda item: (-item[1], item[0])
        ):
            proposed_canonical_value, normalization_rule, review_status = (
                _propose_value(column, raw_value)
            )
            entries.append(
                {
                    "raw_value": raw_value,
                    "occurrence_count": occurrence_count,
                    "proposed_canonical_value": proposed_canonical_value,
                    "normalization_rule": normalization_rule,
                    "review_status": review_status,
                }
            )
        dictionary[column] = {"dictionary_entries": entries}
    return dictionary


def _global_inventory(
    workbook_rows: dict[str, list[dict[str, str]]],
) -> dict[str, object]:
    columns: dict[str, object] = {}
    for column in TARGET_COLUMNS:
        counter: Counter[str] = Counter()
        for rows in workbook_rows.values():
            counter.update(row.get(column, "") for row in rows)
        columns[column] = {
            "unique_count": len(counter),
            "values": [
                {"raw_value": value, "occurrence_count": count}
                for value, count in sorted(
                    counter.items(), key=lambda item: (-item[1], item[0])
                )
            ],
        }
    return columns


def _column_dictionary(
    workbook_rows: dict[str, list[dict[str, str]]],
) -> tuple[dict[str, object], dict[str, object]]:
    """Build column dictionaries and review queue."""
    dictionaries: dict[str, object] = {}
    review_queue: dict[str, object] = {}

    for column in TARGET_COLUMNS:
        global_counter, sheet_occurrences = _collect_column_data(workbook_rows, column)
        dictionary_entries, review_entries = _build_column_entries(
            column, global_counter, sheet_occurrences
        )
        dictionaries[column] = {"dictionary_entries": dictionary_entries}
        review_queue[column] = {
            "needs_review_count": len(review_entries),
            "review_entries": review_entries,
        }

    return dictionaries, review_queue


def _base_payload(generated_at: str, workbook: Path) -> dict[str, object]:
    return {
        "generated_at_utc": generated_at,
        "source_workbook": str(workbook),
        "target_columns": list(TARGET_COLUMNS),
    }


def _output_paths(output_dir: Path, stem: str) -> dict[str, Path]:
    return {
        "inventory": output_dir / f"{stem}_value_inventory.yaml",
        "sheet_dictionaries": output_dir / f"{stem}_sheet_dictionaries.yaml",
        "column_dictionaries": output_dir / f"{stem}_column_dictionaries.yaml",
        "review_queue": output_dir / f"{stem}_dictionary_review_queue.yaml",
        "detail_id_dictionary": output_dir / f"{stem}_normalisation_detail_ids.yaml",
    }


def _collect_column_data(
    workbook_rows: dict[str, list[dict[str, str]]],
    column: str,
) -> tuple[Counter[str], dict[str, list[dict[str, object]]]]:
    """Collect data for a column across all sheets."""
    global_counter: Counter[str] = Counter()
    sheet_occurrences: dict[str, list[dict[str, object]]] = {}
    for sheet_name, rows in workbook_rows.items():
        counter = Counter(row.get(column, "") for row in rows)
        global_counter.update(counter)
        sheet_occurrences[sheet_name] = [
            {"raw_value": raw_value, "occurrence_count": occurrence_count}
            for raw_value, occurrence_count in sorted(
                counter.items(), key=lambda item: (-item[1], item[0])
            )
        ]
    return global_counter, sheet_occurrences


def _build_column_entries(
    column: str,
    global_counter: Counter[str],
    sheet_occurrences: dict[str, list[dict[str, object]]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Build dictionary and review entries for a column."""
    dictionary_entries = []
    review_entries = []
    for raw_value, occurrence_count in sorted(
        global_counter.items(), key=lambda item: (-item[1], item[0])
    ):
        proposed_canonical_value, normalization_rule, review_status = _propose_value(
            column, raw_value
        )
        entry = {
            "raw_value": raw_value,
            "occurrence_count": occurrence_count,
            "proposed_canonical_value": proposed_canonical_value,
            "normalization_rule": normalization_rule,
            "review_status": review_status,
            "sheets": _build_sheet_occurrences(sheet_occurrences, raw_value),
        }
        dictionary_entries.append(entry)
        if review_status != "auto":
            review_entries.append(entry)
    return dictionary_entries, review_entries


def _build_sheet_occurrences(
    sheet_occurrences: dict[str, list[dict[str, object]]],
    raw_value: str,
) -> list[dict[str, object]]:
    """Build sheet occurrences for a raw value."""
    return [
        {
            "sheet_name": sheet_name,
            "occurrence_count": next(
                (
                    item["occurrence_count"]
                    for item in occurrences
                    if item["raw_value"] == raw_value
                ),
                0,
            ),
        }
        for sheet_name, occurrences in sheet_occurrences.items()
        if any(item["raw_value"] == raw_value for item in occurrences)
    ]


def _iter_detail_id_pairs(
    workbook_rows: dict[str, list[dict[str, str]]],
) -> list[tuple[int, str]]:
    pairs: list[tuple[int, str]] = []
    for rows in workbook_rows.values():
        for row in rows:
            detail = row.get(DETAIL_COLUMN, "")
            raw_id = row.get(DETAIL_ID_COLUMN, "")
            if not detail or not raw_id:
                continue
            try:
                detail_id = int(raw_id)
            except ValueError:
                continue
            pairs.append((detail_id, detail))
    return pairs


def _raise_conflicting_detail_text(
    detail_id: int,
    existing_detail: str,
    detail: str,
) -> None:
    raise ValueError(
        f"Conflicting detail text for ID {detail_id}: {existing_detail!r} != {detail!r}"
    )


def _raise_conflicting_detail_id(
    detail: str,
    existing_id: int,
    detail_id: int,
) -> None:
    raise ValueError(
        f"Conflicting detail ID for {detail!r}: {existing_id} != {detail_id}"
    )


def _merge_detail_id_pair(
    pairs: dict[int, str],
    detail_to_id: dict[str, int],
    detail_id: int,
    detail: str,
) -> None:
    existing_detail = pairs.get(detail_id)
    if existing_detail is not None and existing_detail != detail:
        _raise_conflicting_detail_text(detail_id, existing_detail, detail)

    existing_id = detail_to_id.get(detail)
    if existing_id is not None and existing_id != detail_id:
        _raise_conflicting_detail_id(detail, existing_id, detail_id)

    pairs[detail_id] = detail
    detail_to_id[detail] = detail_id


def _detail_id_entries(pairs: dict[int, str]) -> list[dict[str, object]]:
    return [
        {"id": detail_id, "detail": detail}
        for detail_id, detail in sorted(pairs.items())
    ]


def _detail_id_dictionary(
    workbook_rows: dict[str, list[dict[str, str]]],
) -> dict[str, object]:
    """Build workbook-global mapping from detail IDs to detail strings."""
    pairs: dict[int, str] = {}
    detail_to_id: dict[str, int] = {}

    for detail_id, detail in _iter_detail_id_pairs(workbook_rows):
        _merge_detail_id_pair(pairs, detail_to_id, detail_id, detail)

    entries = _detail_id_entries(pairs)
    return {
        "unique_detail_count": len(entries),
        "entries": entries,
    }


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _inventory_payload(
    generated_at: str,
    workbook: Path,
    workbook_rows: dict[str, list[dict[str, str]]],
) -> dict[str, object]:
    return {
        **_base_payload(generated_at, workbook),
        "sheets": {
            sheet_name: {
                "row_count": len(rows),
                "columns": _inventory_for_rows(rows),
            }
            for sheet_name, rows in workbook_rows.items()
        },
        "global_columns": _global_inventory(workbook_rows),
    }


def _sheet_dictionary_payload(
    generated_at: str,
    workbook: Path,
    workbook_rows: dict[str, list[dict[str, str]]],
) -> dict[str, object]:
    return {
        **_base_payload(generated_at, workbook),
        "sheets": {
            sheet_name: _sheet_dictionary(rows)
            for sheet_name, rows in workbook_rows.items()
        },
    }


def _detail_id_payload(
    generated_at: str,
    workbook: Path,
    detail_id_dictionary: dict[str, object],
) -> dict[str, object]:
    return {
        **_base_payload(generated_at, workbook),
        "detail_column": DETAIL_COLUMN,
        "detail_id_column": DETAIL_ID_COLUMN,
        **detail_id_dictionary,
    }


def main() -> int:
    args = _arg_parser().parse_args()
    workbook = args.workbook.resolve()
    output_dir = args.output_dir.resolve()
    workbook_rows = _read_workbook(workbook)
    generated_at = datetime.now(UTC).isoformat()
    column_dictionaries, review_queue = _column_dictionary(workbook_rows)
    detail_id_dictionary = _detail_id_dictionary(workbook_rows)
    base_payload = _base_payload(generated_at, workbook)
    output_paths = _output_paths(output_dir, workbook.stem)

    _write_yaml(
        output_paths["inventory"],
        _inventory_payload(generated_at, workbook, workbook_rows),
    )
    _write_yaml(
        output_paths["sheet_dictionaries"],
        _sheet_dictionary_payload(generated_at, workbook, workbook_rows),
    )
    _write_yaml(
        output_paths["column_dictionaries"],
        {**base_payload, "columns": column_dictionaries},
    )
    _write_yaml(
        output_paths["review_queue"],
        {**base_payload, "columns": review_queue},
    )
    _write_yaml(
        output_paths["detail_id_dictionary"],
        _detail_id_payload(generated_at, workbook, detail_id_dictionary),
    )

    print(
        {
            **{name: str(path) for name, path in output_paths.items()},
            "sheet_count": len(workbook_rows),
            "target_columns": len(TARGET_COLUMNS),
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
