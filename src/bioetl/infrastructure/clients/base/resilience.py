"""Shared resilience helpers for infrastructure clients."""

from __future__ import annotations

import time
from typing import Any, Callable, Tuple

from bioetl.domain.clients.base.contracts import RetryPolicyABC
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.ports.resilience import RequestContext
from bioetl.infrastructure.clients.base.http_error_handler import HttpErrorHandlerABC


class ResilientRequestMixin:
    """Mixin providing unified retry/error-handling workflow."""

    def _init_resilience(
        self,
        *,
        retry_policy: RetryPolicyABC | None,
        error_handler: HttpErrorHandlerABC,
        logger: LoggingPortABC,
    ) -> None:
        self._resilience_retry_policy = retry_policy
        self._resilience_error_handler = error_handler
        self._resilience_logger = logger

    def _execute_with_resilience(
        self,
        send: Callable[[], Tuple[Any, RequestContext]],
        *,
        context: RequestContext,
    ) -> Any:
        attempt = 1
        while True:
            try:
                response, context = send()
                error = self._resilience_error_handler.handle(response, context)
                if error is not None:
                    raise error
                return response
            except Exception as exc:  # noqa: BLE001 - propagate after retry decision
                retry_policy = self._resilience_retry_policy
                if retry_policy is None or not retry_policy.should_retry(exc, attempt):
                    raise

                backoff = retry_policy.get_backoff(attempt)
                self._resilience_logger.warning(
                    "http_request_retry",
                    provider=context.provider,
                    endpoint=context.endpoint,
                    attempt=attempt,
                    backoff_sec=backoff,
                    error=str(exc),
                )
                time.sleep(backoff)
                attempt += 1

