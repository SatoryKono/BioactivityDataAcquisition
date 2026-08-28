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


@pytest.mark.asyncio
async def test_finalize_result_writes_metadata_and_uses_none_for_absent_source_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Финализация передаёт построенный metadata request и сохраняет отсутствие source batch."""
    from datetime import UTC, datetime

    from bioetl.domain.medallion import SilverWriteMode
    from bioetl.infrastructure.storage.silver.finalization_models import (
        _SilverWriteFinalizationPreparationRequest,
        _SilverWriteResultFinalizationRequest,
    )
    from bioetl.infrastructure.storage.silver.metadata_write_models import (
        _SilverMetadataWriteRequest,
    )
    from bioetl.infrastructure.storage.silver.prepared_operation_models import (
        _PreparedSilverWriteFinalizationContext,
    )

    completed_at = datetime(2026, 8, 28, tzinfo=UTC)
    context = _PreparedSilverWriteFinalizationContext(
        dq_metrics=object(),  # type: ignore[arg-type]
        version_after=7,
        completed_at=completed_at,
    )
    written_requests: list[object] = []

    class MetadataOps:
        async def _prepare_silver_write_finalization_context(
            self,
            request: _SilverWriteFinalizationPreparationRequest,
        ) -> _PreparedSilverWriteFinalizationContext:
            assert request.table_name == "silver.publication"
            return context

        async def _write_silver_metadata(self, request: _SilverMetadataWriteRequest) -> None:
            written_requests.append(request)

    def fake_build_silver_write_result(**kwargs: object) -> None:
        assert kwargs["version_after"] == 7
        assert kwargs["records_count"] == 0
        return None

    monkeypatch.setattr(
        operations,
        "_build_silver_write_result",
        fake_build_silver_write_result,
    )
    request = _SilverWriteResultFinalizationRequest(
        table_name="silver.publication",
        records=[],
        table_path="/tmp/silver/publication",
        primary_keys=["publication_id"],
        validated_mode=next(iter(SilverWriteMode)),
        bronze_refs=None,
        partition_cols=None,
        source_batch_id=None,
        started_at=completed_at,
        start_perf=1.0,
    )

    result = await operations.finalize_silver_write_result_operation(MetadataOps(), request)

    assert result is None
    assert len(written_requests) == 1
    assert written_requests[0].source_batch_ids is None
    assert written_requests[0].version_after == 7
    assert written_requests[0].completed_at == completed_at
