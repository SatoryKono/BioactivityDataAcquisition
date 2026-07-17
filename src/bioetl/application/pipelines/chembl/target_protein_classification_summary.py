"""Shared target protein-classification summary policy for ChEMBL surfaces."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Final

import polars as pl
from polars.datatypes import DataTypeClass

from bioetl.domain.mapping.protein_class_target_type import (
    MAJOR_FAMILY_RULE_VERSION,
    ProteinClassTargetTypeMappingData,
    current_protein_class_target_type_mapping,
    derive_major_families,
    derive_protein_class_target_type,
)

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

_SUMMARY_SCHEMA: Final[dict[str, DataTypeClass | pl.DataType]] = {
    "target_id": pl.Utf8,
    "protein_classifications": pl.Utf8,
    **{f"target_protein_class_id_L{level}": pl.Utf8 for level in _LEVELS},
    **{f"target_protein_class_name_L{level}": pl.Utf8 for level in _LEVELS},
    **{f"target_protein_class_desc_L{level}": pl.Utf8 for level in _LEVELS},
    "target_protein_class_type": pl.Utf8,
    "top_level_count": pl.Int64,
    "canonical_top_levels": pl.Utf8,
    "counted_top_levels": pl.Utf8,
    "ignored_top_levels": pl.Utf8,
    "primary_top_level": pl.Utf8,
    "target_type_reason_code": pl.Utf8,
    "multifunctional_origin": pl.Utf8,
    "major_family": pl.Utf8,
    "major_family_rule_version": pl.Utf8,
    "target_type_rule_version": pl.Utf8,
    "l1_mapping_version": pl.Utf8,
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
    mapping_data = current_protein_class_target_type_mapping()
    _populate_target_type_summary(summary, resolved_rows, mapping_data)
    if not resolved_rows:
        return summary

    summary["protein_classifications"] = _serialize_classifications(resolved_rows)
    primary_top_level = _text_or_none(summary.get("primary_top_level"))
    if primary_top_level is not None:
        representative_row = _representative_row_for_primary_top_level(
            rows=resolved_rows,
            primary_top_level=primary_top_level,
            mapping_data=mapping_data,
        )
        _copy_single_hierarchy(summary, representative_row)
        return summary

    _mark_multifunctional(summary)
    return summary


def empty_target_protein_classification_summary(target_id: str) -> dict[str, object]:
    """Return an all-null target protein-classification summary row."""
    row: dict[str, object] = {
        column: None for column in _SUMMARY_SCHEMA if column != "target_id"
    }
    row["target_id"] = target_id
    row["target_protein_class_type"] = "unknown"
    row["top_level_count"] = 0
    row["canonical_top_levels"] = "[]"
    row["counted_top_levels"] = "[]"
    row["ignored_top_levels"] = "[]"
    row["major_family"] = "[]"
    row["major_family_rule_version"] = MAJOR_FAMILY_RULE_VERSION
    return row


def _populate_target_type_summary(
    summary: dict[str, object],
    resolved_rows: list[dict[str, object]],
    mapping_data: ProteinClassTargetTypeMappingData,
) -> None:
    result = derive_protein_class_target_type(resolved_rows, mapping_data)
    major_family = derive_major_families(resolved_rows)
    summary["target_protein_class_type"] = result.target_protein_class_type
    summary["top_level_count"] = result.top_level_count
    summary["canonical_top_levels"] = _serialize_string_tuple(
        result.canonical_top_levels
    )
    summary["counted_top_levels"] = _serialize_string_tuple(result.counted_top_levels)
    summary["ignored_top_levels"] = _serialize_string_tuple(result.ignored_top_levels)
    summary["primary_top_level"] = result.primary_top_level
    summary["target_type_reason_code"] = result.reason_code
    summary["multifunctional_origin"] = (
        _multifunctional_origin(resolved_rows)
        if result.target_protein_class_type == "multifunctional"
        else None
    )
    summary["major_family"] = _serialize_string_tuple(major_family)
    summary["major_family_rule_version"] = MAJOR_FAMILY_RULE_VERSION
    summary["target_type_rule_version"] = result.rule_version
    summary["l1_mapping_version"] = result.mapping_version


def _representative_row_for_primary_top_level(
    *,
    rows: list[dict[str, object]],
    primary_top_level: str,
    mapping_data: ProteinClassTargetTypeMappingData,
) -> dict[str, object]:
    for row in rows:
        result = derive_protein_class_target_type((row,), mapping_data)
        if result.counted_top_levels == (primary_top_level,):
            return row
    return rows[0]


def _multifunctional_origin(rows: list[dict[str, object]]) -> str:
    component_ids = {
        component_id
        for row in rows
        if (component_id := _positive_int_or_none(row.get("component_id"))) is not None
    }
    if len(component_ids) > 1:
        return "multi_component_heterogeneity"
    return "multiple_informative_top_levels"


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


def _serialize_string_tuple(values: tuple[str, ...]) -> str:
    return json.dumps(values, sort_keys=False, separators=(",", ":"))


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
