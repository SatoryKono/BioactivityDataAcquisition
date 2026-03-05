"""Classification helpers for adapter-level error policies."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from bioetl.domain.error_classifier import ErrorClassifier

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


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


def classify_http_error(
    status_code: int,
    *,
    logger: LoggerPort,
) -> ErrorCategory:
    """Classify HTTP status code into retryability categories."""
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


def classify_exception(
    error: Exception,
    *,
    classifier: ErrorClassifier,
    logger: LoggerPort,
) -> ErrorCategory:
    """Classify exception into adapter error category."""
    error_type = classifier.classify(error)

    if error_type.is_critical():
        logger.debug(
            "exception_classified",
            error_type=error_type.value,
            category=ErrorCategory.CRITICAL.value,
            error_class=type(error).__name__,
        )
        return ErrorCategory.CRITICAL

    if error_type.is_recoverable():
        logger.debug(
            "exception_classified",
            error_type=error_type.value,
            category=ErrorCategory.RECOVERABLE.value,
            error_class=type(error).__name__,
        )
        return ErrorCategory.RECOVERABLE

    if error_type.is_data_quality():
        logger.debug(
            "exception_classified",
            error_type=error_type.value,
            category=ErrorCategory.DATA_QUALITY.value,
            error_class=type(error).__name__,
        )
        return ErrorCategory.DATA_QUALITY

    logger.warning(
        "exception_classification_fallback",
        error_type=error_type.value,
        category=ErrorCategory.RECOVERABLE.value,
        error_class=type(error).__name__,
        reason="unknown error type, defaulting to recoverable",
    )
    return ErrorCategory.RECOVERABLE


__all__ = [
    "ErrorCategory",
    "classify_exception",
    "classify_http_error",
]
