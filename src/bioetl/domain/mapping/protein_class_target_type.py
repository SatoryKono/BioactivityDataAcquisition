"""Deterministic ChEMBL protein-class target type derivation."""

from __future__ import annotations

import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Final, Protocol

from . import protein_class_target_type_helpers as helpers

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
    non_counting_classes: frozenset[str] = helpers.NON_COUNTING_CLASSES

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


class _NormalizedTopLevelLike(Protocol):
    canonical_l1: str
    counts_for_target_type: bool


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
        return helpers.missing_top_level(NormalizedProteinClassTopLevel)

    entry = data.by_raw_key.get(normalized)
    if entry is None:
        return helpers.fallback_top_level(normalized, NormalizedProteinClassTopLevel)

    return helpers.mapped_top_level(
        normalized,
        entry,
        NormalizedProteinClassTopLevel,
    )


def normalized_top_level_from_row(
    row: Mapping[str, object],
    mapping_data: ProteinClassTargetTypeMappingData,
    *,
    normalized_top_level_cls: type[
        Any  # Any: Polymorphic class type for normalized top-level objects.
    ],
    normalize_top_level: Callable[
        [object, ProteinClassTargetTypeMappingData | None],
        Any,  # Any: Return type matches polymorphic normalized object type
    ],
    normalize_label: Callable[[object], str | None],
    non_counting_classes: frozenset[str],
) -> Any:  # Any: Return type matches polymorphic normalized object type
    """Resolve one source row into canonical top-level evidence."""
    canonical_l1 = normalize_label(row.get("canonical_l1"))
    if canonical_l1 is not None:
        counts_for_target_type = helpers.coerce_counts_for_target_type(
            row.get("l1_counts_for_target_type"),
            default=canonical_l1 not in non_counting_classes,
            normalize_label=normalize_label,
        )
        normalization_status = helpers.normalized_status(
            row.get("l1_normalization_status"),
            normalize_label=normalize_label,
        )
        raw_l1 = helpers.first_normalized_label(
            row,
            helpers.TOP_LEVEL_KEYS[1:],
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
        helpers.first_present_value(row, helpers.TOP_LEVEL_KEYS[1:]), mapping_data
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


def derive_protein_class_target_type(
    rows: Iterable[Mapping[str, object]],
    mapping_data: ProteinClassTargetTypeMappingData | None = None,
) -> ProteinClassTargetTypeResult:
    """Derive target protein-class type from relation or raw class rows."""
    data = mapping_data or current_protein_class_target_type_mapping()
    normalized = tuple(
        normalized_top_level_from_row(
            row,
            data,
            normalized_top_level_cls=NormalizedProteinClassTopLevel,
            normalize_top_level=normalize_protein_class_top_level,
            normalize_label=normalize_protein_class_label,
            non_counting_classes=data.non_counting_classes,
        )
        for row in rows
    )
    canonical_levels = canonical_top_levels(normalized)
    counted_levels = counted_top_levels(normalized)
    ignored_levels = ignored_top_levels(normalized)
    target_type, primary_top_level, reason_code = helpers.target_type_decision(
        counted_levels,
        multifunctional_class=helpers.MULTIFUNCTIONAL_CLASS,
        unknown_target_type=helpers.UNKNOWN_TARGET_TYPE,
    )

    top_level_count = len(counted_levels)
    return ProteinClassTargetTypeResult(
        target_protein_class_type=target_type,
        top_level_count=top_level_count,
        canonical_top_levels=canonical_levels,
        counted_top_levels=counted_levels,
        ignored_top_levels=ignored_levels,
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
        for label in helpers.normalized_deeper_level_labels(
            rows,
            normalize_label=normalize_protein_class_label,
        )
        for family in helpers.matching_major_families(label)
    }
    return tuple(sorted(families))
