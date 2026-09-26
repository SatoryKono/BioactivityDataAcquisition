"""Shared low-level helpers for workbook-oriented docs tooling."""

from __future__ import annotations

import re
import zipfile
from typing import Final
from urllib.parse import urlunsplit
from xml.etree import ElementTree as ET

_OOXML_HOST = "schemas.openxmlformats.org"
NS: Final[dict[str, str]] = {
    "a": urlunsplit(("http", _OOXML_HOST, "/spreadsheetml/2006/main", "", "")),
    "r": urlunsplit(
        ("http", _OOXML_HOST, "/officeDocument/2006/relationships", "", "")
    ),
    "pr": urlunsplit(("http", _OOXML_HOST, "/package/2006/relationships", "", "")),
}
MAIN_NS: Final[str] = NS["a"]
REL_NS: Final[str] = NS["r"]
COL_RE: Final[re.Pattern[str]] = re.compile(r"[A-Z]+")


def column_index(cell_ref: str) -> int:
    """Convert an XLSX cell reference like AB12 to a 1-based column index."""
    letters = "".join(COL_RE.findall(cell_ref))
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value


def column_letters(index: int) -> str:
    """Convert a 1-based column index to XLSX column letters."""
    letters = ""
    value = index
    while value:
        value, remainder = divmod(value - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def load_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """Load workbook shared strings, if present."""
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return ["".join(node.itertext()) for node in root.findall("a:si", NS)]


def cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    """Read a cell value as plain text."""
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


def set_cell_text(cell: ET.Element, value: str) -> None:
    """Replace a cell payload with inline string content."""
    for child in tuple(cell):
        if child.tag in {f"{{{MAIN_NS}}}v", f"{{{MAIN_NS}}}is"}:
            cell.remove(child)
    cell.set("t", "inlineStr")
    is_node = ET.Element(f"{{{MAIN_NS}}}is")
    text_node = ET.SubElement(is_node, f"{{{MAIN_NS}}}t")
    if value.startswith(" ") or value.endswith(" "):
        text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = value
    cell.append(is_node)


def iter_sheet_targets(archive: zipfile.ZipFile) -> list[tuple[str, str]]:
    """Return workbook sheet targets as (sheet_name, archive_path)."""
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_map = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("pr:Relationship", NS)
    }
    sheets = workbook.find("a:sheets", NS)
    if sheets is None:
        return []
    targets: list[tuple[str, str]] = []
    for sheet in sheets.findall("a:sheet", NS):
        rel_id = sheet.attrib[f"{{{REL_NS}}}id"]
        targets.append((sheet.attrib["name"], "xl/" + rel_map[rel_id].lstrip("/")))
    return targets


def sheet_target_paths(archive: zipfile.ZipFile) -> set[str]:
    """Return workbook sheet archive paths."""
    return {target for _, target in iter_sheet_targets(archive)}


def sheet_target_name_map(archive: zipfile.ZipFile) -> dict[str, str]:
    """Return workbook sheet archive paths keyed to sheet names."""
    return {target: name for name, target in iter_sheet_targets(archive)}


def update_dimension(root: ET.Element, row_count: int, max_col_index: int) -> None:
    """Update an XLSX sheet dimension to match the current row count."""
    dimension = root.find("a:dimension", NS)
    if dimension is None:
        return
    max_col = column_letters(max_col_index)
    dimension.set("ref", f"A1:{max_col}{row_count}")
