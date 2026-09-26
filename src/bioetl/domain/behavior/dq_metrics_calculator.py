"""Centralized DQ metrics calculation for Silver layer.

Single Source of Truth for DQ metrics used by both:
- SilverWriter (for _metadata.yaml)
- SilverDQAnalyzer (for DQ Report)

Implements REQ-DQ-001.

This is pure domain logic (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bioetl.domain.types import JsonDict
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics, SchemaDriftInfo


@dataclass(frozen=True, slots=True)
class DQMetricsInput:
    """Input for DQ metrics calculation.

    Attributes:
        records: List of record dictionaries to analyze.
        existing_schema_fields: Set of field names from existing table schema.
            Used for schema drift detection. None if table doesn't exist.
        required_schema_fields: Contract-required field names used to classify
            missing-field drift as critical. When None, no missing field is
            treated as critical solely by name.
        quarantined_count: Number of records that failed validation.
        validation_errors: List of validation error messages.
    """

    records: list[JsonDict]  # Any: DQ check values vary by check type
    existing_schema_fields: set[str] | None = None
    required_schema_fields: frozenset[str] | set[str] | None = None
    quarantined_count: int = 0
    validation_errors: list[str] | None = None


class DQMetricsCalculator:
    """Calculator for Silver DQ metrics.

    Provides unified calculation logic used by both
    metadata writer and DQ report generator.

    This class is stateless and thread-safe.
    """

    def calculate(self, input_data: DQMetricsInput) -> BatchDQMetrics:
        """Calculate DQ metrics from records.

        Args:
            input_data: Records and context for calculation.

        Returns:
            BatchDQMetrics with computed statistics including:
            - Column statistics (null rate, unique count, min/max/mean)
            - Schema drift info
            - Error/warning counts
        """
        schema_drift = self._detect_schema_drift(
            input_data.records,
            input_data.existing_schema_fields,
            required_fields=input_data.required_schema_fields,
        )

        return BatchDQMetrics.from_records(
            records=input_data.records,
            error_count=input_data.quarantined_count,
            warning_count=0,
            validation_errors=input_data.validation_errors,
            schema_drift=schema_drift,
        )

    def _detect_schema_drift(
        self,
        records: list[JsonDict],  # Any: DQ check values vary by check type
        existing_fields: set[str] | None,
        required_fields: frozenset[str] | set[str] | None = None,
    ) -> SchemaDriftInfo | None:
        """Detect schema drift between existing and incoming schema.

        Args:
            records: Incoming records to check.
            existing_fields: Field names from existing table schema.
            required_fields: Contract-required field names for critical drift.

        Returns:
            SchemaDriftInfo if drift detected, None otherwise.
        """
        if existing_fields is None or not records:
            return None

        incoming_fields = self._extract_incoming_fields(records)
        new_fields, missing_fields = self._compute_schema_delta(
            incoming_fields=incoming_fields,
            existing_fields=existing_fields,
        )

        if not new_fields and not missing_fields:
            return None

        status = self._determine_drift_status(
            new_fields,
            missing_fields,
            required_fields=required_fields,
        )
        return SchemaDriftInfo(
            status=status,
            new_fields=tuple(sorted(new_fields)),
            missing_fields=tuple(sorted(missing_fields)),
        )

    @staticmethod
    def _extract_incoming_fields(
        records: list[JsonDict],  # Any: DQ check values vary by check type
    ) -> set[str]:
        """Extract incoming field names from the full batch union."""
        if not records:
            return set()
        fields: set[str] = set()
        for record in records:
            fields.update(record.keys())
        return fields

    @staticmethod
    def _compute_schema_delta(
        *,
        incoming_fields: set[str],
        existing_fields: set[str],
    ) -> tuple[set[str], set[str]]:
        """Return (new_fields, missing_fields) delta between incoming/existing schema."""
        return incoming_fields - existing_fields, existing_fields - incoming_fields

    def _determine_drift_status(
        self,
        new_fields: set[str],
        missing_fields: set[str],
        required_fields: frozenset[str] | set[str] | None = None,
    ) -> Literal["info", "warn", "critical"]:
        """Determine drift severity status.

        Drift severity levels:
        - critical: Missing contract-required fields (metadata underscore fields
          remain non-critical even if listed)
        - warn: More than 3 new fields
        - info: Minor schema changes
        """
        if self._has_critical_missing_fields(missing_fields, required_fields):
            return "critical"
        if self._has_excessive_new_fields(new_fields):
            return "warn"
        return "info"

    @staticmethod
    def _has_critical_missing_fields(
        missing_fields: set[str],
        required_fields: frozenset[str] | set[str] | None = None,
    ) -> bool:
        """Return True when contract-required non-metadata fields are missing."""
        if not required_fields:
            return False
        return any(
            field in required_fields and not field.startswith("_")
            for field in missing_fields
        )

    @staticmethod
    def _has_excessive_new_fields(new_fields: set[str]) -> bool:
        """Return True when incoming schema introduces too many new fields."""
        return len(new_fields) > 3


__all__ = ["DQMetricsCalculator", "DQMetricsInput"]
