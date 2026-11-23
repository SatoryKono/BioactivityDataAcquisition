"""Canonical persisted text for the IUPHAR target classification detail fields."""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from typing import cast

from bioetl.domain.normalization.json import serialize_json_canonical

IUPHAR_SOURCE_COMPLETENESS = frozenset(
    {"family_only", "source_unavailable", "typed", "unannotated"}
)
LOCAL_STATUS_VALUES = frozenset(
    {"candidate_only", "conflicting", "not_supported", "supported"}
)
_SCALAR_FIELDS = frozenset(
    {"iuphar_type_raw", "iuphar_source_completeness", "local_status"}
)
_SET_FIELDS = frozenset(
    {
        "iuphar_family_ids",
        "iuphar_subclasses",
        "local_subclasses",
        "local_rule_ids",
        "effective_subclasses",
        "conflict_codes",
    }
)
_PATH_FIELD = "iuphar_family_paths"
_EVIDENCE_FIELD = "classification_evidence_refs"
_PATH_KEYS = frozenset({"family_id", "root_to_leaf"})
_EVIDENCE_KEYS = frozenset({"local_evidence_ids", "match_evidence_ids"})
_EvidenceIds = tuple[Iterable[object], Iterable[object]]


def _missing(value: object) -> bool:
    if value is None:
        return True
    return isinstance(value, float) and math.isnan(value)


def _one_string(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("classification values must be strings")
    text = value.strip()
    if not text or any(ord(char) < 32 for char in text):
        raise ValueError("classification values must be non-blank")
    return text


def _string_set(values: Iterable[object]) -> tuple[str, ...]:
    return tuple(sorted({_one_string(item) for item in values}))


def canonical_string_set(values: Iterable[object]) -> str:
    return serialize_json_canonical(list(_string_set(values)))


def canonical_family_paths(paths: Iterable[tuple[object, Sequence[object]]]) -> str:
    records: list[dict[str, object]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for family_id, nodes in paths:
        family = _one_string(family_id)
        chain = tuple(_one_string(node) for node in nodes)
        if not chain:
            raise ValueError("classification path requires a root-to-leaf chain")
        key = (family, chain)
        if key in seen:
            continue
        seen.add(key)
        records.append({"family_id": family, "root_to_leaf": list(chain)})
    records.sort(
        key=lambda item: (
            str(item["family_id"]),
            tuple(cast(list[str], item["root_to_leaf"])),
        )
    )
    return serialize_json_canonical(records)


def canonical_evidence_refs(
    match_ids: Iterable[object], local_ids: Iterable[object]
) -> str:
    return serialize_json_canonical(
        {
            "local_evidence_ids": list(_string_set(local_ids)),
            "match_evidence_ids": list(_string_set(match_ids)),
        }
    )


def _source_is_unavailable(
    annotation_status: str | None, match_status: str | None
) -> bool:
    return (
        annotation_status == "source_unavailable"
        or match_status == "source_unavailable"
    )


def _source_is_typed(type_raw: str | None) -> bool:
    return type_raw is not None and bool(type_raw.strip())


def source_completeness(
    *,
    annotation_status: str | None,
    type_raw: str | None,
    family_ids: Iterable[object],
    match_status: str | None = None,
) -> str:
    if _source_is_unavailable(annotation_status, match_status):
        return "source_unavailable"
    if _source_is_typed(type_raw):
        return "typed"
    if any(True for _item in family_ids):
        return "family_only"
    return "unannotated"


def project_classification_detail(
    *,
    computed: bool,
    iuphar_type_raw: str | None,
    annotation_status: str | None,
    match_status: str | None = None,
    family_ids: Iterable[object],
    subclasses: Iterable[object],
    paths: Iterable[tuple[object, Sequence[object]]],
    local_status: str | None,
    local_subclasses: Iterable[object],
    local_rule_ids: Iterable[object],
    effective_subclasses: Iterable[object],
    conflict_codes: Iterable[object],
    evidence_ids: _EvidenceIds,
) -> dict[str, str | None]:
    from bioetl.domain.config.target_classification import (
        TARGET_CLASSIFICATION_DETAIL_FIELDS,
    )

    if not computed:
        return dict.fromkeys(TARGET_CLASSIFICATION_DETAIL_FIELDS)
    families = tuple(family_ids)
    return {
        "iuphar_type_raw": None
        if iuphar_type_raw is None
        else _canonical_scalar("iuphar_type_raw", iuphar_type_raw),
        "iuphar_source_completeness": source_completeness(
            annotation_status=annotation_status,
            match_status=match_status,
            type_raw=iuphar_type_raw,
            family_ids=families,
        ),
        "iuphar_family_ids": canonical_string_set(families),
        "iuphar_subclasses": canonical_string_set(subclasses),
        "iuphar_family_paths": canonical_family_paths(paths),
        "local_status": None
        if local_status is None
        else _canonical_scalar("local_status", local_status),
        "local_subclasses": canonical_string_set(local_subclasses),
        "local_rule_ids": canonical_string_set(local_rule_ids),
        "effective_subclasses": canonical_string_set(effective_subclasses),
        "conflict_codes": canonical_string_set(conflict_codes),
        "classification_evidence_refs": canonical_evidence_refs(*evidence_ids),
    }


def _canonical_json_field(field_name: str, value: str) -> str:
    parsed = _parse_json(value)
    if field_name in _SET_FIELDS:
        if not isinstance(parsed, list):
            raise ValueError(f"{field_name} must be a JSON array")
        return canonical_string_set(parsed)
    if field_name == _PATH_FIELD:
        return canonical_family_paths(_path_pairs(parsed))
    if field_name == _EVIDENCE_FIELD:
        return canonical_evidence_refs(*_evidence_members(parsed))
    raise ValueError(f"unknown classification detail field: {field_name}")


def canonical_persisted_text(field_name: str, value: object) -> str | None:
    if _missing(value):
        return None
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a canonical string or null")
    if field_name in _SCALAR_FIELDS:
        return _canonical_scalar(field_name, value)
    return _canonical_json_field(field_name, value)


def detail_is_canonical(field_name: str, value: object) -> bool:
    """Accept only null or text that is already in canonical form."""
    if _missing(value):
        return True
    try:
        return canonical_persisted_text(field_name, value) == value
    except (TypeError, ValueError):
        return False


def _canonical_scalar(field_name: str, value: str) -> str:
    text = _one_string(value)
    if (
        field_name == "iuphar_source_completeness"
        and text not in IUPHAR_SOURCE_COMPLETENESS
    ):
        raise ValueError("unknown IUPHAR source completeness")
    if field_name == "local_status" and text not in LOCAL_STATUS_VALUES:
        raise ValueError("unknown local classification status")
    return text


def _parse_json(value: str) -> object:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("classification value must be JSON") from exc


def _path_record(item: object) -> tuple[object, tuple[object, ...]]:
    if not isinstance(item, Mapping) or set(item) != _PATH_KEYS:
        raise ValueError("classification path keys must be family_id and root_to_leaf")
    chain = item["root_to_leaf"]
    if not isinstance(chain, list):
        raise ValueError("classification path root_to_leaf must be an array")
    return item["family_id"], tuple(chain)


def _path_pairs(parsed: object) -> tuple[tuple[object, tuple[object, ...]], ...]:
    if not isinstance(parsed, list):
        raise ValueError("classification paths must be a JSON array")
    return tuple(_path_record(item) for item in parsed)


def _evidence_members(parsed: object) -> tuple[list[object], list[object]]:
    if not isinstance(parsed, Mapping) or set(parsed) != _EVIDENCE_KEYS:
        raise ValueError("classification evidence refs must contain both id sets")
    match_ids = parsed["match_evidence_ids"]
    local_ids = parsed["local_evidence_ids"]
    if not isinstance(match_ids, list) or not isinstance(local_ids, list):
        raise ValueError("classification evidence ids must be arrays")
    return match_ids, local_ids


__all__ = [
    "IUPHAR_SOURCE_COMPLETENESS",
    "LOCAL_STATUS_VALUES",
    "canonical_evidence_refs",
    "canonical_family_paths",
    "canonical_persisted_text",
    "canonical_string_set",
    "detail_is_canonical",
    "project_classification_detail",
    "source_completeness",
]
