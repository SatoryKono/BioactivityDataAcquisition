# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for BatchProcessingSupportService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_uuid_from_callsite,
)

import pytest

from bioetl.application.core.batch_processing_support import (
    BatchProcessingSupportService,
)
from bioetl.application.core.batch_transformer import TransformResult
from bioetl.domain.types import RunType


def _make_transform_result() -> TransformResult:
    return TransformResult(
        silver_records=[{"entity_id": "1"}, {"entity_id": "2"}],
        gold_records=[{"entity_id": "1"}],
        quarantined_count=0,
        gold_excluded_by_contract_count=1,
        filtered_out_count=0,
    )


@pytest.fixture
def mock_context() -> MagicMock:
    context = MagicMock()
    context.run_id = deterministic_uuid_from_callsite("test_batch_processing_support")
    context.run_type = RunType.INCREMENTAL
    return context


@pytest.fixture
def mock_services() -> MagicMock:
    services = MagicMock()
    services.data_source = MagicMock()
    return services


@pytest.fixture
def mock_batch_metrics() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_transformer() -> MagicMock:
    transformer = MagicMock()
    transformer.transform_batch = AsyncMock(return_value=_make_transform_result())
    return transformer


@pytest.fixture
def mock_writer() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_tracing() -> MagicMock:
    return MagicMock()


@pytest.mark.unit
async def test_transform_and_track_metrics_records_gold_excluded_by_contract(
    mock_context: MagicMock,
    mock_services: MagicMock,
    mock_batch_metrics: MagicMock,
    mock_transformer: MagicMock,
    mock_writer: MagicMock,
    mock_tracing: MagicMock,
) -> None:
    """Support service should expose Gold contract exclusions in stage accounting."""
    support = BatchProcessingSupportService(
        services=mock_services,
        logger=MagicMock(),
        batch_metrics=mock_batch_metrics,
        transformer=mock_transformer,
        writer=mock_writer,
        tracing=mock_tracing,
        quarantine_manager=MagicMock(),
        run_id=mock_context.run_id,
    )

    result = await support.transform_and_track_metrics(
        records=[{"id": "1"}, {"id": "2"}],
        batch_id=deterministic_batch_uuid_from_callsite(
            "test_batch_processing_support"
        ),
        start_index=0,
    )

    assert result.gold_excluded_by_contract_count == 1
    mock_batch_metrics.track_stage_records.assert_any_call(
        stage="gold",
        outcome="excluded_by_contract",
        count=1,
    )


@pytest.mark.unit
async def test_write_silver_gold_concurrent_orders_layers_and_lineage(
    mock_context: MagicMock,
    mock_services: MagicMock,
    mock_batch_metrics: MagicMock,
    mock_transformer: MagicMock,
) -> None:
    """Silver must complete before Gold; Gold receives Silver lineage refs."""
    from datetime import UTC, datetime

    call_order: list[str] = []
    silver_result = MagicMock(name="silver_result")

    async def write_silver(records, batch_id, ingestion_ts, bronze_refs=None):  # type: ignore[no-untyped-def]
        _ = (records, batch_id, ingestion_ts, bronze_refs)
        call_order.append("silver")
        return silver_result

    async def write_gold(records, silver_refs=None):  # type: ignore[no-untyped-def]
        _ = records
        call_order.append("gold")
        assert silver_refs == [silver_result]

    writer = MagicMock()
    writer.write_silver = AsyncMock(side_effect=write_silver)
    writer.write_gold = AsyncMock(side_effect=write_gold)
    writer.track_batch_written = MagicMock()

    async def execute_with_span(name, coro, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        call_order.append(f"span:{name}")
        return await coro

    tracing = MagicMock()
    support = BatchProcessingSupportService(
        services=mock_services,
        logger=MagicMock(),
        batch_metrics=mock_batch_metrics,
        transformer=mock_transformer,
        writer=writer,
        tracing=tracing,
        quarantine_manager=MagicMock(),
        run_id=mock_context.run_id,
    )
    # Drive the span helper through the support method under test.
    support._execute_with_span = execute_with_span  # type: ignore[method-assign]

    transform_result = _make_transform_result()
    batch_id = deterministic_batch_uuid_from_callsite(
        "test_write_silver_gold_concurrent"
    )
    await support.write_silver_gold_concurrent(
        transform_result=transform_result,
        batch_id=batch_id,
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        bronze_refs=None,
    )

    assert call_order.index("silver") < call_order.index("gold")
    writer.write_silver.assert_awaited_once()
    writer.write_gold.assert_awaited_once()


@pytest.mark.unit
async def test_write_silver_gold_concurrent_stops_on_silver_failure(
    mock_context: MagicMock,
    mock_services: MagicMock,
    mock_batch_metrics: MagicMock,
    mock_transformer: MagicMock,
) -> None:
    """Silver write failure must not start Gold."""
    from datetime import UTC, datetime

    writer = MagicMock()
    writer.write_silver = AsyncMock(side_effect=RuntimeError("silver failed"))
    writer.write_gold = AsyncMock()
    writer.track_batch_written = MagicMock()

    async def execute_with_span(_name, coro, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return await coro

    support = BatchProcessingSupportService(
        services=mock_services,
        logger=MagicMock(),
        batch_metrics=mock_batch_metrics,
        transformer=mock_transformer,
        writer=writer,
        tracing=MagicMock(),
        quarantine_manager=MagicMock(),
        run_id=mock_context.run_id,
    )
    support._execute_with_span = execute_with_span  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="silver failed"):
        await support.write_silver_gold_concurrent(
            transform_result=_make_transform_result(),
            batch_id=deterministic_batch_uuid_from_callsite(
                "test_write_silver_gold_fail"
            ),
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            bronze_refs=None,
        )

    writer.write_gold.assert_not_awaited()


@pytest.mark.unit
async def test_write_silver_gold_skips_gold_when_silver_quarantined(
    mock_context: MagicMock,
    mock_services: MagicMock,
    mock_batch_metrics: MagicMock,
    mock_transformer: MagicMock,
) -> None:
    """A quarantined Silver write (None) must not proceed to Gold."""
    from datetime import UTC, datetime

    from bioetl.domain.exceptions import SchemaViolationError

    writer = MagicMock()
    writer.write_silver = AsyncMock(
        side_effect=SchemaViolationError("silver", ["bad column"])
    )
    writer.write_gold = AsyncMock()
    writer.track_batch_written = MagicMock()
    writer.track_batch_failed = MagicMock()

    async def execute_with_span(_name, coro, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return await coro

    support = BatchProcessingSupportService(
        services=mock_services,
        logger=MagicMock(),
        batch_metrics=mock_batch_metrics,
        transformer=mock_transformer,
        writer=writer,
        tracing=MagicMock(),
        quarantine_manager=AsyncMock(),
        run_id=mock_context.run_id,
    )
    support._execute_with_span = execute_with_span  # type: ignore[method-assign]

    await support.write_silver_gold_concurrent(
        transform_result=_make_transform_result(),
        batch_id=deterministic_batch_uuid_from_callsite(
            "test_write_silver_gold_quarantine"
        ),
        ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
        bronze_refs=None,
    )

    writer.write_gold.assert_not_awaited()
    mock_batch_metrics.track_stage_records.assert_any_call(
        stage="storage",
        outcome="silver_written",
        count=0,
    )
    mock_batch_metrics.track_stage_records.assert_any_call(
        stage="storage",
        outcome="gold_written",
        count=0,
    )
