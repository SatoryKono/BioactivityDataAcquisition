"""Error Classifier for BioETL."""

from bioetl.domain.types import ErrorType


class ErrorClassifier:
    """Classifies exceptions into ErrorType categories."""

    def classify(self, error: Exception) -> ErrorType:
        """Classify an exception into a predefined ErrorType.

        This basic implementation can be extended with a registry
        pattern to allow for more sophisticated, pipeline-specific
        classifiers.
        """
        error_name = type(error).__name__
        if "Schema" in error_name or "Validation" in error_name:
            return ErrorType.SCHEMA_VIOLATION
        elif "Missing" in error_name or "Required" in error_name:
            return ErrorType.MISSING_REQUIRED_FIELD
        else:
            return ErrorType.INVALID_DATA
