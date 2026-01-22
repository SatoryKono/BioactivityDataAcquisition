"""Validation exceptions for input data and schemas.

These errors indicate that data is incorrect in structure or type.
Usually leads to skipping the problematic record.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import BioETLError
from bioetl.domain.types import ErrorType


class ValidationError(BioETLError):
    """Base class for data/schema validation errors.

    Raised when input data fails format or schema validation checks.
    """

    error_type = ErrorType.INVALID_DATA


class SchemaValidationError(ValidationError):
    """Raised when a data record does not match the expected schema."""

    error_type = ErrorType.SCHEMA_VIOLATION

    def __init__(self, table: str, errors: list[str]) -> None:
        self.table = table
        self.errors = errors
        super().__init__(f"Schema validation failed for '{table}': {errors}")


class MissingRequiredFieldError(ValidationError):
    """Raised when a required field is missing from a data record."""

    error_type = ErrorType.MISSING_REQUIRED_FIELD

    def __init__(self, field: str, record_id: str | None = None) -> None:
        self.field = field
        self.record_id = record_id
        msg = f"Missing required field: {field}"
        if record_id:
            msg += f" (record_id={record_id})"
        super().__init__(msg)


class InvalidDataFormatError(ValidationError):
    """Raised when a data field's format or value is invalid (e.g., wrong data type or format)."""

    error_type = ErrorType.INVALID_DATA

    def __init__(self, field: str, value: str, expected_format: str) -> None:
        self.field = field
        self.value = value
        self.expected_format = expected_format
        super().__init__(
            f"Invalid format for '{field}': got '{value}', expected {expected_format}"
        )


class ExternalDataValidationError(ValidationError):
    """Raised when data returned from an external service fails validation.

    e.g. malformed JSON or missing fields in response.
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        field: str | None = None,
        value: str | None = None,
    ) -> None:
        self.service_name = service_name
        self.field = field
        self.value = value
        super().__init__(message)
