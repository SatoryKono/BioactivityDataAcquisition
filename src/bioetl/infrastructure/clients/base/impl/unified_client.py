"""
Unified HTTP Client implementation.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

import requests

from bioetl.infrastructure.clients.middleware import HttpClientMiddleware
from bioetl.infrastructure.config.models import ClientConfig


class UnifiedAPIClient:
    """
    Унифицированный HTTP-клиент.
    Обертка над HttpClientMiddleware с конфигурацией через Pydantic.
    """

    def __init__(
        self,
        provider: str,
        config: ClientConfig,
        base_client: Any | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.base_client = base_client or requests.Session()
        
        # Map config to middleware params
        # Note: HttpClientMiddleware might expect slightly different param names
        # We map them here.
        self.middleware = HttpClientMiddleware(
            provider=provider,
            base_client=self.base_client,
            max_attempts=config.max_retries,
            backoff_factor=config.backoff_factor,
            timeout=config.timeout,
            circuit_breaker_threshold=config.circuit_breaker_threshold,
            circuit_breaker_recovery_time=config.circuit_breaker_recovery_time,
        )

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Выполнить HTTP-запрос с учетом политик."""
        method_upper = method.upper()
        if method_upper in {"POST", "PUT", "PATCH", "DELETE"}:
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("Idempotency-Key", str(uuid4()))
            kwargs["headers"] = headers

        return self.middleware.request(method, url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> Any:
        """GET запрос."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        """POST запрос."""
        return self.request("POST", url, **kwargs)

    def close(self) -> None:
        """Закрыть соединение."""
        if hasattr(self.base_client, "close"):
            self.base_client.close()

