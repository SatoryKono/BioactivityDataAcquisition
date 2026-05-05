"""Internal contracts and shared helpers for CrossRef batch workflows."""

from __future__ import annotations

import contextlib
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Protocol

from httpx import RequestError, Response

from bioetl.domain.exceptions import BioETLError, NetworkError
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )


class HttpTransport(Protocol):
    """Minimal async HTTP transport required by the batch helpers."""

    async def get(
        self,
        url: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Execute one HTTP GET request and return the raw response."""
        ...


class BaseMetrics(Protocol):
    """Minimal metrics wrapper used around request timing."""

    def measure_request(self, route: str) -> AbstractContextManager[object]:
        """Return a timing context manager for one logical CrossRef route."""
        _ = route
        raise NotImplementedError


class HeadersProvider(Protocol):
    """Callable wrapper for request headers construction."""

    def __call__(self) -> dict[str, str]: ...


CROSSREF_RUNTIME_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    ConnectionError,
    TimeoutError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    KeyError,
)
CROSSREF_FALLBACK_ERRORS = (CrossRefApiError, *CROSSREF_RUNTIME_ERRORS)


def record_response_timing(
    request_collector: APIRequestCollector | None,
    response: Response | None,
    duration_ms: float,
) -> None:
    """Record API request timing for metadata enrichment if collector present."""
    if request_collector and response is not None:
        with contextlib.suppress(Exception):
            request_collector.record_from_response(response, duration_ms)
