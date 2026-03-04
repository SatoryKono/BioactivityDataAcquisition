"""Public HTTP verb methods for UnifiedHTTPClient."""

from __future__ import annotations

from bioetl.domain.types import JsonDict

import httpx


class HTTPClientRequestMethodsMixin:
    """Thin request verb wrappers around retry-orchestrated request flow."""

    async def get(
        self,
        url: str,
        params: JsonDict | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send GET request with retry policy."""
        return await self._request_with_retry(
            "GET", url, params=params, headers=headers
        )

    async def post(
        self,
        url: str,
        json: JsonDict | None = None,
        data: JsonDict | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send POST request with retry policy."""
        return await self._request_with_retry(
            "POST", url, json=json, data=data, headers=headers
        )

    async def head(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send HEAD request with retry policy."""
        return await self._request_with_retry("HEAD", url, headers=headers)

    async def get_once(
        self,
        url: str,
        params: JsonDict | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send single GET request without retry loop."""
        client = self._get_client()
        await self.rate_limiter.acquire()
        response = await self.circuit_breaker.call(
            client.request, "GET", url, params=params, headers=headers
        )
        response.raise_for_status()
        return response
