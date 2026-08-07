"""Cross-validation domain models for composite pipeline enrichment.

Defines value objects for comparing seed and enricher data before merge.
Cross-validation detects field mismatches between seed records and enricher
records, flagging warnings, nullifying divergent enricher data, and
quarantining suspect seed records.

See plan: Pre-Merge Cross-Validation for Composite Publication Pipeline.
"""

from __future__ import annotations

import math

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "ComparisonMethod",
    "CrossValidationStats",
    "CrossValidationVerdict",
    "EnricherCVStats",
    "EnricherFieldPairing",
    "FieldComparisonSpec",
    "FieldMismatch",
    "RecordCrossValidationResult",
]


class ComparisonMethod(StrEnum):
    """Method used to compare a field between seed and enricher."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    NUMERIC_TOLERANCE = "numeric_tolerance"
    SKIP = "skip"


class CrossValidationVerdict(StrEnum):
    """Verdict for a single seed-enricher record pair."""

    PASS = "pass"  # nosec B105
    WARNING = "warning"
    ENRICHER_ERROR = "enricher_error"


@dataclass(frozen=True, slots=True)
class FieldComparisonSpec:
    """Specification for comparing a single field.

    Attributes:
        field_name: Unified Silver column name (e.g., "title", "doi").
        method: Comparison method to apply.
        threshold: Threshold for fuzzy/numeric comparisons.
            For FUZZY: Jaccard similarity threshold (default 0.8).
            For NUMERIC_TOLERANCE: relative tolerance (default 0.10 = 10%).
            Ignored for EXACT.
    """

    field_name: str
    method: ComparisonMethod
    threshold: float = 0.0

    def _coerce_method(self) -> None:
        if isinstance(self.method, str):
            object.__setattr__(self, "method", ComparisonMethod(self.method))

    def _apply_default_threshold(self) -> None:
        # Deterministic defaults when callers leave threshold at zero.
        # NOSONAR - math.isclose() is the correct way to compare floats (Sonar S1244 false positive)
        if not math.isclose(self.threshold, 0.0, abs_tol=1e-15):
            return
        if self.method == ComparisonMethod.FUZZY:
            object.__setattr__(self, "threshold", 0.8)
            return
        if self.method == ComparisonMethod.NUMERIC_TOLERANCE:
            object.__setattr__(self, "threshold", 0.10)

    def _validate_threshold_range(self) -> None:
        needs_threshold = self.method in (
            ComparisonMethod.FUZZY,
            ComparisonMethod.NUMERIC_TOLERANCE,
        )
        if not needs_threshold:
            return
        if 0.0 < self.threshold <= 1.0:
            return
        raise ValueError(
            f"{self.method} threshold must be in (0.0, 1.0], got {self.threshold}"
        )

    def __post_init__(self) -> None:
        """Apply method defaults and validate specification."""
        if not self.field_name:
            raise ValueError("field_name cannot be empty")
        self._coerce_method()
        self._apply_default_threshold()
        self._validate_threshold_range()


@dataclass(frozen=True, slots=True)
class EnricherFieldPairing:
    """Defines which fields to compare for a specific enricher.

    Attributes:
        enricher_pipeline: Pipeline name (e.g., "crossref_publication").
        fields: Tuple of field comparison specifications.
    """

    enricher_pipeline: str
    fields: tuple[FieldComparisonSpec, ...]

    def __post_init__(self) -> None:
        """Normalize then validate pairing."""
        if isinstance(self.fields, list):
            object.__setattr__(self, "fields", tuple(self.fields))
        if not self.enricher_pipeline:
            raise ValueError("enricher_pipeline cannot be empty")
        if not self.fields:
            raise ValueError(
                f"EnricherFieldPairing for '{self.enricher_pipeline}' "
                "must have at least one field"
            )


@dataclass(frozen=True, slots=True)
class FieldMismatch:
    """Details of a single field mismatch between seed and enricher.

    Attributes:
        field_name: Name of the mismatched field.
        seed_value: Value from seed record.
        enricher_value: Value from enricher record.
        method: Comparison method that detected the mismatch.
    """

    field_name: str
    seed_value: object
    enricher_value: object
    method: ComparisonMethod


@dataclass(frozen=True, slots=True)
class RecordCrossValidationResult:
    """Cross-validation result for a single record against one enricher.

    Attributes:
        enricher: Enricher pipeline name.
        verdict: Overall verdict (PASS, WARNING, or ENRICHER_ERROR).
        mismatches: Tuple of field mismatches found.
        fields_compared: Number of fields actually compared (both non-null).
        fields_skipped: Number of fields skipped (one or both null).
    """

    enricher: str
    verdict: CrossValidationVerdict
    mismatches: tuple[FieldMismatch, ...] = ()
    fields_compared: int = 0
    fields_skipped: int = 0

    def __post_init__(self) -> None:
        """Convert lists to tuples."""
        if isinstance(self.mismatches, list):
            object.__setattr__(self, "mismatches", tuple(self.mismatches))


@dataclass(frozen=True, slots=True)
class EnricherCVStats:
    """Per-enricher cross-validation statistics.

    Attributes:
        enricher: Enricher pipeline name.
        total_records: Total records validated.
        passed: Records that passed validation.
        warned: Records with warnings (1 mismatch).
        errored: Records with enricher error (2+ mismatches).
        field_mismatches: Per-field mismatch counts, e.g. (("title", 12), ("doi", 0)).
    """

    enricher: str
    total_records: int = 0
    passed: int = 0
    warned: int = 0
    errored: int = 0
    field_mismatches: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class CrossValidationStats:
    """Aggregate cross-validation statistics for merge operation.

    Attributes:
        total_records: Total seed records validated.
        passed: Records with no enricher errors.
        warned: Records with at least one warning but no enricher errors.
        errored: Records with at least one enricher error.
        quarantined: Records quarantined (2+ enricher errors).
        enricher_stats: Per-enricher breakdowns.
    """

    total_records: int = 0
    passed: int = 0
    warned: int = 0
    errored: int = 0
    quarantined: int = 0
    enricher_stats: tuple[EnricherCVStats, ...] = ()

    def __post_init__(self) -> None:
        """Convert lists to tuples."""
        if isinstance(self.enricher_stats, list):
            object.__setattr__(self, "enricher_stats", tuple(self.enricher_stats))
