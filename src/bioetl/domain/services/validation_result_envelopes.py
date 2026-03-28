"""Shared helpers for assembling domain validation result envelopes."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.domain.types.validation_result import ValidationIssue, ValidationResult
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
