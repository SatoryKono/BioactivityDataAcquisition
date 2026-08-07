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

    def __init__(
        self,
        message: str,
        record_id: str | None = None,
        field: str | None = None,
    ) -> None:
        """Initialize ValidationError.

        Args:
            message: Human-readable error message.
            record_id: Optional ID of the affected record.
            field: Optional name of the field with validation error.
        """
        super().__init__(message)
        # Always present so callers can access without AttributeError.
        self.record_id = record_id
        self.field = field


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

    def __init__(
        self,
        table: str,
        errors: list[str],
        record_id: str | None = None,
    ) -> None:
        """Initialize SchemaViolationError.

        Args:
            table: Name of the table or entity with schema violation.
            errors: List of specific validation error messages.
            record_id: Optional ID of the affected record.
        """
        self.table = table
        self.errors = errors
        super().__init__(
            f"Schema validation failed for '{table}': {errors}",
            record_id=record_id,
        )
