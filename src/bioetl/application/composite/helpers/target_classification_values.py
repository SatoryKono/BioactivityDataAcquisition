"""Parsers for the post-join target classification whitelist."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from typing import Final

import polars as pl

from bioetl.domain.types import JsonDict

_KEYWORD_ID: Final = re.compile(r"^(?:KW-\d+|\d+)$")
_SHA256: Final = re.compile(r"^[0-9a-f]{64}$")
_HIERARCHY_PARTS: Final = ("id", "name", "desc")
_HIERARCHY_LEVELS: Final = (1, 2, 3, 4, 5)


def text_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def put_value(business: JsonDict, key: str, value: object) -> None:
    if value is not None:
        business[key] = value


def sha256_text(value: object) -> str | None:
    text = text_value(value)
    if text is None or _SHA256.fullmatch(text) is None:
        return None
    return text


def first_present(
    row: Mapping[str, object], columns: Sequence[str]
) -> tuple[str | None, object]:
    for column in columns:
        if column not in row:
            continue
        value = row.get(column)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        return column, value
    return None, None


def first_text(
    row: Mapping[str, object], columns: Sequence[str]
) -> tuple[str | None, str | None]:
    column, value = first_present(row, columns)
    return column, text_value(value)


def controlled_keyword_ids(value: object) -> tuple[str, ...]:
    found: list[str] = []
    for item in _json_items(value):
        raw = item.get("id") if isinstance(item, dict) else item
        if not isinstance(raw, str):
            continue
        token = raw.strip()
        if _KEYWORD_ID.fullmatch(token) and token not in found:
            found.append(token)
    return tuple(found)


def keyword_status(value: object, keyword_ids: tuple[str, ...]) -> str:
    if keyword_ids:
        return "present"
    if value is None:
        return "absent"
    return "uncontrolled_ignored"


def hierarchy_levels(row: Mapping[str, object]) -> list[dict[str, object]]:
    return [
        entry
        for level in _HIERARCHY_LEVELS
        if (entry := _hierarchy_level(row, level)) is not None
    ]


def source_hashes(
    frames: Mapping[str, pl.DataFrame] | None,
) -> dict[tuple[str, str], str]:
    if not frames:
        return {}
    index: dict[tuple[str, str], str] = {}
    for pipeline in sorted(frames):
        _index_frame(index, pipeline, frames[pipeline])
    return index


def _hierarchy_level(row: Mapping[str, object], level: int) -> dict[str, object] | None:
    entry: dict[str, object] = {"level": level}
    found = False
    for part in _HIERARCHY_PARTS:
        qualified = (
            f"chembl.target_protein_classification.target_protein_class_{part}_L{level}"
        )
        column, value = first_text(
            row, (qualified, f"target_protein_class_{part}_L{level}")
        )
        if value is None:
            continue
        entry[part] = value
        entry["qualified_column"] = column or qualified
        found = True
    if not found:
        return None
    entry["equivalent_to_historical_m_column"] = False
    return entry


def _index_frame(
    index: dict[tuple[str, str], str], pipeline: str, frame: pl.DataFrame
) -> None:
    if "content_hash" not in frame.columns:
        return
    key_field = next(
        (
            name
            for name in ("target_id", "uniprot_accession", "accession")
            if name in frame.columns
        ),
        None,
    )
    if key_field is None:
        return
    for row in frame.iter_rows(named=True):
        key = text_value(row.get(key_field))
        digest = sha256_text(row.get("content_hash"))
        if key is not None and digest is not None:
            index[(pipeline, key)] = digest


def _json_items(value: object) -> tuple[object, ...]:
    if value is None or isinstance(value, (list, tuple)):
        return tuple(value or ())
    if not isinstance(value, str):
        return ()
    text = value.strip()
    if not text:
        return ()
    if text.startswith("["):
        return _json_array(text)
    return tuple(part.strip() for part in re.split(r"[|;]", text) if part.strip())


def _json_array(text: str) -> tuple[object, ...]:
    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        return ()
    if isinstance(loaded, list):
        return tuple(loaded)
    return ()
