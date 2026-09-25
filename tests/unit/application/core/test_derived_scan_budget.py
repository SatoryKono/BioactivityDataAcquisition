"""Derived scans cannot silently certify a truncated source as complete."""

import asyncio

import pytest

from bioetl.application.core.derived_scan_budget import (
    DEFAULT_SCAN_RECORDS,
    bounded_source_records,
    iter_derived_source,
    resolve_derived_upstream_limit,
)
from bioetl.domain.exceptions.internal_state import InvalidStateError

pytestmark = pytest.mark.unit


def test_resolve_derived_upstream_limit_scales_output_and_filters() -> None:
    assert (
        resolve_derived_upstream_limit(None, multiplier=10) == DEFAULT_SCAN_RECORDS + 1
    )
    assert resolve_derived_upstream_limit(10, multiplier=20) == 201
    assert resolve_derived_upstream_limit(10, multiplier=200) == 2001
    assert (
        resolve_derived_upstream_limit(1_000, multiplier=200) == DEFAULT_SCAN_RECORDS
    )
    assert resolve_derived_upstream_limit(250, multiplier=200) == DEFAULT_SCAN_RECORDS
    assert (
        resolve_derived_upstream_limit(10, multiplier=20, filter_ids=["a", "b", "c"])
        == 4
    )
    assert resolve_derived_upstream_limit(10, multiplier=20, filter_id_count=7) == 8
    assert resolve_derived_upstream_limit(0, multiplier=20) == 1
    with pytest.raises(ValueError):
        resolve_derived_upstream_limit(10, multiplier=0)


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [0, 2, 3])
async def test_natural_eof_vs_scan_exhaustion(size):
    closed = []

    async def source():
        try:
            for row in range(size):
                yield row
        finally:
            closed.append(True)

    rows = []
    if size > 2:
        with pytest.raises(InvalidStateError, match="derived_scan_budget_exceeded"):
            async for row in bounded_source_records(source(), max_records=2):
                rows.append(row)
    else:
        rows = [row async for row in bounded_source_records(source(), max_records=2)]
    assert rows == list(range(min(size, 2)))
    assert closed == [True]


@pytest.mark.asyncio
async def test_stop_on_exhaustion_returns_the_bounded_sample():
    closed = []

    async def source():
        try:
            for row in range(5):
                yield row
        finally:
            closed.append(True)

    rows = [
        row
        async for row in bounded_source_records(
            source(), max_records=2, stop_on_exhaustion=True
        )
    ]
    assert rows == [0, 1]
    assert closed == [True]


@pytest.mark.asyncio
async def test_iter_derived_source_stops_for_limited_output_and_fails_when_unlimited():
    async def source(size: int):
        for row in range(size):
            yield row

    limited = [
        row
        async for row in iter_derived_source(
            source(4), output_limit=1, scan_limit=2
        )
    ]
    assert limited == [0, 1]

    with pytest.raises(InvalidStateError, match="derived_scan_budget_exceeded"):
        async for _row in iter_derived_source(
            source(DEFAULT_SCAN_RECORDS + 1),
            output_limit=None,
            scan_limit=DEFAULT_SCAN_RECORDS + 1,
        ):
            pass


@pytest.mark.asyncio
async def test_deadline_closes_blocked_source():
    closed = []

    async def source():
        try:
            await asyncio.Event().wait()
            yield 1
        finally:
            closed.append(True)

    with pytest.raises(InvalidStateError, match="time budget"):
        await anext(bounded_source_records(source(), timeout_seconds=0.01))
    assert closed == [True]


@pytest.mark.asyncio
async def test_progressing_pages_are_not_killed_by_sum_of_waits():
    closed = []

    async def source():
        try:
            for row in range(3):
                await asyncio.sleep(0.03)
                yield row
        finally:
            closed.append(True)

    rows = [
        row
        async for row in bounded_source_records(
            source(), max_records=10, timeout_seconds=0.08
        )
    ]
    assert rows == [0, 1, 2]
    assert closed == [True]


@pytest.mark.asyncio
async def test_source_timeout_is_not_misclassified_as_scan_deadline():
    async def source():
        raise TimeoutError("provider timeout")
        yield 1

    with pytest.raises(TimeoutError, match="provider timeout"):
        await anext(bounded_source_records(source()))


@pytest.mark.asyncio
async def test_cancellation_propagates_and_closes_source():
    entered = asyncio.Event()
    closed = []

    async def source():
        try:
            entered.set()
            await asyncio.Event().wait()
            yield 1
        finally:
            closed.append(True)

    task = asyncio.create_task(anext(bounded_source_records(source())))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert closed == [True]
