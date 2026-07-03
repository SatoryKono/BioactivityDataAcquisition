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
