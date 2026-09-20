"""Shared helpers for assembling domain validation result envelopes."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import (
    CompositeValidationReport,
    ValidationIssue,
    ValidationResult,
)
from bioetl.domain.types.validation_severity import ValidationLayer


def build_validation_result(
    *,
    issues: list[ValidationIssue],
    validation_layer: ValidationLayer,
    execution_context: JsonDict | None = None,
    timestamp: str | None = None,
) -> ValidationResult:
    """Build one canonical ValidationResult envelope."""
    return ValidationResult(
        issues=issues,
        validation_layer=validation_layer,
        execution_context=execution_context,
        timestamp=timestamp,
    )


def _require_composite_validation_report(
    value: object,
) -> CompositeValidationReport:
    """Return a concrete report after validating replacement output."""
    if not isinstance(value, CompositeValidationReport):
        raise TypeError(
            "dataclass replacement did not preserve CompositeValidationReport"
        )
    return value
