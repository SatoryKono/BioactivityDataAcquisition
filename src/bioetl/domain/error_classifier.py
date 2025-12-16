"""Error Classifier for BioETL.

Pure domain logic - no infrastructure dependencies.
Uses keyword matching on exception class names to classify errors.
"""

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

    This is a pure domain class with no infrastructure dependencies.
    Classification is done via keyword matching on exception class names,
    allowing infrastructure exceptions to be classified without importing them.
    """

    def classify(self, error: Exception) -> ErrorType:
        """Classify an exception into a predefined ErrorType.

        Uses keyword matching on the exception class name to determine
        the error category. This approach avoids coupling the domain
        layer to specific infrastructure exception types.

        Args:
            error: The exception to classify

        Returns:
            ErrorType category for the exception
        """
        return _match_error_type(type(error).__name__)
