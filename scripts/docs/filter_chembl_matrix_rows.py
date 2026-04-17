#!/usr/bin/env python3
"""Filter rows from ChEMBL matrix workbooks by column value."""

from __future__ import annotations

import argparse
import copy
import sys
import zipfile
from pathlib import Path
from typing import Final
from xml.etree import ElementTree as ET

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.docs.common.xlsx import (
    NS,
    cell_text,
    column_index,
    column_letters,
    load_shared_strings,
    sheet_target_paths,
    update_dimension,
)

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DEFAULT_INPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
DEFAULT_OUTPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Remove workbook rows matching a value in specified columns."
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_INPUT, help="Input workbook."
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="Output workbook."
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        default=["Source Kind", "Source_Field_Type", "Source_Field_Nullable"],
        help="Headers to inspect.",
    )
    parser.add_argument(
        "--value",
        default="not_mapped",
        help="Value that triggers row removal.",
    )
    return parser


def _rewrite_row_refs(row: ET.Element, new_row_number: int) -> None:
    row.set("r", str(new_row_number))
    for cell in row.findall("a:c", NS):
        col_idx = column_index(cell.attrib["r"])
        cell.set("r", f"{column_letters(col_idx)}{new_row_number}")


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
                sheet_data = root.find("a:sheetData", NS)
                rows = sheet_data.findall("a:row", NS)
                if not rows:
                    zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))
                    continue

                header_map = {
                    column_index(cell.attrib["r"]): cell_text(cell, shared_strings)
                    for cell in rows[0].findall("a:c", NS)
                }
                max_col_index = max(header_map)
                kept_rows = [rows[0]]

                for row in rows[1:]:
                    row_map = {
                        header_map[column_index(cell.attrib["r"])]: cell_text(
                            cell, shared_strings
                        )
                        for cell in row.findall("a:c", NS)
                        if column_index(cell.attrib["r"]) in header_map
                    }
                    if any(
                        row_map.get(column) == args.value for column in args.columns
                    ):
                        continue
                    kept_rows.append(row)

                for row in list(sheet_data):
                    sheet_data.remove(row)

                for idx, row in enumerate(kept_rows, start=1):
                    _rewrite_row_refs(row, idx)
                    sheet_data.append(row)

                update_dimension(root, len(kept_rows), max_col_index)
                zout.writestr(copy.copy(info), ET.tostring(root, encoding="utf-8"))

    if temp_output_path != output_path:
        temp_output_path.replace(output_path)

    print(
        {
            "input": str(input_path),
            "output": str(output_path),
            "filtered_value": args.value,
            "columns": args.columns,
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
