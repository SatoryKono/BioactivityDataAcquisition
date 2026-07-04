"""Shared exception bundles reused across adapter families."""

from __future__ import annotations

import httpx
from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import (
    BioETLError,
    ExternalServiceError,
    NetworkError,
    RetryExhaustedError,
)

__all__ = [
    "COMMON_ADAPTER_FETCH_RESILIENCE_ERRORS",
    "COMMON_ADAPTER_HEALTH_ERRORS",
    "COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR",
    "COMMON_TITLE_FALLBACK_ERRORS",
    "build_common_network_error_bundle",
]


def build_common_network_error_bundle(
    *extra_errors: type[BaseException],
) -> tuple[type[BaseException], ...]:
    """Return the canonical network/runtime error bundle shared by adapters."""
    return (
        BioETLError,
        NetworkError,
        RequestError,
        *extra_errors,
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
    )

COMMON_ADAPTER_FETCH_RESILIENCE_ERRORS = (
    BioETLError,
    ExternalServiceError,
    RetryExhaustedError,
    httpx.HTTPError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
    AttributeError,
    Exception,
)

COMMON_ADAPTER_HEALTH_ERRORS = build_common_network_error_bundle(
    HTTPStatusError,
    Exception,
)

COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR = build_common_network_error_bundle(
    HTTPStatusError,
    KeyError,
    Exception,
)

COMMON_TITLE_FALLBACK_ERRORS = build_common_network_error_bundle(KeyError)
