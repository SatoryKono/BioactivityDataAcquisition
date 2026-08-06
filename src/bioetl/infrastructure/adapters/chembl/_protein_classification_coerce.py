"""Coercion and validation helpers for ChEMBL protein classification graph."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassificationResolutionError,
    ProteinClassLevel,
)

__all__ = [
    "MAX_PROVIDER_CLASS_LEVEL",
    "coerce_int",
    "coerce_int_tuple",
    "coerce_positive_int",
    "coerce_str",
    "load_json_if_needed",
    "validate_contiguous_levels",
    "validated_class_level",
]

MAX_PROVIDER_CLASS_LEVEL = 10


def load_json_if_needed(value: object) -> object:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return None
    import json

    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ProteinClassificationResolutionError(
            "protein_classifications must be canonical JSON"
        ) from exc


def coerce_int_tuple(value: object) -> tuple[int, ...]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        return ()
    coerced = [
        int_value
        for item in value
        if (int_value := coerce_int(item)) is not None and int_value > 0
    ]
    return tuple(dict.fromkeys(coerced))


def coerce_int(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(stripped)
        except ValueError:
            return None
    return None


def coerce_positive_int(value: object) -> int | None:
    int_value = coerce_int(value)
    if int_value is None or int_value < 1:
        return None
    return int_value


def coerce_str(value: object) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def validated_class_level(
    node: object,
    *,
    leaf_id: int,
) -> int:
    level = getattr(node, "class_level", None)
    protein_class_id = getattr(node, "protein_class_id", None)
    if level is None:
        raise ProteinClassificationResolutionError(
            f"missing class_level in chain for protein_class_id={leaf_id}"
        )
    if level < 1:
        raise ProteinClassificationResolutionError(
            f"class_level must be >= 1 for protein_class_id={protein_class_id}"
        )
    if level > MAX_PROVIDER_CLASS_LEVEL:
        raise ProteinClassificationResolutionError(
            f"class_level {level} exceeds supported provider range for protein_class_id={protein_class_id}"
        )
    return int(level)


def validate_contiguous_levels(
    levels: Mapping[int, ProteinClassLevel],
    *,
    leaf_id: int,
) -> None:
    if not levels:
        raise ProteinClassificationResolutionError(
            f"no protein classification path resolved for protein_class_id={leaf_id}"
        )
    ordered_levels = sorted(levels)
    expected = list(range(1, max(ordered_levels) + 1))
    if ordered_levels != expected:
        raise ProteinClassificationResolutionError(
            f"broken protein classification chain for protein_class_id={leaf_id}"
        )
