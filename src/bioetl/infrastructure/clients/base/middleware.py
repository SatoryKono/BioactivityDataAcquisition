"""HTTP middleware for client error handling and retries."""
from __future__ import annotations

import logging
import time
from typing import Any, Protocol

from bioetl.domain.errors import (
    ClientNetworkError,
    ClientRateLimitError,
    ClientResponseError,
)
from bioetl.infrastructure.clients.base.contracts import RetryPolicyABC


class _HttpClient(Protocol):
    def get(self, url: str) -> Any:  # pragma: no cover - Protocol definition
        ...


class HttpClientMiddleware:
    """Обертка для HTTP-клиента с обработкой ошибок и ретраями."""

    def __init__(
        self,
        provider: str,
        http_client: _HttpClient,
        retry_policy: RetryPolicyABC,
        logger: logging.Logger | None = None,
    ) -> None:
        self._provider = provider
        self._http_client = http_client
        self._retry_policy = retry_policy
        self._logger = logger or logging.getLogger(__name__)

    def request(self, url: str) -> Any:
        """Выполняет GET-запрос с обработкой сетевых и HTTP-ошибок."""

        attempt = 1
        while True:
            try:
                response = self._http_client.get(url)
            except TimeoutError as exc:  # pragma: no cover - covered by tests
                error = ClientNetworkError(
                    provider=self._provider,
                    endpoint=url,
                    message=str(exc),
                    cause=exc,
                )
            else:
                status_code = getattr(response, "status_code", None)
                if status_code == 429:
                    error = ClientRateLimitError(
                        provider=self._provider,
                        endpoint=url,
                        status_code=status_code,
                        message="Rate limit exceeded",
                    )
                elif status_code is not None and status_code >= 500:
                    error = ClientResponseError(
                        provider=self._provider,
                        endpoint=url,
                        status_code=status_code,
                        message="Server error",
                    )
                else:
                    try:
                        return response.json()
                    except Exception as exc:  # pragma: no cover - defensive
                        error = ClientResponseError(
                            provider=self._provider,
                            endpoint=url,
                            status_code=status_code,
                            message="Failed to parse response JSON",
                            cause=exc,
                        )

            self._logger.warning(
                "HTTP request failed",
                extra={"attempt": attempt, "error_type": type(error).__name__},
            )

            if not self._retry_policy.should_retry(error, attempt):
                raise error from error.cause

            delay = self._retry_policy.get_delay(attempt)
            self._logger.info(
                "Retrying request", extra={"attempt": attempt + 1, "delay": delay}
            )
            time.sleep(delay)
            attempt += 1

