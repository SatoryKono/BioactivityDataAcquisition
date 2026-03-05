"""Compatibility re-export for adapter error classification helpers."""

from __future__ import annotations

from bioetl.infrastructure.adapters.adapter_error_classifier import (
    ErrorCategory,
    classify_exception,
    classify_http_error,
)

__all__ = [
    "ErrorCategory",
    "classify_exception",
    "classify_http_error",
]
