"""Adapter implementations for external systems."""

from __future__ import annotations

from bioetl.infrastructure.adapters.cached_bronze_data_source import (
    CachedBronzeDataSource,
)
from bioetl.infrastructure.adapters.decorators import (
    CircuitBreakerDataSourceDecorator,
    RetryingDataSourceDecorator,
    wrap_with_resilience,
)
from bioetl.infrastructure.adapters.validation import (
    RecordValidationResult,
    get_record_model,
    parse_with_validation,
    validate_record,
    validate_records,
)

__all__ = [
    "CachedBronzeDataSource",
    "CircuitBreakerDataSourceDecorator",
    "RecordValidationResult",
    "RetryingDataSourceDecorator",
    "get_record_model",
    "parse_with_validation",
    "validate_record",
    "validate_records",
    "wrap_with_resilience",
]
