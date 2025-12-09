"""
Unified HTTP Client implementation.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import requests

from bioetl.domain.clients.base.contracts import ApiClientABC
from bioetl.domain.configs import ClientConfig


class UnifiedAPIClientImpl(ApiClientABC):
    """
    Унифицированный HTTP-клиент без промежуточных middleware-слоев.
    Делегирует вызовы напрямую базовому HTTP-клиенту.
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

    def request_call(self, method: str, url: str, **kwargs: Any) -> Any:
        """Выполнить HTTP-запрос с настройками клиента."""
        method_upper = method.upper()
        if method_upper in {"POST", "PUT", "PATCH", "DELETE"}:
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("Idempotency-Key", str(uuid4()))
            kwargs["headers"] = headers

        timeout = kwargs.pop("timeout", self.config.timeout_sec)
        return self.base_client.request(
            method=method, url=url, timeout=timeout, **kwargs
        )

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Execute a request using the configured HTTP client."""
        return self.request_call(method, url, **kwargs)

    def get_response(self, url: str, **kwargs: Any) -> Any:
        """GET запрос."""
        return self.request_call("GET", url, **kwargs)

    def request_post(self, url: str, **kwargs: Any) -> Any:
        """POST запрос."""
        return self.request_call("POST", url, **kwargs)

    def close(self) -> None:
        """Закрыть соединение."""
        if hasattr(self.base_client, "close"):
            self.base_client.close()
