"""Error Classifier for BioETL.

Pure domain logic - classifies exceptions into error categories.
Primary classification uses the explicit error_type attribute on BioETLError subclasses.
Falls back to keyword matching for non-domain exceptions (tracked via fallback_usage_count).
"""

from __future__ import annotations

from bioetl.domain.exceptions import (
    BioETLError,
)
from bioetl.domain.types import ErrorType

__all__ = [
    "ErrorClassifier",
]

# Keyword to ErrorType mapping for legacy/external exceptions
# Maps (keywords_tuple, error_type) - first match wins
_ERROR_KEYWORDS: list[tuple[tuple[str, ...], ErrorType]] = [
    # Critical errors (infrastructure failures)
    (("LockLost", "LockAcquisition", "LockExpired"), ErrorType.LOCK_LOST),
    (
        (
            "BucketNotFound",
            "TableNotFound",
            "DBUnavailable",
            "CheckpointConflict",
            "MergeConflict",
        ),
        ErrorType.DB_UNAVAILABLE,
    ),
    (("AuthFailure", "Unauthorized", "Forbidden"), ErrorType.AUTH_FAILURE),
    # Recoverable errors (can retry)
    (("RateLimit", "TooManyRequests", "429"), ErrorType.RATE_LIMIT),
    (
        ("CircuitBreakerOpen", "Timeout", "TimeoutError", "504", "502"),
        ErrorType.TIMEOUT,
    ),
    (
        (
            "Upload",
            "NetworkError",
            "RetryExhausted",
            "ReadError",
            "WriteError",
            "ConnectError",
            "ProtocolError",
            "DecodingError",
            "TransportError",
            "StreamError",
        ),
        ErrorType.NETWORK_ERROR,
    ),
    # Data quality errors (skip record)
    (("Schema", "SchemaValidation", "Validation"), ErrorType.SCHEMA_VIOLATION),
    (("Missing", "Required", "MissingRequired"), ErrorType.MISSING_REQUIRED_FIELD),
    (("Invalid", "Malformed"), ErrorType.INVALID_DATA),
    (("DataQualityThreshold",), ErrorType.DATA_QUALITY),
]


def _match_error_type(error_name: str) -> ErrorType:
    """Match error name against keyword patterns (legacy fallback).

    Args:
        error_name: The exception class name

    Returns:
        Matched ErrorType or INVALID_DATA as default
    """
    for keywords, error_type in _ERROR_KEYWORDS:
        if any(kw in error_name for kw in keywords):
            return error_type
    return ErrorType.INVALID_DATA


class ErrorClassifier:
    """Classifies exceptions into ErrorType categories.

    This is a pure domain class that uses the centralized exception hierarchy.
    Primary classification uses the explicit error_type attribute on BioETLError subclasses.
    Falls back to keyword matching for non-domain exceptions (tracked for observability).

    Attributes:
        strict_mode: If True, raise ValueError for unknown non-domain exceptions.
        fallback_usage_count: Counter for observability - tracks keyword fallback usage.
    """

    def __init__(self, strict_mode: bool = False) -> None:
        """Initialize the error classifier.

        Args:
            strict_mode: If True, raise ValueError for unknown non-domain exceptions
                        instead of using fallback. Enable in tests for stricter validation.
        """
        self._strict_mode = strict_mode
        self._fallback_count = 0

    def classify(self, error: Exception) -> ErrorType:
        """Classify an exception into a predefined ErrorType.

        Classification strategy:
        1. If BioETLError subclass: use error_type class attribute (deterministic)
        2. For non-domain exceptions: fall back to keyword matching with warning

        Args:
            error: The exception to classify

        Returns:
            ErrorType category for the exception

        Raises:
            ValueError: In strict_mode if non-domain exception cannot be classified

        Examples:
            >>> classifier = ErrorClassifier()
            >>> from bioetl.domain.exceptions import LockLostError, SchemaViolationError
            >>> classifier.classify(LockLostError("test", "run123"))
            <ErrorType.LOCK_LOST: 'LOCK_LOST'>
            >>> classifier.classify(SchemaViolationError("users", ["error"]))
            <ErrorType.SCHEMA_VIOLATION: 'SCHEMA_VIOLATION'>
        """
        # Primary: Use explicit error_type attribute from BioETLError subclass
        if isinstance(error, BioETLError):
            return self._classify_domain_error(error)

        # Fallback: Keyword matching for non-domain exceptions
        return self._classify_external_error(error)

    def _classify_domain_error(self, error: BioETLError) -> ErrorType:
        """Classify domain exceptions using the explicit error_type attribute.

        Args:
            error: BioETLError instance

        Returns:
            ErrorType from the exception's error_type class attribute
        """
        override_error_type = getattr(error, "error_type_override", None)
        if isinstance(override_error_type, ErrorType):
            return override_error_type

        instance_error_type = getattr(error, "error_type", None)
        if isinstance(instance_error_type, ErrorType):
            return instance_error_type

        # Use the explicit error_type attribute (deterministic)
        return error.get_error_type()

    def _classify_external_error(self, error: Exception) -> ErrorType:
        """Classify non-domain exceptions using keyword matching.

        Args:
            error: Non-BioETLError exception

        Returns:
            ErrorType based on keyword matching

        Raises:
            ValueError: In strict_mode if exception cannot be classified
        """
        self._fallback_count += 1
        error_name = type(error).__name__
        result = _match_error_type(error_name)

        # In strict mode, raise for unknown exception types
        if self._strict_mode and result == ErrorType.INVALID_DATA:
            raise ValueError(
                f"Unknown exception type: {error_name}. "
                f"Consider wrapping in BioETLError subclass with explicit error_type."
            )

        return result

    @property
    def fallback_usage_count(self) -> int:
        """Number of times keyword fallback was used (for metrics/observability)."""
        return self._fallback_count

    def reset_fallback_count(self) -> None:
        """Reset the fallback counter (useful for testing)."""
        self._fallback_count = 0
