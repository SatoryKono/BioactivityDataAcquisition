from __future__ import annotations

import httpx
import pytest

from tests.contract.test_chembl_contract import _request_or_skip


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
async def test_request_or_skip_does_not_mask_http_500() -> None:
    request = httpx.Request("GET", "https://example.org/chembl")
    response = httpx.Response(500, request=request, text="upstream failure")

    result = await _request_or_skip(
        _StubClient(response=response),  # type: ignore[arg-type]
        "GET",
        str(request.url),
    )

    assert result.status_code == 500


@pytest.mark.asyncio
async def test_request_or_skip_skips_on_rate_limit() -> None:
    request = httpx.Request("GET", "https://example.org/chembl")
    response = httpx.Response(429, request=request, text="rate limited")

    with pytest.raises(pytest.skip.Exception, match="HTTP 429"):
        await _request_or_skip(
            _StubClient(response=response),  # type: ignore[arg-type]
            "GET",
            str(request.url),
        )


@pytest.mark.asyncio
async def test_request_or_skip_skips_on_connect_timeout() -> None:
    request = httpx.Request("GET", "https://example.org/chembl")
    exc = httpx.ConnectTimeout("timed out", request=request)

    with pytest.raises(pytest.skip.Exception, match="not reachable"):
        await _request_or_skip(
            _StubClient(exc=exc),  # type: ignore[arg-type]
            "GET",
            str(request.url),
        )
