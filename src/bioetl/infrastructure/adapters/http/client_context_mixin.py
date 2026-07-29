# mypy: disable-error-code=attr-defined
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Context-manager helpers for UnifiedHTTPClient."""

from __future__ import annotations

from types import TracebackType
from typing import Self

import httpx

from bioetl.infrastructure.adapters.base import build_json_accept_headers


class HTTPClientContextMixin:
    """Async context lifecycle and client-access helpers."""

    # Annotation-only host surface. Do not seed numeric counters with class-level
    # None: getattr(self, name, 0) still returns None when the class attr is None.
    _client: httpx.AsyncClient | None  # pyright: ignore[reportUninitializedInstanceVariable]
    _client_enter_depth: int  # pyright: ignore[reportUninitializedInstanceVariable]
    user_agent: str  # pyright: ignore[reportUninitializedInstanceVariable]
    contact_email: str | None  # pyright: ignore[reportUninitializedInstanceVariable]
    run_id: object | None  # pyright: ignore[reportUninitializedInstanceVariable]
    timeout: float  # pyright: ignore[reportUninitializedInstanceVariable]
    read_timeout_multiplier: float  # pyright: ignore[reportUninitializedInstanceVariable]
    max_connections: int  # pyright: ignore[reportUninitializedInstanceVariable]
    max_keepalive_connections: int  # pyright: ignore[reportUninitializedInstanceVariable]
    trust_env: bool  # pyright: ignore[reportUninitializedInstanceVariable]

    def _enter_depth(self) -> int:
        """Return nested enter depth, treating unset/None as zero."""
        raw = getattr(self, "_client_enter_depth", 0)
        return 0 if raw is None else int(raw)

    async def __aenter__(
        self,
    ) -> Self:
        """Enter async context manager."""
        current_depth = self._enter_depth()
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
        current_depth = self._enter_depth()
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
