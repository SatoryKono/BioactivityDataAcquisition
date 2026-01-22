"""Adapter implementations for external systems."""

from __future__ import annotations

from bioetl.infrastructure.adapters.decorators import (
    CircuitBreakerDataSourceDecorator,
    RetryingDataSourceDecorator,
    wrap_with_resilience,
)
from bioetl.infrastructure.adapters.validation import (
    ValidationResult,
    get_record_model,
    parse_with_validation,
    validate_record,
    validate_records,
)

__all__ = [
    "CircuitBreakerDataSourceDecorator",
    "RetryingDataSourceDecorator",
    "ValidationResult",
    "get_record_model",
    "parse_with_validation",
    "validate_record",
    "validate_records",
    "wrap_with_resilience",
]
