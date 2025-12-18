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
    (("CircuitBreakerOpen", "Timeout", "TimeoutError", "504", "502"), ErrorType.TIMEOUT),
    (("Upload", "NetworkError", "RetryExhausted"), ErrorType.NETWORK_ERROR),
    # Data quality errors (skip record)
    (("Schema", "Validation", "SchemaValidation"), ErrorType.SCHEMA_VIOLATION),
    (("Missing", "Required", "MissingRequired"), ErrorType.MISSING_REQUIRED_FIELD),
    (("Invalid", "Malformed"), ErrorType.INVALID_DATA),
    (("DataQualityThreshold",), ErrorType.DATA_QUALITY),
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
        """Classify domain exceptions using keyword matching and hierarchy fallback.

        Args:
            error: BioETLError instance

        Returns:
            ErrorType category based on exception name or hierarchy
        """
        # First try keyword-based classification
        result = _match_error_type(type(error).__name__)
        if result != ErrorType.INVALID_DATA:
            return result

        # Use hierarchy-based classification as fallback
        return self._classify_by_hierarchy(error)

    def _classify_by_hierarchy(self, error: BioETLError) -> ErrorType:
        """Classify by exception hierarchy when keyword matching fails."""
        if isinstance(error, DataQualityError):
            return ErrorType.INVALID_DATA
        if isinstance(error, CriticalError):
            return ErrorType.DB_UNAVAILABLE
        if isinstance(error, RecoverableError):
            return ErrorType.NETWORK_ERROR
        return ErrorType.INVALID_DATA
