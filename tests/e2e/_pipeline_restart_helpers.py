"""Shared helpers for single-process Target→Molecule→Target restart e2e scenarios."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner

from .conftest import (
    E2E_THREE_SEQUENTIAL_PIPELINE_TIMEOUT,
    assert_silver_table_has_records,
    create_test_context,
)

ABA_RESTART_TIMEOUT = E2E_THREE_SEQUENTIAL_PIPELINE_TIMEOUT


def aba_restart_marks(test_fn: object) -> object:
    """Apply the shared e2e/vcr/asyncio/timeout marks for ABA restart tests."""
    for mark in (
        pytest.mark.e2e,
        pytest.mark.vcr(allow_playback_repeats=True),
        pytest.mark.asyncio,
        pytest.mark.timeout(ABA_RESTART_TIMEOUT),
    ):
        test_fn = mark(test_fn)
    return test_fn


def batch_processing_service(runner: object) -> object:
    """Return the runner's batch extraction service (test seam)."""
    return runner._executor._extraction_loop_service._batch_processing_service  # type: ignore[attr-defined]  # pylint: disable=protected-access


def bootstrap_target_runner(*, limit: int) -> object:
    """Bootstrap a chembl_target runner with the shared e2e limit."""
    return bootstrap_pipeline_runner(create_test_context("chembl_target", limit=limit))


@contextmanager
def patched_extract_records(
    runner: object,
    monkeypatch: pytest.MonkeyPatch,
    replacement: Callable[..., AsyncIterator[object]],
) -> Iterator[object]:
    """Temporarily replace ``extract_records`` on the runner's batch service."""
    source = batch_processing_service(runner)
    original = source.extract_records  # type: ignore[attr-defined]
    monkeypatch.setattr(source, "extract_records", replacement)
    try:
        yield source
    finally:
        monkeypatch.setattr(source, "extract_records", original)


def failing_extract_records(
    *_args: object, **_kwargs: object
) -> AsyncIterator[object]:
    """Async iterator that fails before yielding any records."""

    async def fail_during_iteration() -> AsyncIterator[object]:
        if False:  # pragma: no cover - keeps this an async generator
            yield None
        raise RuntimeError("injected ChEMBL source failure")

    return fail_during_iteration()


def gated_extract_factory(
    original_extract: Callable[..., AsyncIterator[object]],
    first_record_ready: asyncio.Event,
    continue_extraction: asyncio.Event,
) -> Callable[..., AsyncIterator[object]]:
    """Wrap ``original_extract`` so the first record waits for a cancel signal."""

    def gated_extract_records(*args: object, **kwargs: object) -> AsyncIterator[object]:
        records = original_extract(*args, **kwargs)

        async def gate_first_record() -> AsyncIterator[object]:
            iterator = aiter(records)
            try:
                first_record = await anext(iterator)
                first_record_ready.set()
                await continue_extraction.wait()
                yield first_record
                async for record in iterator:
                    yield record
            finally:
                aclose = getattr(iterator, "aclose", None)
                if callable(aclose):
                    await aclose()

        return gate_first_record()

    return gated_extract_records


async def cancel_after_first_record(runner: object, first_record_ready: asyncio.Event) -> None:
    """Run ``runner`` until the first record is ready, then cancel the task."""
    task = asyncio.create_task(runner.run())  # type: ignore[attr-defined]
    first_record_waiter = asyncio.create_task(first_record_ready.wait())
    try:
        done, _ = await asyncio.wait(
            {task, first_record_waiter},
            timeout=30,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if first_record_waiter not in done:
            if task in done:
                task.result()
            pytest.fail("Pipeline did not reach the first-record cancellation point")
        if task in done:
            task.result()
            pytest.fail("Pipeline finished before reaching the cancellation point")
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        first_record_waiter.cancel()
        await asyncio.gather(first_record_waiter, return_exceptions=True)
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def run_molecule_then_target_and_assert(
    e2e_data_dir: Path,
    *,
    require_a2_records_fetched: bool = False,
    a2_fetch_message: str = "A2 fetched no Target records",
) -> None:
    """Shared B→A2 restart path plus silver presence checks."""
    runner_b = bootstrap_pipeline_runner(
        create_test_context("chembl_molecule", limit=2)
    )
    await runner_b.run()

    runner2 = bootstrap_target_runner(limit=2)
    await runner2.run()  # type: ignore[attr-defined]
    if require_a2_records_fetched:
        assert runner2.execution_metrics["records_fetched"] > 0, a2_fetch_message  # type: ignore[index]

    await assert_silver_table_has_records(e2e_data_dir, "chembl_target", expected_min=1)
    await assert_silver_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )
