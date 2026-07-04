# mypy: disable-error-code=attr-defined
"""Public HTTP verb methods for UnifiedHTTPClient."""

from __future__ import annotations

from typing import Any, cast

import httpx

from bioetl.domain.types import JsonDict


class HTTPClientRequestMethodsMixin:
    """Thin request verb wrappers around retry-orchestrated request flow."""

    rate_limiter: Any  # Any: mixed-in concrete type provides async acquire()
    circuit_breaker: Any  # Any: mixed-in concrete type provides async call()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,  # Any: forwarded request kwargs
    ) -> httpx.Response:
        """Implemented by HTTP retry mixin."""
        raise NotImplementedError

    def _get_client(self) -> httpx.AsyncClient:
        """Implemented by HTTP context mixin."""
        raise NotImplementedError

    async def get(
        self,
        url: str,
        params: JsonDict | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send GET request with retry policy.

        Args:
            url: Target URL for the request.
            params: Optional query parameters to append to the URL.
            headers: Optional additional HTTP headers.

        Returns:
            httpx.Response from the server after applying retry policy.
        """
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
        """Send POST request with retry policy.

        Args:
            url: Target URL for the request.
            json: Optional JSON payload to send as request body.
            data: Optional form data to send as request body.
            headers: Optional additional HTTP headers.

        Returns:
            httpx.Response from the server after applying retry policy.
        """
        return await self._request_with_retry(
            "POST", url, json=json, data=data, headers=headers
        )

    async def head(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send HEAD request with retry policy.

        Args:
            url: Target URL for the request.
            headers: Optional additional HTTP headers.

        Returns:
            httpx.Response from the server after applying retry policy.
        """
        return await self._request_with_retry("HEAD", url, headers=headers)

    async def get_once(
        self,
        url: str,
        params: JsonDict | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Send single GET request without retry loop.

        Args:
            url: Target URL for the request.
            params: Optional query parameters to append to the URL.
            headers: Optional additional HTTP headers.

        Returns:
            httpx.Response from the server, raises on non-2xx status.
        """
        client = self._get_client()
        await self.rate_limiter.acquire()
        response = await self.circuit_breaker.call(
            client.request, "GET", url, params=params, headers=headers
        )
        typed_response = cast("httpx.Response", response)
        typed_response.raise_for_status()
        return typed_response
