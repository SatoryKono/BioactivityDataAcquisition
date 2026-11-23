"""Canonical JSON cells for the additive 3.2.0 target projection."""

from __future__ import annotations

import json

from iuphar_target_class.pipeline import RowResult


def _jsonable(value: object) -> object:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    fields = getattr(value, "__dataclass_fields__", None)
    if isinstance(fields, dict):
        return {str(name): _jsonable(getattr(value, str(name))) for name in fields}
    return value


def _cell_json(value: object) -> str:
    """Compact canonical JSON for a table cell. Empty means computed empty."""
    return json.dumps(
        _jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def detail_projection(output: RowResult) -> dict[str, str | None]:
    """Project 3.2.0 detail. Null stays reserved for rows that were not computed."""
    result = output.result
    direct = output.direct
    annotation = output.annotation
    evidence = tuple(sorted({*result.match_evidence_ids, *result.local_evidence_ids}))
    return {
        "iuphar_type_raw": result.iuphar_type_raw,
        "iuphar_annotation_capability": (
            direct.annotation_capability if direct is not None else None
        ),
        "iuphar_family_ids": _cell_json(
            annotation.family_ids if annotation is not None else ()
        ),
        "iuphar_subclasses": _cell_json(
            direct.iuphar_subclasses if direct is not None else ()
        ),
        "iuphar_paths": _cell_json(direct.paths if direct is not None else ()),
        "local_status": result.local_status,
        "local_subclasses": _cell_json(result.local_subclasses),
        "local_rule_ids": _cell_json(result.local_rule_ids),
        "effective_subclasses": _cell_json(result.effective_subclasses),
        "conflict_codes": _cell_json(result.conflict_codes),
        "classification_evidence_ids": _cell_json(evidence),
    }
