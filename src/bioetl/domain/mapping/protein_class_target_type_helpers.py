"""Pure helper logic for protein-class target type derivation."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import TYPE_CHECKING, Any, Final, Protocol

if TYPE_CHECKING:
    from bioetl.domain.mapping.protein_class_target_type import (
        ProteinClassTargetTypeMappingData,
    )

_TOP_LEVEL_KEYS: Final[tuple[str, ...]] = (
    "canonical_l1",
    "l1",
    "level_1",
    "level1",
    "l1_name",
)
_DEEPER_LEVEL_KEYS: Final[tuple[str, ...]] = (
    "l2",
    "l3",
    "l4",
    "level_2",
    "level_3",
    "level_4",
)
_MAJOR_FAMILY_RULES: Final[tuple[tuple[str, str], ...]] = (
    ("g protein-coupled receptor", "gpcr"),
    ("gpcr", "gpcr"),
    ("nuclear receptor", "nuclear_receptor"),
    ("kinase", "kinase"),
)
_BOOL_BY_TOKEN: Final[dict[str, bool]] = {
    "0": False,
    "1": True,
    "false": False,
    "n": False,
    "no": False,
    "true": True,
    "y": True,
    "yes": True,
}


class _NormalizedTopLevelLike(Protocol):
    canonical_l1: str
    counts_for_target_type: bool


def normalized_top_level_from_row(
    row: Mapping[str, object],
    mapping_data: ProteinClassTargetTypeMappingData,
    *,
    normalized_top_level_cls: type[Any],
    normalize_top_level: Callable[
        [object, ProteinClassTargetTypeMappingData | None],
        Any,
    ],
    normalize_label: Callable[[object], str | None],
    non_counting_classes: frozenset[str],
) -> Any:
    """Resolve one source row into canonical top-level evidence."""
    canonical_l1 = normalize_label(row.get("canonical_l1"))
    if canonical_l1 is not None:
        counts_for_target_type = _coerce_counts_for_target_type(
            row.get("l1_counts_for_target_type"),
            default=canonical_l1 not in non_counting_classes,
            normalize_label=normalize_label,
        )
        normalization_status = _normalized_status(
            row.get("l1_normalization_status"),
            normalize_label=normalize_label,
        )
        raw_l1 = _first_normalized_label(
            row,
            _TOP_LEVEL_KEYS[1:],
            normalize_label=normalize_label,
        )
        return normalized_top_level_cls(
            raw_l1=raw_l1,
            canonical_l1=canonical_l1,
            counts_for_target_type=counts_for_target_type,
            normalization_status=normalization_status,
            normalization_notes=None,
        )

    return normalize_top_level(
        _first_present_value(row, _TOP_LEVEL_KEYS[1:]), mapping_data
    )


def canonical_top_levels(
    normalized_rows: Iterable[_NormalizedTopLevelLike],
) -> tuple[str, ...]:
    """Return sorted unique canonical L1 classes from normalized rows."""
    return tuple(sorted({row.canonical_l1 for row in normalized_rows}))


def counted_top_levels(
    normalized_rows: Iterable[_NormalizedTopLevelLike],
) -> tuple[str, ...]:
    """Return sorted unique counted top-level classes."""
    return tuple(
        sorted(
            {row.canonical_l1 for row in normalized_rows if row.counts_for_target_type}
        )
    )


def ignored_top_levels(
    normalized_rows: Iterable[_NormalizedTopLevelLike],
) -> tuple[str, ...]:
    """Return sorted unique non-counted top-level classes."""
    return tuple(
        sorted(
            {
                row.canonical_l1
                for row in normalized_rows
                if not row.counts_for_target_type
            }
        )
    )


def target_type_decision(
    counted_levels: tuple[str, ...],
    *,
    multifunctional_class: str,
    unknown_target_type: str,
) -> tuple[str, str | None, str]:
    """Resolve final target-type class from counted canonical top levels."""
    if not counted_levels:
        return unknown_target_type, None, "no_informative_top_level"
    if len(counted_levels) == 1:
        primary = counted_levels[0]
        return primary, primary, "single_informative_top_level"
    return multifunctional_class, None, "multiple_informative_top_levels"


def normalized_deeper_level_labels(
    rows: Iterable[Mapping[str, object]],
    *,
    normalize_label: Callable[[object], str | None],
) -> tuple[str, ...]:
    """Return sorted unique normalized L2+ labels from source rows."""
    return tuple(
        sorted(
            {
                normalized
                for row in rows
                for key in _DEEPER_LEVEL_KEYS
                for normalized in [normalize_label(row.get(key))]
                if normalized is not None
            }
        )
    )


def matching_major_families(label: str) -> tuple[str, ...]:
    """Return reviewed major-family tags matching one normalized deeper label."""
    matches = [family for needle, family in _MAJOR_FAMILY_RULES if needle in label]
    return tuple(sorted(set(matches)))


def _coerce_counts_for_target_type(
    value: object,
    *,
    default: bool,
    normalize_label: Callable[[object], str | None],
) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = normalize_label(value)
    if normalized is None:
        return default
    return _BOOL_BY_TOKEN.get(normalized, default)


def _normalized_status(
    value: object,
    *,
    normalize_label: Callable[[object], str | None],
) -> str:
    normalized = normalize_label(value)
    return normalized or "ok"


def _first_normalized_label(
    row: Mapping[str, object],
    keys: Iterable[str],
    *,
    normalize_label: Callable[[object], str | None],
) -> str | None:
    for key in keys:
        normalized = normalize_label(row.get(key))
        if normalized is not None:
            return normalized
    return None


def _first_present_value(
    row: Mapping[str, object],
    keys: Iterable[str],
) -> object:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None
