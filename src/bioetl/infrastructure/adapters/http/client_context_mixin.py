# mypy: disable-error-code=no-any-return
"""Context-manager helpers for UnifiedHTTPClient."""

from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx


class HTTPClientContextMixin:
    """Async context lifecycle and client-access helpers."""

    _client: httpx.AsyncClient | None

    async def __aenter__(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> Any:  # Any: mixin self type is provided structurally by composed adapter class
        """Enter async context manager."""
        user_agent = self.user_agent
        if self.contact_email:
            user_agent = f"{user_agent} ({self.contact_email})"
        headers: dict[str, str] = {
            "User-Agent": user_agent,
            "Accept": "application/json",
        }
        if self.run_id:
            headers["X-Correlation-ID"] = str(self.run_id)

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout),
            headers=headers,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
            ),
        )
        return self

    async def __aexit__(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        del exc_type, exc_val, exc_tb
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_client(
        self: Any,  # Any: mixin self type is provided structurally by composed adapter class
    ) -> (
        httpx.AsyncClient
    ):  # Any: mixin self type is provided structurally by composed adapter class
        """Get httpx client, raising if client not entered."""
        if self._client is None:
            raise RuntimeError(
                "UnifiedHTTPClient must be used within async context manager"
            )
        return self._client
