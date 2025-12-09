"""
Unified HTTP Client implementation.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import requests

from bioetl.domain.clients.base.contracts import ApiClientABC
from bioetl.domain.configs import ClientConfig
from bioetl.domain.observability import LoggingPortABC
from bioetl.infrastructure.observability.factories import default_logging_port


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
        *,
        logger: LoggingPortABC | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.base_client = base_client or requests.Session()
        self.logger = logger or default_logging_port()
        self.logger.info(
            "http_client_initialized",
            provider=self.provider,
            timeout_sec=self.config.timeout_sec,
            max_retries=self.config.max_retries,
            backoff_factor=self.config.backoff_factor,
            rate_limit_per_sec=self.config.rate_limit_per_sec,
        )

    def request_call(self, method: str, url: str, **kwargs: Any) -> Any:
        """Выполнить HTTP-запрос с настройками клиента."""
        method_upper = method.upper()
        if method_upper in {"POST", "PUT", "PATCH", "DELETE"}:
            headers = dict(kwargs.get("headers") or {})
            headers.setdefault("Idempotency-Key", str(uuid4()))
            kwargs["headers"] = headers

        timeout = kwargs.pop("timeout", self.config.timeout_sec)
        start = time.monotonic()
        response = self.base_client.request(
            method=method, url=url, timeout=timeout, **kwargs
        )
        latency = time.monotonic() - start
        self.logger.info(
            "http_request_completed",
            provider=self.provider,
            method=method_upper,
            url=url,
            status_code=getattr(response, "status_code", None),
            latency_sec=latency,
        )
        return response

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
