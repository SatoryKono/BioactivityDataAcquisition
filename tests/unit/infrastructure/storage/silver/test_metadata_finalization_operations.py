"""Тесты helpers финализации метаданных Silver writer."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from bioetl.infrastructure.storage.silver.operations import (
    metadata_finalization_operations as operations,
)


@pytest.mark.asyncio
async def test_prepare_finalization_uses_metadata_mixin_perf_counter_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """При отсутствии override используется единственный канонический perf counter."""
    received_perf_counter: Callable[[], float] | None = None

    async def fake_prepare(
        metadata_ops: object,
        request: object,
        *,
        perf_counter: Callable[[], float],
    ) -> object:
        nonlocal received_perf_counter
        del metadata_ops, request
        received_perf_counter = perf_counter
        return "prepared"

    monkeypatch.setattr(
        operations,
        "_prepare_silver_write_finalization_context",
        fake_prepare,
    )

    result = await operations.prepare_silver_write_finalization_context_with_default_perf_counter(
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
    )

    assert result == "prepared"
    assert received_perf_counter is not None
    assert isinstance(received_perf_counter(), float)


@pytest.mark.asyncio
async def test_prepare_finalization_operation_preserves_explicit_perf_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Operation facade передаёт явно заданный perf counter без подмены."""
    received_perf_counter: Callable[[], float] | None = None

    async def fake_prepare(
        metadata_ops: object,
        request: object,
        *,
        perf_counter: Callable[[], float],
    ) -> object:
        nonlocal received_perf_counter
        del metadata_ops, request
        received_perf_counter = perf_counter
        return "prepared"

    def custom_perf_counter() -> float:
        return 1.25

    monkeypatch.setattr(
        operations,
        "_prepare_silver_write_finalization_context",
        fake_prepare,
    )

    result = await operations.prepare_silver_write_finalization_context_operation(
        object(),  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        perf_counter=custom_perf_counter,
    )

    assert result == "prepared"
    assert received_perf_counter is custom_perf_counter
