"""Error Classifier for BioETL.

Pure domain logic - classifies exceptions into error categories.
Uses both isinstance checks for domain exceptions and keyword matching
for backward compatibility with infrastructure exceptions.
"""

from bioetl.domain.exceptions import (
    BioETLError,
    CriticalError,
    DataQualityError,
    RecoverableError,
)
from bioetl.domain.types import ErrorType

# Keyword to ErrorType mapping (reduces cyclomatic complexity)
# Maps (keywords_tuple, error_type) - first match wins
_ERROR_KEYWORDS: list[tuple[tuple[str, ...], ErrorType]] = [
    # Critical errors (infrastructure failures)
    (("BucketNotFound", "TableNotFound", "DBUnavailable"), ErrorType.DB_UNAVAILABLE),
    (("AuthFailure", "Unauthorized", "Forbidden"), ErrorType.AUTH_FAILURE),
    (("LockLost", "LockExpired"), ErrorType.LOCK_LOST),
    # Recoverable errors (can retry)
    (("Upload", "MergeConflict", "NetworkError"), ErrorType.NETWORK_ERROR),
    (("RateLimit", "TooManyRequests", "429"), ErrorType.RATE_LIMIT),
    (("Timeout", "TimeoutError", "504", "502"), ErrorType.TIMEOUT),
    # Data quality errors (skip record)
    (("Schema", "Validation", "SchemaValidation"), ErrorType.SCHEMA_VIOLATION),
    (("Missing", "Required", "MissingRequired"), ErrorType.MISSING_REQUIRED_FIELD),
    (("Invalid", "Malformed"), ErrorType.INVALID_DATA),
]


def _match_error_type(error_name: str) -> ErrorType:
    """Match error name against keyword patterns.

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
    Primary classification uses isinstance checks on domain exceptions.
    Falls back to keyword matching for backward compatibility with non-domain exceptions.
    """

    def classify(self, error: Exception) -> ErrorType:
        """Classify an exception into a predefined ErrorType.

        Classification strategy:
        1. Check if error is a BioETLError subclass and use specific mappings
        2. Fall back to keyword matching on exception class name for backward compatibility

        Args:
            error: The exception to classify

        Returns:
            ErrorType category for the exception

        Examples:
            >>> classifier = ErrorClassifier()
            >>> from bioetl.domain.exceptions import LockLostError, SchemaViolationError
            >>> classifier.classify(LockLostError("test", "run123"))
            <ErrorType.LOCK_LOST: 'lock_lost'>
            >>> classifier.classify(SchemaViolationError("users", ["error"]))
            <ErrorType.SCHEMA_VIOLATION: 'schema_violation'>
        """
        # First, check if it's a BioETLError subclass
        if isinstance(error, BioETLError):
            return self._classify_domain_error(error)

        # Fall back to keyword matching for non-domain exceptions
        return _match_error_type(type(error).__name__)

    def _classify_domain_error(self, error: BioETLError) -> ErrorType:
        """Classify domain exceptions using isinstance checks.

        Args:
            error: BioETLError instance

        Returns:
            ErrorType category based on exception hierarchy
        """
        error_name = type(error).__name__

        # Check specific exception types first (most specific to least specific)
        # Critical errors
        if "LockLost" in error_name:
            return ErrorType.LOCK_LOST
        if "LockAcquisition" in error_name:
            return ErrorType.LOCK_LOST
        if "CheckpointConflict" in error_name or "MergeConflict" in error_name:
            return ErrorType.DB_UNAVAILABLE

        # Recoverable errors
        if "RateLimit" in error_name:
            return ErrorType.RATE_LIMIT
        if "CircuitBreakerOpen" in error_name:
            return ErrorType.TIMEOUT
        if "RetryExhausted" in error_name:
            return ErrorType.NETWORK_ERROR
        if "BucketNotFound" in error_name or "TableNotFound" in error_name:
            return ErrorType.DB_UNAVAILABLE
        if "Upload" in error_name:
            return ErrorType.NETWORK_ERROR

        # Data quality errors
        if "SchemaViolation" in error_name:
            return ErrorType.SCHEMA_VIOLATION
        if "MissingRequiredField" in error_name:
            return ErrorType.MISSING_REQUIRED_FIELD
        if "InvalidDataFormat" in error_name:
            return ErrorType.INVALID_DATA

        # Use hierarchy-based classification as fallback
        if isinstance(error, DataQualityError):
            return ErrorType.INVALID_DATA
        if isinstance(error, CriticalError):
            return ErrorType.DB_UNAVAILABLE
        if isinstance(error, RecoverableError):
            return ErrorType.NETWORK_ERROR

        # Default fallback
        return ErrorType.INVALID_DATA
