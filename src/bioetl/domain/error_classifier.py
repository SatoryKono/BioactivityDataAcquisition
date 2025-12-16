"""Error Classifier for BioETL."""

from bioetl.domain.types import ErrorType

# Keyword to ErrorType mapping (reduces cyclomatic complexity)
_ERROR_KEYWORDS: list[tuple[tuple[str, ...], ErrorType]] = [
    (("Schema", "Validation"), ErrorType.SCHEMA_VIOLATION),
    (("Missing", "Required"), ErrorType.MISSING_REQUIRED_FIELD),
]


def _match_error_type(error_name: str) -> ErrorType:
    """Match error name against keyword patterns."""
    for keywords, error_type in _ERROR_KEYWORDS:
        if any(kw in error_name for kw in keywords):
            return error_type
    return ErrorType.INVALID_DATA


class ErrorClassifier:
    """Classifies exceptions into ErrorType categories."""

    def classify(self, error: Exception) -> ErrorType:
        """Classify an exception into a predefined ErrorType.

        This basic implementation can be extended with a registry
        pattern to allow for more sophisticated, pipeline-specific
        classifiers.
        """
        return _match_error_type(type(error).__name__)
