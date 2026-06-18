"""Deterministic ChEMBL protein-class target type derivation."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

__all__ = [
    "MAJOR_FAMILY_RULE_VERSION",
    "PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION",
    "NormalizedProteinClassTopLevel",
    "ProteinClassTargetTypeMappingData",
    "ProteinClassTargetTypeResult",
    "ProteinClassTopLevelMappingEntry",
    "current_protein_class_target_type_mapping",
    "derive_major_families",
    "derive_protein_class_target_type",
    "initialize_protein_class_target_type_mapping",
    "is_protein_class_target_type_mapping_initialized",
    "normalize_protein_class_label",
    "normalize_protein_class_top_level",
]

PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION: Final = "target_type_rule_v1"
MAJOR_FAMILY_RULE_VERSION: Final = "major_family_rule_v1"

_NON_COUNTING_CLASSES: Final = frozenset({"missing", "unknown", "unclassified_protein"})
_UNKNOWN_NONEMPTY_CLASS: Final = "other_classified_protein"
_MISSING_CLASS: Final = "missing"
_MULTIFUNCTIONAL_CLASS: Final = "multifunctional"
_UNKNOWN_TARGET_TYPE: Final = "unknown"
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


@dataclass(frozen=True, slots=True)
class ProteinClassTopLevelMappingEntry:
    """One raw L1 label mapping to a canonical target-type class."""

    raw_label: str
    canonical_l1: str
    counts_for_target_type: bool

    @property
    def raw_key(self) -> str:
        """Return the deterministic lookup key for the raw label."""
        normalized = normalize_protein_class_label(self.raw_label)
        if normalized is None:
            raise ValueError("protein class mapping raw_label must not be blank")
        return normalized


@dataclass(frozen=True, slots=True)
class ProteinClassTargetTypeMappingData:
    """Immutable versioned mapping data for ChEMBL protein-class L1 labels."""

    mapping_version: str
    entries: tuple[ProteinClassTopLevelMappingEntry, ...]
    non_counting_classes: frozenset[str] = _NON_COUNTING_CLASSES

    def __post_init__(self) -> None:
        if not self.mapping_version.strip():
            raise ValueError("mapping_version must not be blank")
        if not self.entries:
            raise ValueError("protein class target type mapping must not be empty")
        keys = [entry.raw_key for entry in self.entries]
        if len(set(keys)) != len(keys):
            raise ValueError("protein class target type mapping has duplicate labels")

    @property
    def by_raw_key(self) -> dict[str, ProteinClassTopLevelMappingEntry]:
        """Return raw normalized label -> mapping entry."""
        return {entry.raw_key: entry for entry in self.entries}


@dataclass(frozen=True, slots=True)
class NormalizedProteinClassTopLevel:
    """Normalized one-row top-level class evidence."""

    raw_l1: str | None
    canonical_l1: str
    counts_for_target_type: bool
    normalization_status: str
    normalization_notes: str | None


@dataclass(frozen=True, slots=True)
class ProteinClassTargetTypeResult:
    """Target-level protein class type aggregation result."""

    target_protein_class_type: str
    top_level_count: int
    canonical_top_levels: tuple[str, ...]
    counted_top_levels: tuple[str, ...]
    ignored_top_levels: tuple[str, ...]
    primary_top_level: str | None
    reason_code: str
    mapping_version: str
    rule_version: str = PROTEIN_CLASS_TARGET_TYPE_RULE_VERSION


_mapping_data: ProteinClassTargetTypeMappingData | None = None


def initialize_protein_class_target_type_mapping(
    data: ProteinClassTargetTypeMappingData,
) -> None:
    """Initialize domain lookup data from composition-provided mapping."""
    global _mapping_data
    _mapping_data = data


def is_protein_class_target_type_mapping_initialized() -> bool:
    """Return whether the protein class target-type mapping has been loaded."""
    return _mapping_data is not None


def current_protein_class_target_type_mapping() -> ProteinClassTargetTypeMappingData:
    """Return the initialized mapping data or fail closed."""
    if _mapping_data is None:
        raise RuntimeError(
            "Protein class target type mapping not initialized. "
            "Call initialize_protein_class_target_type_mapping() at startup."
        )
    return _mapping_data


def normalize_protein_class_label(value: object) -> str | None:
    """Normalize a provider class label for deterministic lookup."""
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", str(value)).strip()
    if not text:
        return None
    return " ".join(text.split()).casefold()


def normalize_protein_class_top_level(
    raw_l1: object,
    mapping_data: ProteinClassTargetTypeMappingData | None = None,
) -> NormalizedProteinClassTopLevel:
    """Normalize one raw L1 value to canonical top-level evidence."""
    data = mapping_data or current_protein_class_target_type_mapping()
    normalized = normalize_protein_class_label(raw_l1)
    if normalized is None:
        return _missing_top_level()

    entry = data.by_raw_key.get(normalized)
    if entry is None:
        return _fallback_top_level(normalized)

    return _mapped_top_level(normalized, entry)


def derive_protein_class_target_type(
    rows: Iterable[Mapping[str, object]],
    mapping_data: ProteinClassTargetTypeMappingData | None = None,
) -> ProteinClassTargetTypeResult:
    """Derive target protein-class type from relation or raw class rows."""
    data = mapping_data or current_protein_class_target_type_mapping()
    normalized = tuple(
        _normalized_top_level_from_row(
            row,
            data,
            normalized_top_level_cls=NormalizedProteinClassTopLevel,
            normalize_top_level=normalize_protein_class_top_level,
        )
        for row in rows
    )
    canonical_top_levels = _canonical_top_levels(normalized)
    counted_top_levels = _counted_top_levels(normalized)
    ignored_top_levels = _ignored_top_levels(normalized)
    target_type, primary_top_level, reason_code = _target_type_decision(
        counted_top_levels,
        multifunctional_class=_MULTIFUNCTIONAL_CLASS,
        unknown_target_type=_UNKNOWN_TARGET_TYPE,
    )

    top_level_count = len(counted_top_levels)
    return ProteinClassTargetTypeResult(
        target_protein_class_type=target_type,
        top_level_count=top_level_count,
        canonical_top_levels=canonical_top_levels,
        counted_top_levels=counted_top_levels,
        ignored_top_levels=ignored_top_levels,
        primary_top_level=primary_top_level,
        reason_code=reason_code,
        mapping_version=data.mapping_version,
    )


def derive_major_families(
    rows: Iterable[Mapping[str, object]],
) -> tuple[str, ...]:
    """Derive major scientific families from L2+ labels only."""
    families = {
        family
        for label in _normalized_deeper_level_labels(rows)
        for family in _matching_major_families(label)
    }
    return tuple(sorted(families))


def _missing_top_level() -> NormalizedProteinClassTopLevel:
    return NormalizedProteinClassTopLevel(
        raw_l1=None,
        canonical_l1=_MISSING_CLASS,
        counts_for_target_type=False,
        normalization_status="missing",
        normalization_notes="top-level protein class is absent",
    )


def _fallback_top_level(raw_l1: str) -> NormalizedProteinClassTopLevel:
    return NormalizedProteinClassTopLevel(
        raw_l1=raw_l1,
        canonical_l1=_UNKNOWN_NONEMPTY_CLASS,
        counts_for_target_type=True,
        normalization_status="fallback",
        normalization_notes="unmapped non-empty top-level protein class",
    )


def _mapped_top_level(
    raw_l1: str,
    entry: ProteinClassTopLevelMappingEntry,
) -> NormalizedProteinClassTopLevel:
    status = "ok" if entry.counts_for_target_type else "non_counting"
    return NormalizedProteinClassTopLevel(
        raw_l1=raw_l1,
        canonical_l1=entry.canonical_l1,
        counts_for_target_type=entry.counts_for_target_type,
        normalization_status=status,
        normalization_notes=None,
    )


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
