"""Shared helpers for ChEMBL target protein-classification composition wrappers."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassificationResolutionError,
)

_TARGET_ENTITY_TYPE = "target"
_TARGET_COMPONENT_ENTITY_TYPE = "target_component"
_PROTEIN_CLASS_ENTITY_TYPE = "protein_class"
_TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE = "target_protein_classification"
_SUPPORTED_TARGET_FILTER_FIELDS = frozenset({"target_id", "target_chembl_id"})
_SUPPORTED_COMPONENT_FILTER_FIELDS = frozenset({"component_id", "primary_component_id"})


def target_id_from_record(record: Mapping[str, object]) -> str | None:
    """Return the canonical target identifier from a target-like record."""
    for key in ("target_id", "target_chembl_id"):
        value = coerce_text(record.get(key))
        if value is not None:
            return value
    return None


def component_ids_from_target_record(record: Mapping[str, object]) -> tuple[int, ...]:
    """Extract unique component IDs from a target record."""
    raw_components = record.get("target_components")
    component_ids = list(_component_ids_from_target_components_value(raw_components))
    component_ids.extend(
        _component_ids_from_component_ids_value(record.get("component_ids"))
    )
    primary_component_id = coerce_positive_int(record.get("primary_component_id"))
    if primary_component_id is not None:
        component_ids.append(primary_component_id)
    return tuple(dict.fromkeys(component_ids))


def build_target_component_indexes(
    target_rows: Iterable[Mapping[str, object]],
) -> tuple[dict[str, tuple[int, ...]], dict[int, tuple[str, ...]]]:
    """Build deterministic target/component lookup indexes from snapshot rows."""
    target_ids_by_component: dict[int, list[str]] = defaultdict(list)
    component_ids_by_target: dict[str, tuple[int, ...]] = {}
    for row in target_rows:
        target_id = target_id_from_record(row)
        if target_id is None:
            continue
        component_ids = component_ids_from_target_record(row)
        component_ids_by_target[target_id] = component_ids
        for component_id in component_ids:
            target_ids_by_component[component_id].append(target_id)
    return dict(sorted(component_ids_by_target.items())), {
        component_id: tuple(dict.fromkeys(sorted(target_ids)))
        for component_id, target_ids in sorted(target_ids_by_component.items())
    }


def resolve_target_ids(
    *,
    filter_ids: list[str] | None,
    filter_field: str | None,
    target_component_ids: Mapping[str, tuple[int, ...]],
    target_ids_by_component: Mapping[int, tuple[str, ...]],
) -> tuple[str, ...]:
    """Resolve target IDs from target/component filters against snapshot indexes."""
    if not filter_ids:
        return tuple(sorted(target_component_ids))
    if filter_field in _SUPPORTED_TARGET_FILTER_FIELDS:
        requested = {str(value).strip() for value in filter_ids if str(value).strip()}
        return tuple(
            target_id
            for target_id in sorted(target_component_ids)
            if target_id in requested
        )
    if filter_field in _SUPPORTED_COMPONENT_FILTER_FIELDS:
        target_ids: set[str] = set()
        for raw_component_id in filter_ids:
            component_id = coerce_positive_int(raw_component_id)
            if component_id is None:
                continue
            target_ids.update(target_ids_by_component.get(component_id, ()))
        return tuple(sorted(target_ids))
    raise ValueError(
        f"Unsupported target protein classification filter_field: {filter_field}"
    )


def target_ids_from_component_record(record: Mapping[str, object]) -> tuple[str, ...]:
    """Extract unique target IDs from a target-component record."""
    raw_targets = record.get("targets")
    if not isinstance(raw_targets, list):
        return ()
    target_ids = [
        target_id
        for item in raw_targets
        if isinstance(item, Mapping)
        if (target_id := target_id_from_record(item)) is not None
    ]
    return tuple(dict.fromkeys(target_ids))


def leaf_ids_from_component_row(record: Mapping[str, object]) -> tuple[int, ...]:
    """Extract normalized protein-classification leaf IDs from a component row."""
    leaf_ids = leaf_ids_from_value(record.get("protein_classification_ids"))
    if leaf_ids:
        return leaf_ids
    return leaf_ids_from_classification_objects(record.get("protein_classifications"))


def leaf_ids_from_classification_objects(value: object) -> tuple[int, ...]:
    """Extract leaf IDs from list-based classification objects."""
    if not isinstance(value, list):
        return ()
    leaf_ids = [
        leaf_id
        for item in value
        if isinstance(item, Mapping)
        if (
            leaf_id := coerce_positive_int(
                item.get("protein_classification_id")
                or item.get("protein_class_id")
                or item.get("leaf_id")
            )
        )
        is not None
    ]
    return tuple(dict.fromkeys(leaf_ids))


def leaf_ids_from_value(value: object) -> tuple[int, ...]:
    """Extract leaf IDs from canonical JSON or iterable scalar payloads."""
    if value is None:
        return ()
    loaded = value
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ()
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ProteinClassificationResolutionError(
                "protein_classification_ids must be canonical JSON"
            ) from exc
    if not isinstance(loaded, Iterable) or isinstance(loaded, (str, bytes)):
        return ()
    leaf_ids = [
        leaf_id for item in loaded if (leaf_id := coerce_positive_int(item)) is not None
    ]
    return tuple(dict.fromkeys(leaf_ids))


def coerce_positive_int(value: object) -> int | None:
    """Normalize positive integer-like values from mixed payloads."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if not value.is_integer():
            return None
        return coerce_positive_int(int(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return coerce_positive_int(int(stripped))
        except ValueError:
            return None
    return None


def coerce_text(value: object) -> str | None:
    """Normalize optional text-like values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def canonical_json(
    value: Any,
) -> str:  # Any: JSON can be any serializable type (str, int, dict, list, etc.)
    """Serialize a deterministic JSON payload for graph lookup helpers."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _component_ids_from_target_components_value(value: object) -> tuple[int, ...]:
    loaded = _load_json_if_needed(value)
    if not isinstance(loaded, list):
        return ()
    component_ids = [
        component_id
        for item in loaded
        if isinstance(item, Mapping)
        if (component_id := coerce_positive_int(item.get("component_id"))) is not None
    ]
    return tuple(dict.fromkeys(component_ids))


def _component_ids_from_component_ids_value(value: object) -> tuple[int, ...]:
    loaded = _load_json_if_needed(value)
    if not isinstance(loaded, Iterable) or isinstance(loaded, (str, bytes)):
        return ()
    component_ids = [
        component_id
        for item in loaded
        if (component_id := coerce_positive_int(item)) is not None
    ]
    return tuple(dict.fromkeys(component_ids))


def _load_json_if_needed(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ProteinClassificationResolutionError(
            "target component identifiers must be canonical JSON"
        ) from exc
