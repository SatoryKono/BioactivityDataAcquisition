"""Bounded execution contract for expensive operator HTTP endpoints."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine, Mapping
from time import perf_counter
from typing import Any
from uuid import uuid4

from bioetl.application.observability.control_plane_evidence.timing import (
    observe_evidence_stages,
)

FORENSIC_ENDPOINT_CONCURRENCY = 4
FORENSIC_ENDPOINT_QUEUE_TIMEOUT_SECONDS = 0.25
FORENSIC_ENDPOINT_TIMEOUT_SECONDS = 12.0
FORENSIC_ENDPOINT_ERROR_CONTRACT = "forensic_endpoint_error_v1"
_LOGGER = logging.getLogger(__name__)


class ForensicEndpointUnavailable(RuntimeError):
    """Typed operator-endpoint failure with an explicit HTTP disposition."""

    def __init__(
        self, *, reason: str, status_code: int, request_id: str | None = None
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code
        self.request_id = request_id


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


def forensic_unavailable_table_payload(
    *,
    endpoint: str,
    reason: str,
    observed_at: str | None = None,
    request_id: str | None = None,
) -> dict[str, object]:
    """Extend the forensic error contract with one Infinity table row."""
    stamp = observed_at if observed_at is not None else "unavailable"
    payload = forensic_unavailable_payload(endpoint=endpoint, reason=reason)
    payload["observed_at"] = stamp
    if request_id is not None:
        payload["request_id"] = request_id
    payload["rows"] = [
        {
            "check": "endpoint_availability",
            "status": "ERROR",
            "reason": reason,
            "detail": (
                "retryable=true; refresh the panel. HTTP 504/503 is backend "
                "unavailable, not a valid empty table."
            ),
            "endpoint": endpoint,
            "retryable": True,
            "observed_at": stamp,
        }
    ]
    if endpoint == "/ops/control-plane/trust-summary":
        # The Trust panel selects an object, unlike the validation row tables.
        # Query failure must not masquerade as missing selection or run evidence.
        payload["trust"] = {
            "processing_status": "UNKNOWN",
            "trust_status": "QUERY ERROR",
            "reasons_text": f"{reason}; Trust not evaluated. Retry the query.",
            "reasons_display": f"{reason}; Trust not evaluated. Retry the query.",
            "reasons_count": 1,
            "evidence_observed_at": None,
            "evidence_freshness": "unavailable",
        }
    return payload


def table_error_as_http_ok(query: Mapping[str, str]) -> bool:
    """Return whether Grafana asked to materialize forensic errors as rows."""
    raw = str(query.get("error_as_row") or "").strip().lower()
    return raw in {"1", "true", "yes"}


async def run_bounded_forensic_operation[ResultT](
    *,
    limiter: asyncio.Semaphore,
    operation_factory: Callable[
        [], Coroutine[Any, Any, ResultT]  # Any: standard coroutine yield/send types
    ],
    timeout_seconds: float = FORENSIC_ENDPOINT_TIMEOUT_SECONDS,
    queue_timeout_seconds: float = FORENSIC_ENDPOINT_QUEUE_TIMEOUT_SECONDS,
    endpoint: str = "unspecified",
) -> ResultT:
    """Run one expensive operation under a hard deadline and concurrency cap.

    A timed-out thread-backed operation cannot be cancelled safely. Its limiter
    slot therefore remains occupied until the underlying task really finishes,
    preventing timed-out requests from creating an unbounded worker backlog.
    """
    request_id = uuid4().hex
    queued_at = perf_counter()
    try:
        await asyncio.wait_for(
            limiter.acquire(),
            timeout=queue_timeout_seconds,
        )
    except TimeoutError as exc:
        _LOGGER.warning(
            "forensic_capacity_exhausted request_id=%s endpoint=%s queue_seconds=%.6f",
            request_id,
            endpoint,
            perf_counter() - queued_at,
        )
        raise ForensicEndpointUnavailable(
            reason="capacity_exhausted",
            status_code=503,
            request_id=request_id,
        ) from exc

    started_at = perf_counter()
    queue_seconds = started_at - queued_at

    def observe_stage(stage: str, elapsed: float) -> None:
        _LOGGER.log(
            logging.WARNING if elapsed >= 1.0 else logging.INFO,
            "forensic_stage request_id=%s endpoint=%s stage=%s seconds=%.6f",
            request_id,
            endpoint,
            stage,
            elapsed,
        )

    try:
        with observe_evidence_stages(observe_stage):
            operation_task = asyncio.create_task(operation_factory())
    except BaseException:
        limiter.release()
        raise
    release_deferred = False

    def release_after_completion(completed_task: asyncio.Task[ResultT]) -> None:
        limiter.release()
        _LOGGER.warning(
            "forensic_deferred_completion request_id=%s endpoint=%s operation_seconds=%.6f cancelled=%s",
            request_id,
            endpoint,
            perf_counter() - started_at,
            completed_task.cancelled(),
        )
        if not completed_task.cancelled():
            completed_task.exception()

    try:
        return await asyncio.wait_for(
            asyncio.shield(operation_task),
            timeout=timeout_seconds,
        )
    except TimeoutError as exc:
        _LOGGER.warning(
            "forensic_deadline_exceeded request_id=%s endpoint=%s queue_seconds=%.6f "
            "operation_seconds=%.6f deadline_seconds=%.6f",
            request_id,
            endpoint,
            queue_seconds,
            perf_counter() - started_at,
            timeout_seconds,
        )
        if not operation_task.done():
            operation_task.add_done_callback(release_after_completion)
            release_deferred = True
        raise ForensicEndpointUnavailable(
            reason="deadline_exceeded",
            status_code=504,
            request_id=request_id,
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
    "forensic_unavailable_table_payload",
    "run_bounded_forensic_operation",
    "table_error_as_http_ok",
]
