"""Centralized DQ metrics calculation for Silver layer.

Single Source of Truth for DQ metrics used by both:
- SilverWriter (for _metadata.yaml)
- SilverDQAnalyzer (for DQ Report)

Implements REQ-DQ-001.

This is pure domain logic (no I/O) per RULES.md §1.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics, SchemaDriftInfo


@dataclass(frozen=True, slots=True)
class DQMetricsInput:
    """Input for DQ metrics calculation.

    Attributes:
        records: List of record dictionaries to analyze.
        existing_schema_fields: Set of field names from existing table schema.
            Used for schema drift detection. None if table doesn't exist.
        quarantined_count: Number of records that failed validation.
        validation_errors: List of validation error messages.
    """

    records: list[dict[str, Any]]
    existing_schema_fields: set[str] | None = None
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
        records: list[dict[str, Any]],
        existing_fields: set[str] | None,
    ) -> SchemaDriftInfo | None:
        """Detect schema drift between existing and incoming schema.

        Args:
            records: Incoming records to check.
            existing_fields: Field names from existing table schema.

        Returns:
            SchemaDriftInfo if drift detected, None otherwise.

        Drift severity levels:
        - critical: Missing required fields (non-underscore prefix)
        - warn: More than 3 new fields
        - info: Minor schema changes
        """
        if not existing_fields or not records:
            return None

        incoming_fields = set(records[0].keys())
        new_fields = incoming_fields - existing_fields
        missing_fields = existing_fields - incoming_fields

        if not new_fields and not missing_fields:
            return None

        # Critical: missing required fields (business fields without underscore prefix)
        critical_missing = [f for f in missing_fields if not f.startswith("_")]

        if critical_missing:
            status = "critical"
        elif len(new_fields) > 3:
            status = "warn"
        else:
            status = "info"

        return SchemaDriftInfo(
            status=status,
            new_fields=tuple(sorted(new_fields)),
            missing_fields=tuple(sorted(missing_fields)),
        )


__all__ = ["DQMetricsCalculator", "DQMetricsInput"]
