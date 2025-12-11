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
from bioetl.domain.ports.resilience import ClientResilienceStrategy, RequestContext
from bioetl.infrastructure.clients.base.http_error_handler import (
    DefaultHttpErrorHandler,
    HttpErrorHandlerABC,
    StatusCodeErrorClassifier,
)
from bioetl.infrastructure.clients.base.resilience import ResilientRequestMixin
from bioetl.infrastructure.errors import (
    ApiClientError,
    ApiTimeoutError,
    wrap_http_errors,
)
from bioetl.infrastructure.http import ExponentialRetryPolicy
from bioetl.infrastructure.settings.http import DEFAULT_RETRY
from bioetl.infrastructure.settings.metrics import MetricName


class _HttpTransport(ResilientRequestMixin):
    """Internal HTTP transport without middleware layers.

    Delegates calls directly to the underlying HTTP client.
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
        resilience_strategy: ClientResilienceStrategy | None = None,
    ) -> None:
        self.provider = provider
        self.config = config
        self.base_client = base_client
        self.logger = logger
        self.metrics = metrics
        classifier = StatusCodeErrorClassifier()
        self.resilience_strategy = resilience_strategy or ClientResilienceStrategy.from_http_config(
            config,
            classifier=classifier,
            retry_exceptions=DEFAULT_RETRY.retry_exceptions,
        )
        resolved_error_handler = error_handler or DefaultHttpErrorHandler(
            logger, classifier=self.resilience_strategy.error_classifier
        )
        retry_policy = ExponentialRetryPolicy(
            max_attempts=self.resilience_strategy.backoff.max_attempts,
            backoff_factor=self.resilience_strategy.backoff.backoff_factor,
            backoff_max=self.resilience_strategy.backoff.backoff_max,
            retry_statuses=self.resilience_strategy.backoff.retry_statuses,
            retry_exceptions=self.resilience_strategy.backoff.retry_exceptions,
        )
        self._init_resilience(
            retry_policy=retry_policy,
            error_handler=resolved_error_handler,
            logger=logger,
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
        """Execute HTTP request with client settings."""
        context = RequestContext(
            provider=self.provider, endpoint=url, status_code=None, method=method
        )
        return self._execute_with_resilience(
            lambda: self._send_once(method, url, context, **kwargs),
            context=context,
        )

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Execute a request using the configured HTTP client."""
        return self._request_with_retry(method, url, **kwargs)

    def get_response(self, url: str, **kwargs: Any) -> Any:
        """Execute GET request."""
        return self.request("GET", url, **kwargs)

    def request_post(self, url: str, **kwargs: Any) -> Any:
        """Execute POST request."""
        return self.request("POST", url, **kwargs)

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> Any:
        return self.request_call(method, url, **kwargs)

    def close(self) -> None:
        """Close the underlying HTTP connection."""
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

    def _send_once(
        self, method: str, url: str, context: RequestContext, **kwargs: Any
    ) -> tuple[Any, RequestContext]:
        start = time.monotonic()
        status_label = "unknown"
        method_upper = method.upper()
        try:
            with wrap_http_errors(
                provider=self.provider, endpoint=url, logger=self.logger
            ) as error_context:
                if method_upper in {"POST", "PUT", "PATCH", "DELETE"}:
                    headers = dict(kwargs.get("headers") or {})
                    headers.setdefault("Idempotency-Key", str(uuid4()))
                    kwargs["headers"] = headers

                timeout = kwargs.pop("timeout", self.config.timeout_sec)
                response = self.base_client.request(
                    method=method, url=url, timeout=timeout, **kwargs
                )
                raw_status = getattr(response, "status_code", None)
                status_code = raw_status if isinstance(raw_status, int) else None
                error_context["status_code"] = status_code
                status_label = self._normalize_status(status_code)

                log_method = (
                    self.logger.error
                    if status_code is not None and status_code >= 400
                    else self.logger.info
                )
                log_method(
                    "http_request_completed",
                    provider=self.provider,
                    method=method_upper,
                    url=url,
                    status_code=status_code,
                    latency_sec=time.monotonic() - start,
                )

                updated_context = RequestContext(
                    provider=context.provider,
                    endpoint=context.endpoint,
                    status_code=status_code,
                    method=method_upper,
                    response_body=context.response_body,
                )
                return response, updated_context
        except Exception as exc:
            status_label = self._status_from_exception(status_label, exc)
            self._record_error(url, status_label)
            raise
        finally:
            latency = time.monotonic() - start
            self._observe_latency(url, latency, status_label)
            self._record_total(url, status_label)
