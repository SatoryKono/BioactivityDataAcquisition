"""Common utilities for DQ analyzers.

Provides shared functions used by Bronze, Silver, and Gold DQ analyzers.
Extracted to reduce code duplication per refactoring analysis 2026-01-25.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    DQReportStatus,
    DQReportSummary,
)


def update_counts(
    status: DQCheckStatus,
    passed: int,
    failed: int,
    warnings: int,
) -> tuple[int, int, int]:
    """Update check counts based on status.

    Args:
        status: Result status of the check.
        passed: Current count of passed checks.
        failed: Current count of failed checks.
        warnings: Current count of warning checks.

    Returns:
        Updated tuple of (passed, failed, warnings).
    """
    if status == DQCheckStatus.PASS:
        return passed + 1, failed, warnings
    if status == DQCheckStatus.FAIL:
        return passed, failed + 1, warnings
    return passed, failed, warnings + 1


def convert_value(value: Any) -> Any:
    """Convert a value to serializable format.

    Handles nested dataclasses, enums, datetimes, and collections.

    Args:
        value: Any value to convert.

    Returns:
        JSON-serializable value.
    """
    if hasattr(value, "value"):  # Enum
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return result_to_dict(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [convert_value(v) for v in value]
    if isinstance(value, dict):
        return {k: convert_value(v) for k, v in value.items()}
    return value


def result_to_dict(result: Any) -> dict[str, Any]:
    """Convert dataclass result to dict for serialization.

    Args:
        result: Dataclass result object.

    Returns:
        Dictionary representation suitable for JSON serialization.
    """
    if hasattr(result, "__dataclass_fields__"):
        return {
            field: convert_value(getattr(result, field))
            for field in result.__dataclass_fields__
            if not field.startswith("_")
        }
    return {"value": result}


def build_summary(
    passed: int,
    failed: int,
    warnings: int,
    threshold_status: DQCheckStatus | None = None,
) -> DQReportSummary:
    """Build DQ report summary with overall status.

    Args:
        passed: Number of passed checks.
        failed: Number of failed checks.
        warnings: Number of warning checks.
        threshold_status: Optional status from threshold calculation
            (used by Silver analyzer).

    Returns:
        DQReportSummary with overall status.
    """
    if failed > 0 or (threshold_status == DQCheckStatus.FAIL):
        overall_status = DQReportStatus.FAIL
    elif warnings > 0 or (threshold_status == DQCheckStatus.WARN):
        overall_status = DQReportStatus.WARNING
    else:
        overall_status = DQReportStatus.PASS

    return DQReportSummary(
        total_checks=passed + failed + warnings,
        passed=passed,
        failed=failed,
        warnings=warnings,
        overall_status=overall_status,
    )


__all__ = [
    "build_summary",
    "convert_value",
    "result_to_dict",
    "update_counts",
]
