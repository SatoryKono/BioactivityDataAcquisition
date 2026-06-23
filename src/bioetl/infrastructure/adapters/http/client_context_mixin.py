# mypy: disable-error-code=attr-defined
"""Context-manager helpers for UnifiedHTTPClient."""

from __future__ import annotations

from types import TracebackType
from typing import Self

import httpx

from bioetl.infrastructure.adapters.base import build_json_accept_headers


class HTTPClientContextMixin:
    """Async context lifecycle and client-access helpers."""

    _client: httpx.AsyncClient | None
    _client_enter_depth: int
    user_agent: str
    contact_email: str | None
    run_id: object | None
    timeout: float
    read_timeout_multiplier: float
    max_connections: int
    max_keepalive_connections: int
    trust_env: bool

    async def __aenter__(
        self,
    ) -> Self:
        """Enter async context manager."""
        current_depth = int(getattr(self, "_client_enter_depth", 0))
        if self._client is not None and current_depth > 0:
            self._client_enter_depth = current_depth + 1
            return self
        if self._client is not None:
            # Recover from inconsistent lifecycle state before opening a new client.
            await self._client.aclose()
            self._client = None

        user_agent = self.user_agent
        if self.contact_email:
            user_agent = f"{user_agent} ({self.contact_email})"
        headers = build_json_accept_headers(
            user_agent,
            correlation_id=self.run_id,
        )

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
            trust_env=self.trust_env,
        )
        self._client_enter_depth = 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        del exc_type, exc_val, exc_tb
        current_depth = int(getattr(self, "_client_enter_depth", 0))
        if current_depth > 1:
            self._client_enter_depth = current_depth - 1
            return
        self._client_enter_depth = 0
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
