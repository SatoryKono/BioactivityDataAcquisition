"""Data quality exceptions for invalid or malformed data.

These errors indicate problems with individual data records that should
be logged and skipped, but should not stop the pipeline.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import BioETLError, DataQualityError
from bioetl.domain.types import ErrorType


class SchemaViolationError(DataQualityError):
    """Raised when data does not match expected schema.

    This indicates that a data record has schema validation errors and should be skipped.
    """

    error_type = ErrorType.SCHEMA_VIOLATION

    def __init__(self, table: str, errors: list[str]) -> None:
        self.table = table
        self.errors = errors
        super().__init__(f"Schema validation failed for '{table}': {errors}")


class MissingRequiredFieldError(DataQualityError):
    """Raised when required field is missing from data record."""

    error_type = ErrorType.MISSING_REQUIRED_FIELD

    def __init__(self, field: str, record_id: str | None = None) -> None:
        self.field = field
        self.record_id = record_id
        msg = f"Missing required field: {field}"
        if record_id:
            msg += f" (record_id={record_id})"
        super().__init__(msg)


class InvalidDataFormatError(DataQualityError):
    """Raised when data format is invalid."""

    error_type = ErrorType.INVALID_DATA

    def __init__(self, field: str, value: str, expected_format: str) -> None:
        self.field = field
        self.value = value
        self.expected_format = expected_format
        super().__init__(
            f"Invalid format for '{field}': got '{value}', expected {expected_format}"
        )


class DataQualityThresholdError(BioETLError):
    """Raised when Data Quality error rate exceeds the hard threshold.

    This error indicates that the quality of the batch is too low to proceed,
    requiring the pipeline or batch to stop.
    """

    error_type = ErrorType.DATA_QUALITY

    def __init__(self, error_rate: float, threshold: float) -> None:
        self.error_rate = error_rate
        self.threshold = threshold
        super().__init__(
            f"DQ Hard Threshold exceeded: {error_rate:.2%} errors (limit: {threshold:.2%})"
        )
