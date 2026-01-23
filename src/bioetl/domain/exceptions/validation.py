"""Validation exceptions for schema and data format errors.

These errors indicate that data does not conform to expected schemas or formats.
ValidationErrors are typically recoverable at the record level - individual invalid
records can be logged and skipped while processing continues for other records.

Категория: ValidationErrors - ошибки валидации данных и схем (нарушение формата,
отсутствующие поля и т.п.).
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import DataQualityError
from bioetl.domain.types import ErrorType


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


class MissingRequiredFieldError(ValidationError):
    """Raised when a required field is missing from a data record.

    Attributes:
        field: Name of the missing required field.
        record_id: Optional identifier of the affected record.

    Example:
        >>> raise MissingRequiredFieldError("molecule_chembl_id", record_id="CHEMBL25")
    """

    error_type = ErrorType.MISSING_REQUIRED_FIELD

    def __init__(self, field: str, record_id: str | None = None) -> None:
        """Initialize MissingRequiredFieldError.

        Args:
            field: Name of the missing required field.
            record_id: Optional identifier of the affected record.
        """
        self.field = field
        self.record_id = record_id
        msg = f"Missing required field: {field}"
        if record_id:
            msg += f" (record_id={record_id})"
        super().__init__(msg)


class InvalidDataFormatError(ValidationError):
    """Raised when data format is invalid.

    Indicates that a field value does not match its expected format,
    such as an invalid date string or malformed identifier.

    Attributes:
        field: Name of the field with invalid format.
        value: The actual invalid value.
        expected_format: Description of the expected format.

    Example:
        >>> raise InvalidDataFormatError("date", "2024/01/01", "ISO 8601 (YYYY-MM-DD)")
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(self, field: str, value: str, expected_format: str) -> None:
        """Initialize InvalidDataFormatError.

        Args:
            field: Name of the field with invalid format.
            value: The actual invalid value.
            expected_format: Description of the expected format.
        """
        self.field = field
        self.value = value
        self.expected_format = expected_format
        super().__init__(
            f"Invalid format for '{field}': got '{value}', expected {expected_format}"
        )
