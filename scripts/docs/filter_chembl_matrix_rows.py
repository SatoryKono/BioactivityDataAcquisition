#!/usr/bin/env python3
"""Filter rows from ChEMBL matrix workbooks by column value."""

from __future__ import annotations

import argparse
import copy
import re
import zipfile
from pathlib import Path
from typing import Final
from xml.etree import ElementTree as ET

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
DEFAULT_INPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
DEFAULT_OUTPUT: Final[Path] = (
    PROJECT_ROOT / "docs/reports/chembl_pipeline_silver_matrices_v12.xlsx"
)
NS: Final[dict[str, str]] = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}
MAIN_NS: Final[str] = NS["a"]
REL_NS: Final[str] = NS["r"]
COL_RE: Final[re.Pattern[str]] = re.compile(r"[A-Z]+")


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


def _column_index(cell_ref: str) -> int:
    letters = "".join(COL_RE.findall(cell_ref))
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value


def _column_letters(index: int) -> str:
    letters = ""
    value = index
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.itertext()) for node in root.findall("a:si", NS)]


def _sheet_targets(archive: zipfile.ZipFile) -> set[str]:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("pr:Relationship", NS)
    }
    targets: set[str] = set()
    for sheet in workbook.find("a:sheets", NS).findall("a:sheet", NS):
        rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
        targets.add("xl/" + rel_map[rel_id].lstrip("/"))
    return targets


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find("a:is", NS)
        return "".join(inline.itertext()) if inline is not None else ""
    value_node = cell.find("a:v", NS)
    if value_node is None:
        return ""
    value = value_node.text or ""
    if cell_type == "s":
        return shared_strings[int(value)]
    return value


def _rewrite_row_refs(row: ET.Element, new_row_number: int) -> None:
    row.set("r", str(new_row_number))
    for cell in row.findall("a:c", NS):
        col_idx = _column_index(cell.attrib["r"])
        cell.set("r", f"{_column_letters(col_idx)}{new_row_number}")


def _update_dimension(root: ET.Element, row_count: int, max_col_index: int) -> None:
    dimension = root.find("a:dimension", NS)
    if dimension is None:
        return
    max_col = _column_letters(max_col_index)
    dimension.set("ref", f"A1:{max_col}{row_count}")


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
        shared_strings = _load_shared_strings(zin)
        sheet_targets = _sheet_targets(zin)

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
                    _column_index(cell.attrib["r"]): _cell_text(cell, shared_strings)
                    for cell in rows[0].findall("a:c", NS)
                }
                max_col_index = max(header_map)
                kept_rows = [rows[0]]

                for row in rows[1:]:
                    row_map = {
                        header_map[_column_index(cell.attrib["r"])]: _cell_text(
                            cell, shared_strings
                        )
                        for cell in row.findall("a:c", NS)
                        if _column_index(cell.attrib["r"]) in header_map
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

                _update_dimension(root, len(kept_rows), max_col_index)
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
