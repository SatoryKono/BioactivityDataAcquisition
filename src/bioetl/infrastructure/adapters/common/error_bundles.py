"""Shared exception bundles reused across adapter families."""

from __future__ import annotations

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError

__all__ = [
    "COMMON_ADAPTER_HEALTH_ERRORS",
    "COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR",
    "COMMON_TITLE_FALLBACK_ERRORS",
]

COMMON_ADAPTER_HEALTH_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    HTTPStatusError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    Exception,
)

COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR = (
    BioETLError,
    NetworkError,
    RequestError,
    HTTPStatusError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
    Exception,
)

COMMON_TITLE_FALLBACK_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
)
