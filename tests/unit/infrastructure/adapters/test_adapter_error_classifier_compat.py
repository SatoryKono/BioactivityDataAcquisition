"""Unit tests for adapter _error_classifier compatibility shim."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_adapter_error_classifier_shim_reexports_canonical_symbols() -> None:
    """Legacy _error_classifier module should re-export canonical helpers."""
    from bioetl.infrastructure.adapters import _error_classifier
    from bioetl.infrastructure.adapters._error_classifier import (
        ErrorCategory,
        classify_exception,
        classify_http_error,
    )
    from bioetl.infrastructure.adapters.adapter_error_classifier import (
        ErrorCategory as CanonicalErrorCategory,
    )
    from bioetl.infrastructure.adapters.adapter_error_classifier import (
        classify_exception as CanonicalClassifyException,
    )
    from bioetl.infrastructure.adapters.adapter_error_classifier import (
        classify_http_error as CanonicalClassifyHttpError,
    )

    assert ErrorCategory is CanonicalErrorCategory
    assert classify_exception is CanonicalClassifyException
    assert classify_http_error is CanonicalClassifyHttpError
    assert _error_classifier.__all__ == [
        "ErrorCategory",
        "classify_exception",
        "classify_http_error",
    ]
