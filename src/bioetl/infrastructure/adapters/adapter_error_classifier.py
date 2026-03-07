"""Adapter-facing error taxonomy classifier."""

from __future__ import annotations

from enum import StrEnum

from bioetl.domain.ports import ErrorClassifierPort, LoggerPort

__all__ = [
    "AdapterErrorClassifier",
    "ErrorCategory",
    "classify_exception",
    "classify_http_error",
]


class ErrorCategory(StrEnum):
    """Error categories driving pipeline failure/retry/skip policy."""

    CRITICAL = "CRITICAL"
    RECOVERABLE = "RECOVERABLE"
    DATA_QUALITY = "DATA_QUALITY"


_HTTP_STATUS_CATEGORIES: dict[int, ErrorCategory] = {
    401: ErrorCategory.CRITICAL,
    403: ErrorCategory.CRITICAL,
    429: ErrorCategory.RECOVERABLE,
    500: ErrorCategory.RECOVERABLE,
    502: ErrorCategory.RECOVERABLE,
    503: ErrorCategory.RECOVERABLE,
    504: ErrorCategory.RECOVERABLE,
    400: ErrorCategory.DATA_QUALITY,
    404: ErrorCategory.DATA_QUALITY,
    422: ErrorCategory.DATA_QUALITY,
}


class AdapterErrorClassifier:
    """Classify HTTP status and exceptions into adapter error categories."""

    def __init__(
        self,
        *,
        classifier: ErrorClassifierPort,
        logger: LoggerPort,
    ) -> None:
        self._classifier = classifier
        self._logger = logger

    def classify(
        self,
        *,
        error: Exception,
        status_code: int | None = None,
    ) -> ErrorCategory:
        """Classify adapter error context using status code precedence.

        Returns:
            ErrorCategory based on status code (if provided) or exception type.
        """
        if status_code is not None:
            return self.classify_http_status(status_code)
        return self.classify_exception(error)

    def classify_http_status(self, status_code: int) -> ErrorCategory:
        """Classify HTTP status code into retryability categories.

        Returns:
            ErrorCategory indicating whether the HTTP error is critical, recoverable, or a data quality issue.
        """
        return _classify_http_status(status_code=status_code, logger=self._logger)

    def classify_exception(self, error: Exception) -> ErrorCategory:
        """Classify exception into adapter error category.

        Returns:
            ErrorCategory based on the exception type (critical, recoverable, or data quality).
        """
        error_type = self._classifier.classify(error)

        if error_type.is_critical():
            self._logger.debug(
                "exception_classified",
                error_type=error_type.value,
                category=ErrorCategory.CRITICAL.value,
                error_class=type(error).__name__,
            )
            return ErrorCategory.CRITICAL

        if error_type.is_recoverable():
            self._logger.debug(
                "exception_classified",
                error_type=error_type.value,
                category=ErrorCategory.RECOVERABLE.value,
                error_class=type(error).__name__,
            )
            return ErrorCategory.RECOVERABLE

        if error_type.is_data_quality():
            self._logger.debug(
                "exception_classified",
                error_type=error_type.value,
                category=ErrorCategory.DATA_QUALITY.value,
                error_class=type(error).__name__,
            )
            return ErrorCategory.DATA_QUALITY

        self._logger.warning(
            "exception_classification_fallback",
            error_type=error_type.value,
            category=ErrorCategory.RECOVERABLE.value,
            error_class=type(error).__name__,
            reason="unknown error type, defaulting to recoverable",
        )
        return ErrorCategory.RECOVERABLE


def _classify_http_status(
    *,
    status_code: int,
    logger: LoggerPort,
) -> ErrorCategory:
    """Classify HTTP status code into retryability categories.

    Returns:
        ErrorCategory based on the HTTP status code value.
    """
    if status_code in _HTTP_STATUS_CATEGORIES:
        return _HTTP_STATUS_CATEGORIES[status_code]

    if 400 <= status_code < 500:
        logger.debug(
            "http_error_classified_by_range",
            status_code=status_code,
            category=ErrorCategory.DATA_QUALITY.value,
            reason="4xx client error (not in explicit mapping)",
        )
        return ErrorCategory.DATA_QUALITY

    if status_code >= 500:
        logger.debug(
            "http_error_classified_by_range",
            status_code=status_code,
            category=ErrorCategory.RECOVERABLE.value,
            reason="5xx server error (not in explicit mapping)",
        )
        return ErrorCategory.RECOVERABLE

    logger.warning(
        "http_error_unknown_status_code",
        status_code=status_code,
        category=ErrorCategory.RECOVERABLE.value,
        reason="unknown status code, defaulting to recoverable",
    )
    return ErrorCategory.RECOVERABLE


def classify_http_error(
    status_code: int,
    *,
    logger: LoggerPort,
) -> ErrorCategory:
    """Compatibility wrapper for status-code classification.

    Returns:
        ErrorCategory for the given HTTP status code.
    """
    return _classify_http_status(status_code=status_code, logger=logger)


def classify_exception(
    error: Exception,
    *,
    classifier: ErrorClassifierPort,
    logger: LoggerPort,
) -> ErrorCategory:
    """Compatibility wrapper for exception classification.

    Returns:
        ErrorCategory based on the exception type.
    """
    adapter_classifier = AdapterErrorClassifier(classifier=classifier, logger=logger)
    return adapter_classifier.classify_exception(error)
