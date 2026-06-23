"""Internal helpers for deterministic protein-class target type derivation."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Final

NON_COUNTING_CLASSES: Final = frozenset({"missing", "unknown", "unclassified_protein"})
UNKNOWN_NONEMPTY_CLASS: Final = "other_classified_protein"
MISSING_CLASS: Final = "missing"
MULTIFUNCTIONAL_CLASS: Final = "multifunctional"
UNKNOWN_TARGET_TYPE: Final = "unknown"
TOP_LEVEL_KEYS: Final[tuple[str, ...]] = (
    "canonical_l1",
    "l1",
    "level_1",
    "level1",
    "l1_name",
)
DEEPER_LEVEL_KEYS: Final[tuple[str, ...]] = (
    "l2",
    "l3",
    "l4",
    "level_2",
    "level_3",
    "level_4",
)
MAJOR_FAMILY_RULES: Final[tuple[tuple[str, str], ...]] = (
    ("g protein-coupled receptor", "gpcr"),
    ("gpcr", "gpcr"),
    ("nuclear receptor", "nuclear_receptor"),
    ("kinase", "kinase"),
)
BOOL_BY_TOKEN: Final[dict[str, bool]] = {
    "0": False,
    "1": True,
    "false": False,
    "n": False,
    "no": False,
    "true": True,
    "y": True,
    "yes": True,
}


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
                for key in DEEPER_LEVEL_KEYS
                for normalized in [normalize_label(row.get(key))]
                if normalized is not None
            }
        )
    )


def matching_major_families(label: str) -> tuple[str, ...]:
    """Return reviewed major-family tags matching one normalized deeper label."""
    matches = [family for needle, family in MAJOR_FAMILY_RULES if needle in label]
    return tuple(sorted(set(matches)))


def missing_top_level(normalized_top_level_cls: type[object]) -> object:
    return normalized_top_level_cls(
        raw_l1=None,
        canonical_l1=MISSING_CLASS,
        counts_for_target_type=False,
        normalization_status="missing",
        normalization_notes="top-level protein class is absent",
    )


def fallback_top_level(
    raw_l1: str,
    normalized_top_level_cls: type[object],
) -> object:
    return normalized_top_level_cls(
        raw_l1=raw_l1,
        canonical_l1=UNKNOWN_NONEMPTY_CLASS,
        counts_for_target_type=True,
        normalization_status="fallback",
        normalization_notes="unmapped non-empty top-level protein class",
    )


def mapped_top_level(
    raw_l1: str,
    entry: object,
    normalized_top_level_cls: type[object],
) -> object:
    status = "ok" if entry.counts_for_target_type else "non_counting"
    return normalized_top_level_cls(
        raw_l1=raw_l1,
        canonical_l1=entry.canonical_l1,
        counts_for_target_type=entry.counts_for_target_type,
        normalization_status=status,
        normalization_notes=None,
    )


def coerce_counts_for_target_type(
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
    return BOOL_BY_TOKEN.get(normalized, default)


def normalized_status(
    value: object,
    *,
    normalize_label: Callable[[object], str | None],
) -> str:
    normalized = normalize_label(value)
    return normalized or "ok"


def first_normalized_label(
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


def first_present_value(
    row: Mapping[str, object],
    keys: Iterable[str],
) -> object:
    for key in keys:
        value = row.get(key)
        if value is not None:
            return value
    return None
