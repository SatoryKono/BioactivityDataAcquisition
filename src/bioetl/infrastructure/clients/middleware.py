from __future__ import annotations

import logging
import random
import time
from typing import Any

from bioetl.domain.errors import (
    ClientNetworkError,
    ClientRateLimitError,
    ClientResponseError,
)

try:  # pragma: no cover - optional dependency
    import httpx

    HTTPX_TIMEOUT_ERRORS = (httpx.TimeoutException,)
    HTTPX_CONNECTION_ERRORS = (httpx.ConnectError, httpx.NetworkError)
    HTTPX_HTTP_ERRORS = (httpx.HTTPStatusError,)
except Exception:  # pragma: no cover - fallback when httpx is absent
    HTTPX_TIMEOUT_ERRORS: tuple[type[Exception], ...] = tuple()
    HTTPX_CONNECTION_ERRORS: tuple[type[Exception], ...] = tuple()
    HTTPX_HTTP_ERRORS: tuple[type[Exception], ...] = tuple()

try:  # pragma: no cover - optional dependency
    from requests import exceptions as requests_exceptions

    REQUESTS_TIMEOUT_ERRORS = (requests_exceptions.Timeout,)
    REQUESTS_CONNECTION_ERRORS = (requests_exceptions.ConnectionError,)
    REQUESTS_HTTP_ERRORS = (requests_exceptions.HTTPError,)
except Exception:  # pragma: no cover - fallback when requests is absent
    REQUESTS_TIMEOUT_ERRORS = tuple()
    REQUESTS_CONNECTION_ERRORS = tuple()
    REQUESTS_HTTP_ERRORS = tuple()

__all__ = ["HttpClientMiddleware"]


class HttpClientMiddleware:
    """HTTP client wrapper with retry/backoff, timeout and structured logging."""

    def __init__(
        self,
        provider: str,
        base_client: Any,
        *,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        timeout: float = 30.0,
    ) -> None:
        self.provider = provider
        self.base_client = base_client
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.timeout = timeout
        self.logger = logging.getLogger(f"bioetl.clients.{provider}")

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        attempt = 1
        while attempt <= self.max_attempts:
            start = time.perf_counter()
            try:
                response = self.base_client.request(
                    method=method,
                    url=url,
                    timeout=kwargs.pop("timeout", self.timeout),
                    **kwargs,
                )
                elapsed = time.perf_counter() - start
            except self._timeout_exceptions as exc:
                elapsed = time.perf_counter() - start
                error = ClientNetworkError(
                    provider=self.provider,
                    endpoint=url,
                    message="Request timed out",
                    cause=exc,
                )
                if self._handle_retry(error, method, url, elapsed, attempt):
                    attempt += 1
                    continue
                raise error from error.cause
            except self._connection_exceptions as exc:
                elapsed = time.perf_counter() - start
                error = ClientNetworkError(
                    provider=self.provider,
                    endpoint=url,
                    message="Connection error",
                    cause=exc,
                )
                if self._handle_retry(error, method, url, elapsed, attempt):
                    attempt += 1
                    continue
                raise error from error.cause
            except Exception as exc:  # pragma: no cover - unexpected errors
                elapsed = time.perf_counter() - start
                self._log_failure(
                    method,
                    url,
                    elapsed,
                    attempt - 1,
                    None,
                    exc.__class__.__name__,
                )
                raise

            status_code = getattr(response, "status_code", None)
            if status_code is not None and self._is_retryable_status(status_code):
                error = self._map_status_error(status_code, url)
                if self._handle_retry(error, method, url, elapsed, attempt, status_code):
                    attempt += 1
                    continue
                raise error

            try:
                response.raise_for_status()
            except self._http_errors as exc:
                status_code = self._extract_status_code(exc)
                error = self._map_http_error(status_code, url, exc)
                if status_code is not None and self._is_retryable_status(status_code):
                    if self._handle_retry(error, method, url, elapsed, attempt, status_code):
                        attempt += 1
                        continue
                self._log_failure(
                    method,
                    url,
                    elapsed,
                    attempt - 1,
                    status_code,
                    error.__class__.__name__,
                )
                raise error from error.cause

            self._log_success(method, url, elapsed, attempt - 1, status_code)
            return response

        raise RuntimeError("Exceeded maximum retry attempts without returning a response")

    def _handle_retry(
        self,
        error: ClientNetworkError | ClientRateLimitError | ClientResponseError,
        method: str,
        url: str,
        elapsed: float,
        attempt: int,
        status_code: int | None = None,
    ) -> bool:
        self._log_failure(
            method,
            url,
            elapsed,
            attempt - 1,
            status_code,
            error.__class__.__name__,
        )
        if attempt >= self.max_attempts:
            return False
        delay = self._backoff_delay(attempt)
        time.sleep(delay)
        return True

    def _backoff_delay(self, attempt: int) -> float:
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        jitter = random.uniform(0.0, delay)
        return min(delay + jitter, self.max_delay)

    @property
    def _timeout_exceptions(self) -> tuple[type[Exception], ...]:
        return (TimeoutError,) + REQUESTS_TIMEOUT_ERRORS + HTTPX_TIMEOUT_ERRORS

    @property
    def _connection_exceptions(self) -> tuple[type[Exception], ...]:
        return REQUESTS_CONNECTION_ERRORS + HTTPX_CONNECTION_ERRORS

    @property
    def _http_errors(self) -> tuple[type[Exception], ...]:
        return REQUESTS_HTTP_ERRORS + HTTPX_HTTP_ERRORS

    def _map_status_error(self, status_code: int, url: str) -> ClientRateLimitError | ClientResponseError:
        if status_code == 429:
            return ClientRateLimitError(
                provider=self.provider,
                endpoint=url,
                status_code=status_code,
                message="Rate limit exceeded",
            )
        return ClientResponseError(
            provider=self.provider,
            endpoint=url,
            status_code=status_code,
            message="Server error",
        )

    def _map_http_error(
        self,
        status_code: int | None,
        url: str,
        exc: Exception,
    ) -> ClientRateLimitError | ClientResponseError:
        if status_code == 429:
            return ClientRateLimitError(
                provider=self.provider,
                endpoint=url,
                status_code=status_code,
                message="Rate limit exceeded",
                cause=exc,
            )
        return ClientResponseError(
            provider=self.provider,
            endpoint=url,
            status_code=status_code,
            message=str(exc),
            cause=exc,
        )

    def _is_retryable_status(self, status_code: int) -> bool:
        return status_code == 429 or 500 <= status_code < 600

    def _extract_status_code(self, exc: Exception) -> int | None:
        response = getattr(exc, "response", None)
        return getattr(response, "status_code", None)

    def _log_success(
        self,
        method: str,
        url: str,
        elapsed: float,
        retry_count: int,
        status_code: int | None,
    ) -> None:
        self.logger.info(
            "HTTP request succeeded",
            extra={
                "provider": self.provider,
                "method": method.upper(),
                "url": url,
                "status_code": status_code,
                "elapsed": elapsed,
                "retry_count": retry_count,
                "error_type": None,
            },
        )

    def _log_failure(
        self,
        method: str,
        url: str,
        elapsed: float,
        retry_count: int,
        status_code: int | None,
        error_type: str,
    ) -> None:
        self.logger.warning(
            "HTTP request failed",
            extra={
                "provider": self.provider,
                "method": method.upper(),
                "url": url,
                "status_code": status_code,
                "elapsed": elapsed,
                "retry_count": retry_count,
                "error_type": error_type,
            },
        )
