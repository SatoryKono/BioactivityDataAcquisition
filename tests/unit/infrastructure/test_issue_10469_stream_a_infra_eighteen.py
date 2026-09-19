"""Stream A remaining INF hits: metrics, CB open, DQ overrides, merged Silver, schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
)
from bioetl.infrastructure.adapters.decorators.circuit_breaker import (
    CircuitBreakerDataSourceDecorator,
)
from bioetl.infrastructure.config.dq_contract_config_loader import (
    _parse_disposition_overrides,
)
from bioetl.infrastructure.control_plane.file_workflow_transform_artifact_store import (
    _created_at_iso,
    _jsonable,
)
from bioetl.infrastructure.schemas.composite_config_base import AggregationSchema
from bioetl.infrastructure.storage.silver.merged_operations import (
    _MergedSilverWriteRequest,
    _PreparedMergedSilverWrite,
    _build_merged_silver_write_request,
    _execute_merged_silver_write_flow,
)

pytestmark = pytest.mark.unit


def test_dropped_duplicates_increments_when_metrics_present() -> None:
    metrics = MagicMock()
    recorder = AdapterMetricsRecorder(metrics=metrics, provider="chembl")
    recorder.record_dropped_duplicates("activity", 2)
    metrics.increment_counter.assert_called()


@pytest.mark.asyncio
async def test_circuit_breaker_reraises_open_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = SimpleNamespace(provider_name="chembl")
    decorator = CircuitBreakerDataSourceDecorator(
        data_source=source,  # type: ignore[arg-type]
        circuit_breaker=MagicMock(),
        logger=MagicMock(),
    )

    async def _open(_source: object, _request: object):
        raise CircuitBreakerOpenError("chembl", retry_after=1.0)
        yield {}  # pragma: no cover

    monkeypatch.setattr(
        "bioetl.infrastructure.adapters.decorators.circuit_breaker.iter_delegated_fetch",
        _open,
    )
    with pytest.raises(CircuitBreakerOpenError):
        async for _row in decorator._iterate_with_error_recording(
            DataSourceFetchRequest(entity_type="activity")
        ):
            pass


def test_disposition_overrides_and_valid_aggregation() -> None:
    parsed = _parse_disposition_overrides({"rule": "fail"})
    assert parsed["rule"] is DQDisposition.FAIL
    schema = AggregationSchema(
        group_by="id",
        order_by=["ts"],
        fields={"n": {"source": "x", "agg": "count"}},
    )
    assert schema.order_by == ["ts"]


def test_created_at_from_clock_and_jsonable_datetime() -> None:
    stamp = datetime(2026, 1, 2, tzinfo=UTC)
    clock = SimpleNamespace(now=lambda: stamp)
    assert _created_at_iso(SimpleNamespace(created_at=None), clock) == stamp.isoformat()
    assert _jsonable(stamp) == stamp.isoformat()
    assert _jsonable([stamp]) == [stamp.isoformat()]


def test_build_merged_silver_write_request_wrapper() -> None:
    request = _build_merged_silver_write_request(
        table_name="activity",
        records=[{"id": "1"}],
        primary_keys=["id"],
    )
    assert request.table_name == "activity"


@pytest.mark.asyncio
async def test_execute_merged_silver_empty_and_full() -> None:
    logger = MagicMock()
    empty = _MergedSilverWriteRequest(table_name="activity", records=[])
    executor = SimpleNamespace(logger=logger)
    await _execute_merged_silver_write_flow(executor, empty)  # type: ignore[arg-type]
    logger.warning.assert_called()

    request = _MergedSilverWriteRequest(
        table_name="activity",
        records=[{"id": "1"}],
        primary_keys=["id"],
    )
    prepared = _PreparedMergedSilverWrite(
        request=request,
        table_path="p",
        arrow_table=object(),
    )
    executor = SimpleNamespace(
        logger=logger,
        _prepare_merged_silver_write=lambda _request: prepared,
        _write_silver_merged_delta=AsyncMock(),
        _export_silver_merged_csv=AsyncMock(),
        _write_silver_merged_metadata=AsyncMock(),
    )
    await _execute_merged_silver_write_flow(executor, request)  # type: ignore[arg-type]
    executor._write_silver_merged_delta.assert_awaited()
    executor._export_silver_merged_csv.assert_awaited()
    executor._write_silver_merged_metadata.assert_awaited()
