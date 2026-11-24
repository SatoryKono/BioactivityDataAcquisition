"""Parsers for the post-join target classification whitelist."""

from __future__ import annotations

import hashlib
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
    """Return a stripped string, or none for a blank or non-string value."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def put_value(business: JsonDict, key: str, value: object) -> None:
    """Store a present whitelist value."""
    if value is not None:
        business[key] = value


def sha256_text(value: object) -> str | None:
    """Return a lowercase SHA-256 hex digest."""
    text = text_value(value)
    if text is None or _SHA256.fullmatch(text) is None:
        return None
    return text


def first_present(
    row: Mapping[str, object], columns: Sequence[str]
) -> tuple[str | None, object]:
    """Return the first populated column and its value."""
    for column in columns:
        if column not in row:
            continue
        value = row.get(column)
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        return column, value
    return None, None


def first_ec(
    row: Mapping[str, object], columns: Sequence[str]
) -> tuple[str | None, object]:
    """Skip empty token sequences and preserve the selected source value."""
    for column in columns:
        value = row.get(column)
        if _has_ec_tokens(value):
            return column, value
    return None, None


def _has_ec_tokens(value: object) -> bool:
    if isinstance(value, (list, tuple)):
        return any(_has_ec_tokens(item) for item in value)
    if not isinstance(value, str):
        return False
    if value.lstrip().startswith("["):
        return _has_ec_tokens(_json_items(value))
    return any(text_value(item) not in (None, "unknown") for item in _json_items(value))


def first_text(
    row: Mapping[str, object], columns: Sequence[str]
) -> tuple[str | None, str | None]:
    """Return the first populated text column."""
    column, value = first_present(row, columns)
    return column, text_value(value)


def controlled_keyword_ids(value: object) -> tuple[str, ...]:
    """Keep keyword tokens that match the controlled-id pattern."""
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
    """Classify keywords as present, absent, or uncontrolled."""
    if keyword_ids:
        return "present"
    if value is None:
        return "absent"
    return "uncontrolled_ignored"


def hierarchy_levels(
    row: Mapping[str, object],
) -> tuple[list[dict[str, object]], tuple[str, ...]]:
    """Read present levels and the exact columns used to build them."""
    levels: list[dict[str, object]] = []
    columns: list[str] = []
    for level in _HIERARCHY_LEVELS:
        entry, level_columns = _hierarchy_level(row, level)
        if level_columns:
            levels.append(entry)
            columns.extend(level_columns)
    return levels, tuple(columns)


def source_hashes(
    frames: Mapping[str, pl.DataFrame] | None,
) -> dict[tuple[str, str], str]:
    """Index dependency content hashes by pipeline and business key."""
    if not frames:
        return {}
    index: dict[tuple[str, str], str] = {}
    for pipeline in sorted(frames):
        _index_frame(index, pipeline, frames[pipeline])
    return index


def _hierarchy_level(
    row: Mapping[str, object], level: int
) -> tuple[dict[str, object], list[str]]:
    entry: dict[str, object] = {"level": level}
    columns: list[str] = []
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
        columns.append(column or qualified)
    entry["equivalent_to_historical_m_column"] = False
    return entry, columns


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
    digests_by_key: dict[str, set[str]] = {}
    for row in frame.iter_rows(named=True):
        key = text_value(row.get(key_field))
        digest = sha256_text(row.get("content_hash"))
        if key is not None and digest is not None:
            digests_by_key.setdefault(key, set()).add(digest)
    for key, digests in digests_by_key.items():
        ordered = sorted(digests)
        index[(pipeline, key)] = (
            ordered[0]
            if len(ordered) == 1
            else hashlib.sha256("".join(ordered).encode("ascii")).hexdigest()
        )


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
