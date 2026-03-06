"""Validation exceptions for schema and data format errors.

These errors indicate that data does not conform to expected schemas or formats.
ValidationErrors are typically recoverable at the record level - individual invalid
records can be logged and skipped while processing continues for other records.

Category: ValidationErrors - data and schema validation errors (format violations,
missing fields, etc.).
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import DataQualityError
from bioetl.domain.types import ErrorType

__all__ = [
    "InvalidDataFormatError",
    "MissingRequiredFieldError",
    "SchemaViolationError",
    "ValidationError",
]


class ValidationError(DataQualityError):
    """Base class for all validation errors.

    ValidationErrors indicate structural problems with data records:
    - Schema violations (wrong structure)
    - Missing required fields
    - Invalid data formats

    These errors are handled by logging and skipping the affected record,
    allowing the pipeline to continue processing other records.

    Inherits from DataQualityError to maintain the error classification hierarchy.
    """

    error_type = ErrorType.INVALID_DATA


class SchemaViolationError(ValidationError):
    """Raised when data does not match expected schema.

    This indicates that a data record has schema validation errors and should be skipped.

    Attributes:
        table: Name of the table/entity with schema violation.
        errors: List of specific validation error messages.

    Example:
        >>> raise SchemaViolationError("compounds", ["missing 'smiles'", "invalid 'mass'"])
    """

    error_type = ErrorType.SCHEMA_VIOLATION

    def __init__(self, table: str, errors: list[str]) -> None:
        """Initialize SchemaViolationError.

        Args:
            table: Name of the table or entity with schema violation.
            errors: List of specific validation error messages.
        """
        self.table = table
        self.errors = errors
        super().__init__(f"Schema validation failed for '{table}': {errors}")


def MissingRequiredFieldError(
    field: str,
    record_id: str | None = None,
) -> ValidationError:
    """Compatibility constructor for legacy MissingRequiredFieldError."""
    msg = f"Missing required field: {field}"
    if record_id:
        msg += f" (record_id={record_id})"
    error = ValidationError(msg)
    error.field = field
    error.record_id = record_id
    error.error_type = ErrorType.MISSING_REQUIRED_FIELD
    return error


def InvalidDataFormatError(
    field: str,
    value: str,
    expected_format: str,
) -> ValidationError:
    """Compatibility constructor for legacy InvalidDataFormatError."""
    error = ValidationError(
        f"Invalid format for '{field}': got '{value}', expected {expected_format}"
    )
    error.field = field
    error.value = value
    error.expected_format = expected_format
    error.error_type = ErrorType.INVALID_DATA
    return error
