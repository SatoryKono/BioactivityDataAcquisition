from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.infrastructure.adapters.common.retry_reduction_policy import (
    run_retry_exhausted_recovery_policy,
)


async def _empty_batch_records() -> AsyncIterator[dict[str, str]]:
    for _ in ():
        yield {"id": "unused"}


@pytest.mark.asyncio
async def test_run_retry_exhausted_recovery_policy_splits_multi_batch() -> None:
    split_calls: list[tuple[list[str], list[str], str]] = []
    reduced_calls: list[list[str]] = []
    single_calls: list[str] = []

    def _on_split(first: list[str], second: list[str], error: Exception) -> None:
        split_calls.append((first, second, str(error)))

    async def _fetch_reduced_batch(batch: list[str]) -> AsyncIterator[dict[str, str]]:
        reduced_calls.append(batch)
        yield {"id": ",".join(batch)}

    async def _fetch_single_fallback(
        single_id: str,
        error: Exception,
    ) -> AsyncIterator[dict[str, str]]:
        del error
        single_calls.append(single_id)
        yield {"id": single_id}

    records = await collect_async_iterator(
        run_retry_exhausted_recovery_policy(
            id_batch=["A", "B", "C", "D"],
            retry_error=RuntimeError("retry exhausted"),
            on_split=_on_split,
            fetch_reduced_batch=_fetch_reduced_batch,
            fetch_single_fallback=_fetch_single_fallback,
        )
    )

    assert records == [{"id": "A,B"}, {"id": "C,D"}]
    assert reduced_calls == [["A", "B"], ["C", "D"]]
    assert single_calls == []
    assert split_calls == [(["A", "B"], ["C", "D"], "retry exhausted")]


@pytest.mark.asyncio
async def test_run_retry_exhausted_recovery_policy_uses_single_fallback() -> None:
    reduced_calls: list[list[str]] = []
    single_calls: list[tuple[str, str]] = []

    async def _fetch_reduced_batch(batch: list[str]) -> AsyncIterator[dict[str, str]]:
        reduced_calls.append(batch)
        async for record in _empty_batch_records():
            yield record

    async def _fetch_single_fallback(
        single_id: str,
        error: Exception,
    ) -> AsyncIterator[dict[str, str]]:
        single_calls.append((single_id, str(error)))
        yield {"id": f"single:{single_id}"}

    records = await collect_async_iterator(
        run_retry_exhausted_recovery_policy(
            id_batch=["CHEMBL123"],
            retry_error=ValueError("fail"),
            on_split=None,
            fetch_reduced_batch=_fetch_reduced_batch,
            fetch_single_fallback=_fetch_single_fallback,
        )
    )

    assert records == [{"id": "single:CHEMBL123"}]
    assert reduced_calls == []
    assert single_calls == [("CHEMBL123", "fail")]


@pytest.mark.asyncio
async def test_run_retry_exhausted_recovery_policy_empty_batch_noop() -> None:
    reduced_calls: list[list[str]] = []
    single_calls: list[str] = []

    async def _fetch_reduced_batch(batch: list[str]) -> AsyncIterator[dict[str, str]]:
        reduced_calls.append(batch)
        async for record in _empty_batch_records():
            yield record

    async def _fetch_single_fallback(
        single_id: str,
        error: Exception,
    ) -> AsyncIterator[dict[str, str]]:
        del error
        single_calls.append(single_id)
        async for record in _empty_batch_records():
            yield record

    records = await collect_async_iterator(
        run_retry_exhausted_recovery_policy(
            id_batch=[],
            retry_error=RuntimeError("irrelevant"),
            on_split=None,
            fetch_reduced_batch=_fetch_reduced_batch,
            fetch_single_fallback=_fetch_single_fallback,
        )
    )

    assert records == []
    assert reduced_calls == []
    assert single_calls == []
