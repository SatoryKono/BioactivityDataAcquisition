# mypy: disable-error-code=attr-defined
"""Context-manager helpers for UnifiedHTTPClient."""

from __future__ import annotations

from types import TracebackType
from typing import Self

import httpx


class HTTPClientContextMixin:
    """Async context lifecycle and client-access helpers."""

    _client: httpx.AsyncClient | None
    user_agent: str
    contact_email: str | None
    run_id: object | None
    timeout: float
    read_timeout_multiplier: float
    max_connections: int
    max_keepalive_connections: int

    async def __aenter__(
        self,
    ) -> Self:
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
            timeout=httpx.Timeout(
                connect=self.timeout,
                read=self.timeout * self.read_timeout_multiplier,
                write=self.timeout,
                pool=self.timeout,
            ),
            headers=headers,
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
            ),
        )
        return self

    async def __aexit__(
        self,
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
        self,
    ) -> httpx.AsyncClient:
        """Get httpx client, raising if client not entered.

        Returns:
            Active httpx.AsyncClient instance, raises RuntimeError if not in context manager.
        """
        if self._client is None:
            raise RuntimeError(
                "UnifiedHTTPClient must be used within async context manager"
            )
        return self._client
