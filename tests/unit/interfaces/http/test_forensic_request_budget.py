# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for bounded execution of expensive operator HTTP endpoints."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Coroutine
from typing import Any, cast

import pytest

from bioetl.interfaces.http._forensic_request_budget import (
    ForensicEndpointUnavailable,
    forensic_unavailable_payload,
    run_bounded_forensic_operation,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_synchronous_factory_failure_releases_capacity() -> None:
    limiter = asyncio.Semaphore(1)

    def fail_before_task_creation() -> Coroutine[Any, Any, str]:
        raise RuntimeError("factory failed")

    with pytest.raises(RuntimeError, match="factory failed"):
        await run_bounded_forensic_operation(
            limiter=limiter,
            operation_factory=fail_before_task_creation,
        )

    await asyncio.wait_for(limiter.acquire(), timeout=0.1)
    limiter.release()


@pytest.mark.asyncio
async def test_invalid_factory_result_releases_capacity() -> None:
    limiter = asyncio.Semaphore(1)

    def return_non_coroutine() -> Coroutine[Any, Any, str]:
        return cast(Coroutine[Any, Any, str], object())

    with pytest.raises(TypeError):
        await run_bounded_forensic_operation(
            limiter=limiter,
            operation_factory=return_non_coroutine,
        )

    await asyncio.wait_for(limiter.acquire(), timeout=0.1)
    limiter.release()


@pytest.mark.asyncio
async def test_timed_out_operation_keeps_capacity_until_backend_finishes() -> None:
    """A timed-out thread-like task must retain its slot until real completion."""
    limiter = asyncio.Semaphore(1)
    backend_release = asyncio.Event()

    async def slow_operation() -> str:
        await backend_release.wait()
        return "done"

    with pytest.raises(ForensicEndpointUnavailable) as deadline_error:
        await run_bounded_forensic_operation(
            limiter=limiter,
            operation_factory=slow_operation,
            timeout_seconds=0.01,
            queue_timeout_seconds=0.01,
        )
    assert deadline_error.value.reason == "deadline_exceeded"
    assert deadline_error.value.status_code == 504

    with pytest.raises(ForensicEndpointUnavailable) as capacity_error:
        await run_bounded_forensic_operation(
            limiter=limiter,
            operation_factory=slow_operation,
            timeout_seconds=0.01,
            queue_timeout_seconds=0.01,
        )
    assert capacity_error.value.reason == "capacity_exhausted"
    assert capacity_error.value.status_code == 503

    backend_release.set()
    await asyncio.wait_for(limiter.acquire(), timeout=0.5)
    limiter.release()


@pytest.mark.asyncio
@pytest.mark.parametrize("client_count", [1, 5, 10])
async def test_bounded_load_profile_stays_below_twenty_second_budget(
    client_count: int,
) -> None:
    """The 1/5/10-client profile remains bounded by the four-slot budget."""
    limiter = asyncio.Semaphore(4)
    active = 0
    peak_active = 0

    async def operation() -> int:
        nonlocal active, peak_active
        active += 1
        peak_active = max(peak_active, active)
        try:
            await asyncio.sleep(0.01)
            return active
        finally:
            active -= 1

    started = time.monotonic()
    results = await asyncio.gather(
        *(
            run_bounded_forensic_operation(
                limiter=limiter,
                operation_factory=operation,
                timeout_seconds=1.0,
                queue_timeout_seconds=0.5,
            )
            for _ in range(client_count)
        )
    )
    elapsed = time.monotonic() - started

    assert len(results) == client_count
    assert peak_active <= 4
    assert elapsed < 1.0
    assert elapsed < 20.0


def test_unavailable_payload_is_typed_and_retryable() -> None:
    assert forensic_unavailable_payload(
        endpoint="filtered-stats",
        reason="backend_unavailable",
    ) == {
        "contract": "forensic_endpoint_error_v1",
        "status": "unavailable",
        "endpoint": "filtered-stats",
        "reason": "backend_unavailable",
        "retryable": True,
    }
