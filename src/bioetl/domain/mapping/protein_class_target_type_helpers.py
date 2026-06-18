"""Helper functions for protein-class target type derivation."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from bioetl.domain.mapping.protein_class_target_type import (
        NormalizedProteinClassTopLevel,
        ProteinClassTargetTypeMappingData,
    )

_BOOL_STRING_VALUES: Final = {
    "true": True,
    "1": True,
    "yes": True,
    "false": False,
    "0": False,
    "no": False,
}

_TOP_LEVEL_KEYS: Final = ("level_1", "l1", "level1", "l1_name")
_MAJOR_FAMILY_MATCHERS: Final[tuple[tuple[str, tuple[str, ...]], ...]] = (
    ("abc_transporter", ("atp-binding cassette", "abc transporter")),
    ("gpcr", ("g protein-coupled receptor", "gpcr")),
    ("kinase", ("kinase",)),
    ("nuclear_receptor", ("nuclear receptor",)),
    ("protease", ("protease", "peptidase")),
    ("slc_transporter", ("slc superfamily of solute carriers", "solute carrier")),
    (
        "voltage_gated_ion_channel",
        ("voltage-gated ion channel", "voltage gated ion channel"),
    ),
)


def normalize_protein_class_label(value: object) -> str | None:
    """Normalize a provider class label for deterministic lookup."""
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text:
        return None
    return " ".join(text.split()).casefold()


def _normalized_top_level_from_row(
    row: Mapping[str, object],
    mapping_data: ProteinClassTargetTypeMappingData,
    *,
    normalized_top_level_cls: type[NormalizedProteinClassTopLevel],
    normalize_top_level: Callable[
        [object, ProteinClassTargetTypeMappingData],
        NormalizedProteinClassTopLevel,
    ],
) -> NormalizedProteinClassTopLevel:
    """Extract and normalize a single top-level protein class from a row."""
    canonical = _text_or_none(row.get("canonical_l1"))
    if canonical is not None:
        counts = _bool_or_none(row.get("l1_counts_for_target_type"))
        if counts is None:
            counts = canonical not in mapping_data.non_counting_classes
        return normalized_top_level_cls(
            raw_l1=_first_text(row, _TOP_LEVEL_KEYS),
            canonical_l1=canonical,
            counts_for_target_type=counts,
            normalization_status=_text_or_none(row.get("l1_normalization_status"))
            or "ok",
            normalization_notes=_text_or_none(row.get("l1_normalization_notes")),
        )

    return normalize_top_level(
        _first_present(row, _TOP_LEVEL_KEYS),
        mapping_data,
    )


def _canonical_top_levels(
    normalized: tuple[NormalizedProteinClassTopLevel, ...],
) -> tuple[str, ...]:
    """Return sorted unique canonical top-level classes."""
    return tuple(sorted({item.canonical_l1 for item in normalized}))


def _counted_top_levels(
    normalized: tuple[NormalizedProteinClassTopLevel, ...],
) -> tuple[str, ...]:
    """Return sorted unique counted top-level classes."""
    return tuple(
        sorted({item.canonical_l1 for item in normalized if item.counts_for_target_type})
    )


def _ignored_top_levels(
    normalized: tuple[NormalizedProteinClassTopLevel, ...],
) -> tuple[str, ...]:
    """Return sorted unique non-counted top-level classes."""
    return tuple(
        sorted(
            {item.canonical_l1 for item in normalized if not item.counts_for_target_type}
        )
    )


def _target_type_decision(
    counted_top_levels: tuple[str, ...],
    *,
    multifunctional_class: str,
    unknown_target_type: str,
) -> tuple[str, str | None, str]:
    """Decide target type and primary top-level from counted classes."""
    if not counted_top_levels:
        return unknown_target_type, None, "no_informative_top_level"

    if len(counted_top_levels) == 1:
        primary = counted_top_levels[0]
        return primary, primary, "single_informative_top_level"

    return multifunctional_class, None, "multiple_informative_top_levels"


def _normalized_deeper_level_labels(
    rows: Iterable[Mapping[str, object]],
) -> Sequence[str]:
    """Extract all L2+ labels from rows for family matching."""
    labels = []
    for row in rows:
        labels.extend(
            normalized
            for label in _deeper_level_labels(row)
            if (normalized := normalize_protein_class_label(label)) is not None
        )
    return tuple(labels)


def _deeper_level_labels(row: Mapping[str, object]) -> Sequence[object]:
    return (
        row.get("l2_name"),
        row.get("level_2"),
        row.get("l2"),
        row.get("level2"),
        row.get("l3_name"),
        row.get("level_3"),
        row.get("l3"),
        row.get("level3"),
        row.get("l4_name"),
        row.get("level_4"),
        row.get("l4"),
        row.get("level4"),
        row.get("l5_name"),
        row.get("level_5"),
        row.get("l5"),
        row.get("level5"),
    )


def _matching_major_families(label: str) -> tuple[str, ...]:
    """Match a label against major family patterns."""
    matches = [
        family
        for family, patterns in _MAJOR_FAMILY_MATCHERS
        if any(pattern in label for pattern in patterns)
    ]
    return tuple(matches)


def _first_present(row: Mapping[str, object], keys: Sequence[str]) -> object:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _first_text(row: Mapping[str, object], keys: Sequence[str]) -> str | None:
    return _text_or_none(_first_present(row, keys))


def _text_or_none(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _bool_or_none(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        return _BOOL_STRING_VALUES.get(value.strip().casefold())
    return None
