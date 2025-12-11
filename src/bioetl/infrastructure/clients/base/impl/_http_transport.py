"""
Unified HTTP Client implementation.
"""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

import requests

from bioetl.domain.configs import HttpClientConfig
from bioetl.domain.observability import LoggingPortABC, MetricsPortABC
from bioetl.infrastructure.clients.base.http_error_handler import (
    DefaultHttpErrorHandler,
    HttpErrorHandlerABC,
    RequestContext,
)
from bioetl.infrastructure.errors import (
    ApiClientError,
    ApiTimeoutError,
    wrap_http_errors,
)
from bioetl.infrastructure.http import ExponentialRetryPolicy
from bioetl.infrastructure.settings.metrics import MetricName


class _HttpTransport:
    """
    Внутренний HTTP-транспорт без промежуточных middleware-слоев.
    Делегирует вызовы напрямую базовому HTTP-клиенту.

    All dependencies must be explicitly injected - no default fallbacks.
    Use composition root or factories to create instances.
    """

    def __init__(
        self,
        provider: str,
        config: HttpClientConfig,
        base_client: Any,
        logger: LoggingPortABC,
        metrics: MetricsPortABC,
        error_handler: HttpErrorHandlerABC | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.base_client = base_client
        self.logger = logger
        self.metrics = metrics
        self.error_handler = error_handler or DefaultHttpErrorHandler(logger)
        attempts = max(1, int(config.max_retries) + 1)
        self.retry_policy = (
            ExponentialRetryPolicy(
                max_attempts=attempts,
                backoff_factor=float(config.backoff_factor),
            )
            if config.retry_enabled
            else None
        )
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
        start = time.monotonic()
        status_label = "unknown"

        try:
            with wrap_http_errors(
                provider=self.provider, endpoint=url, logger=self.logger
            ) as context:
                method_upper = method.upper()
                if method_upper in {"POST", "PUT", "PATCH", "DELETE"}:
                    headers = dict(kwargs.get("headers") or {})
                    headers.setdefault("Idempotency-Key", str(uuid4()))
                    kwargs["headers"] = headers

                timeout = kwargs.pop("timeout", self.config.timeout_sec)
                response = self.base_client.request(
                    method=method, url=url, timeout=timeout, **kwargs
                )
                raw_status = getattr(response, "status_code", None)
                context["status_code"] = (
                    raw_status if isinstance(raw_status, int) else None
                )
                status_label = self._normalize_status(context["status_code"])

                # Use unified error handler
                request_context = RequestContext(
                    provider=self.provider,
                    endpoint=url,
                    status_code=context["status_code"],
                    method=method_upper,
                )
                error = self.error_handler.handle(response, request_context)

                log_method = (
                    self.logger.error
                    if context["status_code"] is not None
                    and context["status_code"] >= 400
                    else self.logger.info
                )
                log_method(
                    "http_request_completed",
                    provider=self.provider,
                    method=method_upper,
                    url=url,
                    status_code=context["status_code"],
                    latency_sec=time.monotonic() - start,
                )

                if error is not None:
                    raise error

                return response
        except Exception as exc:
            status_label = self._status_from_exception(status_label, exc)
            self._record_error(url, status_label)
            raise
        finally:
            latency = time.monotonic() - start
            self._observe_latency(url, latency, status_label)
            self._record_total(url, status_label)

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Execute a request using the configured HTTP client."""
        return self._request_with_retry(method, url, **kwargs)

    def get_response(self, url: str, **kwargs: Any) -> Any:
        """GET запрос."""
        return self.request("GET", url, **kwargs)

    def request_post(self, url: str, **kwargs: Any) -> Any:
        """POST запрос."""
        return self.request("POST", url, **kwargs)

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> Any:
        attempt = 1
        while True:
            try:
                return self.request_call(method, url, **kwargs)
            except Exception as exc:
                if self.retry_policy is None or not self.retry_policy.should_retry(
                    exc, attempt
                ):
                    raise

                backoff = self.retry_policy.get_backoff(attempt)
                self.logger.warning(
                    "http_request_retry",
                    provider=self.provider,
                    url=url,
                    attempt=attempt,
                    backoff_sec=backoff,
                    error=str(exc),
                )
                time.sleep(backoff)
                attempt += 1

    def close(self) -> None:
        """Закрыть соединение."""
        if hasattr(self.base_client, "close"):
            self.base_client.close()

    def _record_total(self, endpoint: str, status: str) -> None:
        if not self.metrics:
            return

        self.metrics.inc_counter(
            MetricName.CLIENT_REQUEST_TOTAL,
            {"provider": self.provider, "endpoint": endpoint, "status": status},
        )

    def _observe_latency(self, endpoint: str, latency: float, status: str) -> None:
        if not self.metrics:
            return

        self.metrics.observe_histogram(
            MetricName.CLIENT_REQUEST_DURATION_SECONDS,
            latency,
            {"provider": self.provider, "endpoint": endpoint, "status": status},
        )

    def _record_error(self, endpoint: str, status: str) -> None:
        if not self.metrics:
            return

        self.metrics.inc_counter(
            MetricName.CLIENT_REQUEST_ERRORS_TOTAL,
            {"provider": self.provider, "endpoint": endpoint, "status": status},
        )

    def _normalize_status(self, status_code: int | None) -> str:
        if status_code is None:
            return "unknown"
        return str(status_code)

    def _status_from_exception(self, current_status: str, exc: Exception) -> str:
        if isinstance(exc, ApiTimeoutError) or isinstance(exc, requests.Timeout):
            return "timeout"
        if isinstance(exc, ApiClientError):
            status_code = getattr(exc, "status_code", None)
            if status_code is not None:
                return str(status_code)
        return exc.__class__.__name__ or current_status
