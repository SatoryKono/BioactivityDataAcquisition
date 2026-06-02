"""Shared target protein-classification summary policy for ChEMBL surfaces."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Final

import polars as pl

__all__ = [
    "MULTIFUNCTIONAL_TARGET_NAME",
    "TARGET_PROTEIN_CLASSIFICATION_PIPELINE",
    "empty_target_protein_classification_summary",
    "summarize_target_protein_classification_dependency",
    "summarize_target_protein_classification_rows",
]

TARGET_PROTEIN_CLASSIFICATION_PIPELINE: Final = "chembl_target_protein_classification"
MULTIFUNCTIONAL_TARGET_NAME: Final = "Multifunctional target"
_RESOLVED_STATUS: Final = "resolved"
_LEVELS: Final = (1, 2, 3, 4, 5)

_SUMMARY_SCHEMA: Final[dict[str, pl.DataType]] = {
    "target_id": pl.Utf8,
    "protein_classifications": pl.Utf8,
    **{f"target_protein_class_id_L{level}": pl.Utf8 for level in _LEVELS},
    **{f"target_protein_class_name_L{level}": pl.Utf8 for level in _LEVELS},
    **{f"target_protein_class_desc_L{level}": pl.Utf8 for level in _LEVELS},
}


def summarize_target_protein_classification_dependency(
    df: pl.DataFrame,
) -> pl.DataFrame:
    """Collapse target-classification relation rows to one deterministic target row."""
    if "target_id" not in df.columns:
        return df
    if df.is_empty():
        return pl.DataFrame(schema=_SUMMARY_SCHEMA)

    rows_by_target: dict[str, list[dict[str, object]]] = {}
    for row in df.to_dicts():
        target_id = _text_or_none(row.get("target_id"))
        if target_id is None:
            continue
        rows_by_target.setdefault(target_id, []).append(row)

    summary_rows = [
        summarize_target_protein_classification_rows(target_id, rows)
        for target_id, rows in sorted(rows_by_target.items())
    ]
    return pl.DataFrame(summary_rows, schema=_SUMMARY_SCHEMA)


def summarize_target_protein_classification_rows(
    target_id: str,
    rows: Iterable[Mapping[str, object]],
) -> dict[str, object]:
    """Summarize relation-like classification rows for one target."""
    summary = empty_target_protein_classification_summary(target_id)
    resolved_rows = _deduplicate_resolved_rows([dict(row) for row in rows])
    if not resolved_rows:
        return summary

    summary["protein_classifications"] = _serialize_classifications(resolved_rows)
    if len(resolved_rows) == 1:
        _copy_single_hierarchy(summary, resolved_rows[0])
        return summary

    _mark_multifunctional(summary)
    return summary


def empty_target_protein_classification_summary(target_id: str) -> dict[str, object]:
    """Return an all-null target protein-classification summary row."""
    row: dict[str, object] = {
        column: None for column in _SUMMARY_SCHEMA if column != "target_id"
    }
    row["target_id"] = target_id
    return row


def _deduplicate_resolved_rows(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    deduped: dict[int, dict[str, object]] = {}
    for row in sorted(rows, key=_classification_sort_key):
        if not _is_resolved(row):
            continue
        leaf_id = _positive_int_or_none(row.get("leaf_id"))
        if leaf_id is None:
            continue
        deduped.setdefault(leaf_id, row)
    return [deduped[leaf_id] for leaf_id in sorted(deduped)]


def _classification_sort_key(row: Mapping[str, object]) -> tuple[int, int, int]:
    leaf_id = _positive_int_or_none(row.get("leaf_id"))
    component_id = _positive_int_or_none(row.get("component_id"))
    return (
        leaf_id if leaf_id is not None else 10**12,
        component_id if component_id is not None else 10**12,
        0 if _is_resolved(row) else 1,
    )


def _is_resolved(row: Mapping[str, object]) -> bool:
    raw_status = row.get("classification_status")
    if raw_status is None:
        return True
    return str(raw_status).strip() == _RESOLVED_STATUS


def _copy_single_hierarchy(
    summary: dict[str, object],
    row: Mapping[str, object],
) -> None:
    for level in _LEVELS:
        summary[f"target_protein_class_id_L{level}"] = _id_text_or_none(
            row.get(f"l{level}_id")
        )
        summary[f"target_protein_class_name_L{level}"] = _text_or_none(
            row.get(f"l{level}_name")
        )
        summary[f"target_protein_class_desc_L{level}"] = _text_or_none(
            row.get(f"l{level}_desc")
        )


def _mark_multifunctional(summary: dict[str, object]) -> None:
    summary["target_protein_class_name_L1"] = MULTIFUNCTIONAL_TARGET_NAME
    summary["target_protein_class_name_L2"] = MULTIFUNCTIONAL_TARGET_NAME
    for level in (3, 4, 5):
        summary[f"target_protein_class_name_L{level}"] = ""


def _serialize_classifications(rows: list[dict[str, object]]) -> str:
    payload = [_classification_payload(row) for row in rows]
    return json.dumps(payload, sort_keys=False, separators=(",", ":"))


def _classification_payload(row: Mapping[str, object]) -> dict[str, object]:
    payload: dict[str, object] = {
        "component_id": _positive_int_or_none(row.get("component_id")),
        "leaf_id": _positive_int_or_none(row.get("leaf_id")),
        "classification_status": _RESOLVED_STATUS,
    }
    for level in _LEVELS:
        payload[f"l{level}_id"] = _positive_int_or_none(row.get(f"l{level}_id"))
        payload[f"l{level}_name"] = _text_or_none(row.get(f"l{level}_name"))
        payload[f"l{level}_desc"] = _text_or_none(row.get(f"l{level}_desc"))
    return payload


def _id_text_or_none(value: object) -> str | None:
    normalized = _positive_int_or_none(value)
    if normalized is not None:
        return str(normalized)
    return _text_or_none(value)


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _positive_int_or_none(value: object) -> int | None:
    normalized = _int_or_none(value)
    if normalized is None:
        return None
    return normalized if normalized > 0 else None


def _int_or_none(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            return None
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None
