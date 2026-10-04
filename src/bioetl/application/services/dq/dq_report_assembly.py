"""Common utilities for DQ analyzers.

Provides shared functions used by Bronze, Silver, and Gold DQ analyzers.
Extracted to reduce code duplication per refactoring analysis 2026-01-25.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence, Set
from dataclasses import fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Protocol

from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    DQReportStatus,
    DQReportSummary,
)


def convert_value(value: Any) -> Any:  # Any: recursive serializer h...
    """Convert a value for serialization.

    Handles dataclasses, enums, datetimes, and collection types.

    Args:
        value: Value to convert.

    Returns:
        Serializable representation of the value.
    """
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: convert_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: convert_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [convert_value(item) for item in value]
    return value


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


class _HasDQStatus(Protocol):
    """Minimal protocol for DQ results used by shared check execution."""

    status: DQCheckStatus


def run_serialized_checks[TCheckType, TCheckResult: _HasDQStatus, TSerializedResult](
    *,
    enabled_checks: Set[TCheckType],
    dispatch: Sequence[tuple[TCheckType, str, Callable[[], TCheckResult]]],
    checks: dict[str, TSerializedResult],
    serialize_result: Callable[[TCheckResult], TSerializedResult],
    passed: int,
    failed: int,
    warnings: int,
) -> tuple[int, int, int]:
    """Execute enabled checks with shared serialization/count aggregation."""
    for check_type, key, handler in dispatch:
        if check_type not in enabled_checks:
            continue
        result = handler()
        checks[key] = serialize_result(result)
        passed, failed, warnings = update_counts(
            result.status,
            passed,
            failed,
            warnings,
        )
    return passed, failed, warnings


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
    "run_serialized_checks",
    "update_counts",
]
