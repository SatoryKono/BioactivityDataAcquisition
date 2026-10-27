"""Separate local admission waits from HTTP transport and provider cooldown."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol, TypedDict, cast

import httpx
from httpx._client import UseClientDefault
from httpx._types import (
    AuthTypes,
    CookieTypes,
    HeaderTypes,
    QueryParamTypes,
    RequestContent,
    RequestData,
    RequestExtensions,
    RequestFiles,
    TimeoutTypes,
)

from bioetl.domain.ports import CircuitBreakerPort, LoggerPort, RateLimiterPort
from bioetl.domain.types import JsonDict, RunID
from bioetl.infrastructure.adapters.http.client_retry_policy import parse_retry_after


class _RequestKwargs(TypedDict, total=False):
    """Keyword contract of the HTTPX request forwarded by the timing wrapper."""

    content: RequestContent | None
    data: RequestData | None
    files: RequestFiles | None
    json: object
    params: QueryParamTypes | None
    headers: HeaderTypes | None
    cookies: CookieTypes | None
    auth: AuthTypes | UseClientDefault | None
    follow_redirects: bool | UseClientDefault
    timeout: TimeoutTypes | UseClientDefault
    extensions: RequestExtensions | None


class RequestTimingHost(Protocol):
    provider: str
    run_id: RunID | None
    logger: LoggerPort | None
    rate_limiter: RateLimiterPort
    circuit_breaker: CircuitBreakerPort
    _request_not_before: float


async def _dispatch_http_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    httpx_kwargs: dict[
        str, Any
    ],  # Any: httpx request kwargs before cast to _RequestKwargs
    *,
    is_stream: bool,
    request_timeout: float | None,
) -> httpx.Response:
    """Send one HTTPX request, optionally as a streamed response."""
    async with asyncio.timeout(request_timeout):
        typed_kwargs = cast(_RequestKwargs, httpx_kwargs)
        if is_stream:
            request = client.build_request(method, url, **typed_kwargs)  # type: ignore[misc]
            return await client.send(request, stream=True)
        return await client.request(method, url, **typed_kwargs)


def _apply_provider_cooldown(host: RequestTimingHost, response: httpx.Response) -> None:
    """Extend local cooldown when the provider signals Retry-After."""
    if response.status_code not in (429, 503):
        return
    retry_after = parse_retry_after(response.headers.get("Retry-After", ""))
    if retry_after is None:
        return
    host._request_not_before = max(
        host._request_not_before, time.monotonic() + retry_after
    )


def _log_http_attempt(
    host: RequestTimingHost,
    *,
    method: str,
    attempt_number: int,
    phase: str,
    started: float,
    admitted: float | None,
    completed: float,
    response: httpx.Response | None,
    error_type: str | None,
) -> None:
    """Emit one attempt-complete log without request secrets."""
    if host.logger is None:
        return
    run_fields: dict[str, str] = {}
    if host.run_id is not None:
        run_fields["run_id"] = str(host.run_id)
    admission_end = admitted if admitted is not None else completed
    transport_seconds = 0.0 if admitted is None else completed - admitted
    status_code = None if response is None else response.status_code
    host.logger.info(
        "http_attempt_completed",
        provider=host.provider,
        **run_fields,
        method=method,
        attempt=attempt_number,
        phase=phase,
        admission_seconds=round(admission_end - started, 6),
        transport_seconds=round(transport_seconds, 6),
        status_code=status_code,
        error_type=error_type,
        circuit_state=host.circuit_breaker.get_state().value,
        cooldown_remaining_seconds=round(
            max(0.0, host._request_not_before - completed), 6
        ),
    )


async def execute_timed_request(
    host: RequestTimingHost,
    client: httpx.AsyncClient,
    method: str,
    url: str,
    request_kwargs: JsonDict,  # Heterogeneous kwargs forwarded to the HTTP client.
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
        await _await_admission(host)
        admitted = time.monotonic()
        phase = "transport"

        is_stream = bool(request_kwargs.get("_stream", False))
        httpx_kwargs = {k: v for k, v in request_kwargs.items() if k != "_stream"}

        async def send() -> httpx.Response:
            return await _dispatch_http_request(
                client,
                method,
                url,
                httpx_kwargs,
                is_stream=is_stream,
                request_timeout=request_timeout,
            )

        response = await host.circuit_breaker.call(send)
        response.extensions["bioetl_transport_seconds"] = time.monotonic() - admitted
        _apply_provider_cooldown(host, response)
        return response
    except BaseException as error:
        error_type = type(error).__name__
        raise
    finally:
        _log_http_attempt(
            host,
            method=method,
            attempt_number=attempt_number,
            phase=phase,
            started=started,
            admitted=admitted,
            completed=time.monotonic(),
            response=response,
            error_type=error_type,
        )


async def _await_admission(host: RequestTimingHost) -> None:
    """Recheck cooldown after each limiter acquisition before starting transport."""
    while True:
        delay = max(0.0, host._request_not_before - time.monotonic())
        if delay:
            await asyncio.sleep(delay)
        await host.rate_limiter.acquire()
        if time.monotonic() >= host._request_not_before:
            return
