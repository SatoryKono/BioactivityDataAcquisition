"""Bounded execution contract for expensive operator HTTP endpoints."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

FORENSIC_ENDPOINT_CONCURRENCY = 4
FORENSIC_ENDPOINT_QUEUE_TIMEOUT_SECONDS = 0.25
FORENSIC_ENDPOINT_TIMEOUT_SECONDS = 12.0
FORENSIC_ENDPOINT_ERROR_CONTRACT = "forensic_endpoint_error_v1"


class ForensicEndpointUnavailable(RuntimeError):
    """Typed operator-endpoint failure with an explicit HTTP disposition."""

    def __init__(self, *, reason: str, status_code: int) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code


def forensic_unavailable_payload(
    *,
    endpoint: str,
    reason: str,
) -> dict[str, object]:
    """Build the stable unavailable response used by forensic dashboards."""
    return {
        "contract": FORENSIC_ENDPOINT_ERROR_CONTRACT,
        "status": "unavailable",
        "endpoint": endpoint,
        "reason": reason,
        "retryable": True,
    }


async def run_bounded_forensic_operation[ResultT](
    *,
    limiter: asyncio.Semaphore,
    operation_factory: Callable[
        [], Coroutine[Any, Any, ResultT]  # Any: standard coroutine yield/send types
    ],
    timeout_seconds: float = FORENSIC_ENDPOINT_TIMEOUT_SECONDS,
    queue_timeout_seconds: float = FORENSIC_ENDPOINT_QUEUE_TIMEOUT_SECONDS,
) -> ResultT:
    """Run one expensive operation under a hard deadline and concurrency cap.

    A timed-out thread-backed operation cannot be cancelled safely. Its limiter
    slot therefore remains occupied until the underlying task really finishes,
    preventing timed-out requests from creating an unbounded worker backlog.
    """
    try:
        await asyncio.wait_for(
            limiter.acquire(),
            timeout=queue_timeout_seconds,
        )
    except TimeoutError as exc:
        raise ForensicEndpointUnavailable(
            reason="capacity_exhausted",
            status_code=503,
        ) from exc

    try:
        operation_task = asyncio.create_task(operation_factory())
    except BaseException:
        limiter.release()
        raise
    release_deferred = False

    def release_after_completion(completed_task: asyncio.Task[ResultT]) -> None:
        limiter.release()
        if not completed_task.cancelled():
            completed_task.exception()

    try:
        return await asyncio.wait_for(
            asyncio.shield(operation_task),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        if not operation_task.done():
            operation_task.add_done_callback(release_after_completion)
            release_deferred = True
        raise ForensicEndpointUnavailable(
            reason="deadline_exceeded",
            status_code=504,
        ) from exc
    except asyncio.CancelledError:
        if not operation_task.done():
            operation_task.add_done_callback(release_after_completion)
            release_deferred = True
        raise
    finally:
        if not release_deferred:
            limiter.release()


__all__ = [
    "FORENSIC_ENDPOINT_CONCURRENCY",
    "FORENSIC_ENDPOINT_ERROR_CONTRACT",
    "FORENSIC_ENDPOINT_QUEUE_TIMEOUT_SECONDS",
    "FORENSIC_ENDPOINT_TIMEOUT_SECONDS",
    "ForensicEndpointUnavailable",
    "forensic_unavailable_payload",
    "run_bounded_forensic_operation",
]
