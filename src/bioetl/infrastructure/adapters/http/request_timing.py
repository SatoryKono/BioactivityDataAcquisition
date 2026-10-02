"""Separate local admission waits from HTTP transport and provider cooldown."""

from __future__ import annotations

import asyncio
import time
from typing import Protocol

import httpx

from bioetl.domain.ports import CircuitBreakerPort, LoggerPort, RateLimiterPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.adapters.http._client_retry_policy import _parse_retry_after


class RequestTimingHost(Protocol):
    provider: str
    run_id: RunID | None
    logger: LoggerPort | None
    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    _request_not_before: float


async def execute_timed_request(
    host: RequestTimingHost,
    client: httpx.AsyncClient,
    method: str,
    url: str,
    request_kwargs: dict[str, object],
    *,
    request_timeout: float | None = None,
    attempt_number: int = 1,
) -> httpx.Response:
    """Apply admission before the transport deadline; never log request secrets."""
    started = time.monotonic()
    admitted = None
    response = None
    error_type = None
    phase = "admission"
    try:
        while True:
            delay = max(0.0, host._request_not_before - time.monotonic())
            if delay:
                await asyncio.sleep(delay)
            await host.rate_limiter.acquire()
            if time.monotonic() >= host._request_not_before:
                break
        admitted = time.monotonic()
        phase = "transport"

        async def send() -> httpx.Response:
            async with asyncio.timeout(request_timeout):
                return await client.request(method, url, **request_kwargs)

        response = await host.circuit_breaker.call(send)
        response.extensions["bioetl_transport_seconds"] = time.monotonic() - admitted
        if response.status_code in (429, 503):
            retry_after = _parse_retry_after(response.headers.get("Retry-After", ""))
            if retry_after is not None:
                host._request_not_before = max(
                    host._request_not_before, time.monotonic() + retry_after
                )
        return response
    except BaseException as error:
        error_type = type(error).__name__
        raise
    finally:
        completed = time.monotonic()
        if host.logger is not None:
            host.logger.info(
                "http_attempt_completed",
                provider=host.provider,
                **({"run_id": str(host.run_id)} if host.run_id is not None else {}),
                method=method,
                attempt=attempt_number,
                phase=phase,
                admission_seconds=round(
                    (admitted if admitted is not None else completed) - started, 6
                ),
                transport_seconds=round(completed - admitted, 6)
                if admitted is not None
                else 0.0,
                status_code=response.status_code if response is not None else None,
                error_type=error_type,
                circuit_state=host.circuit_breaker.get_state().value,
                cooldown_remaining_seconds=round(
                    max(0.0, host._request_not_before - completed), 6
                ),
            )
