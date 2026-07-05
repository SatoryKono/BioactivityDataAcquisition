from __future__ import annotations

import httpx
import pytest

from tests.contract._semanticscholar_contract_support import _request_or_skip


class _StubClient:
    def __init__(
        self,
        response: httpx.Response | None = None,
        exc: Exception | None = None,
    ) -> None:
        self._response = response
        self._exc = exc

    async def request(
        self,
        method: str,
        url: str,
        **kwargs: object,
    ) -> httpx.Response:
        del method, url, kwargs
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


@pytest.mark.asyncio
async def test_request_or_skip__http_500__skips_transient_provider_error() -> None:
    request = httpx.Request(
        "GET", "https://api.semanticscholar.org/graph/v1/paper/search"
    )
    response = httpx.Response(
        500,
        request=request,
        json={"message": "Internal Server Error"},
    )

    with pytest.raises(pytest.skip.Exception, match="HTTP 500"):
        await _request_or_skip(
            _StubClient(response=response),  # type: ignore[arg-type]
            "GET",
            str(request.url),
        )


@pytest.mark.asyncio
async def test_request_or_skip__connect_timeout__skips_endpoint_unreachable() -> None:
    request = httpx.Request(
        "GET", "https://api.semanticscholar.org/graph/v1/paper/search"
    )
    exc = httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(pytest.skip.Exception, match="not reachable"):
        await _request_or_skip(
            _StubClient(exc=exc),  # type: ignore[arg-type]
            "GET",
            str(request.url),
        )
