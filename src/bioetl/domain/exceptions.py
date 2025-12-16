"""Domain exceptions with error type classification.

Provides a hierarchy of exceptions that can be classified by ErrorType
for proper handling in the pipeline executor.
"""
from bioetl.domain.types import ErrorType


class BioETLError(Exception):
    """Base exception for all BioETL errors.

    Subclasses define their error_type for automatic classification.
    """

    error_type: ErrorType = ErrorType.INVALID_DATA

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# Critical errors (fail pipeline immediately)

class AuthenticationError(BioETLError):
    """API authentication failed (401, 403)."""
    error_type = ErrorType.AUTH_FAILURE


class GoldSchemaError(BioETLError):
    """Gold layer schema validation failed."""
    error_type = ErrorType.SCHEMA_MISMATCH_GOLD


class DatabaseUnavailableError(BioETLError):
    """Database connection failed."""
    error_type = ErrorType.DB_UNAVAILABLE


class LockLostError(BioETLError):
    """Distributed lock lost during execution."""
    error_type = ErrorType.LOCK_LOST


# Recoverable errors (retry with backoff)

class RateLimitError(BioETLError):
    """API rate limit exceeded (429)."""
    error_type = ErrorType.RATE_LIMIT


class TimeoutError(BioETLError):
    """Request timeout (502, 504)."""
    error_type = ErrorType.TIMEOUT


class NetworkError(BioETLError):
    """Network connectivity issue."""
    error_type = ErrorType.NETWORK_ERROR


# Data quality errors (log + skip record)

class SchemaViolationError(BioETLError):
    """Record failed schema validation."""
    error_type = ErrorType.SCHEMA_VIOLATION


class InvalidDataError(BioETLError):
    """Invalid data format (e.g., malformed SMILES)."""
    error_type = ErrorType.INVALID_DATA


class MissingRequiredFieldError(BioETLError):
    """Required field is missing or null."""
    error_type = ErrorType.MISSING_REQUIRED_FIELD
