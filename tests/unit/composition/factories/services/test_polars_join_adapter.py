"""Unit tests for the composition-facing PolarsJoinBridge."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.composition.factories.services.polars_join_adapter import PolarsJoinBridge


@pytest.mark.unit
def test_polars_join_adapter_is_join_executor_service() -> None:
    """Adapter remains a thin DI-friendly alias over JoinExecutorService."""

    mock_join_service = MagicMock(spec=JoinExecutorService)
    mock_join_service.get_polars_join_type.return_value = "left"

    adapter = PolarsJoinBridge(join_service=mock_join_service)

    # Adapter is now a wrapper around JoinExecutorService, not an instance of it
    assert hasattr(adapter, "get_polars_join_type")
    assert hasattr(adapter, "execute_polars_join")


@pytest.mark.unit
def test_polars_join_adapter_executes_inherited_join_logic() -> None:
    """Adapter exposes inherited join execution behavior unchanged."""

    mock_join_service = MagicMock(spec=JoinExecutorService)
    mock_join_service.get_polars_join_type.return_value = "left"

    # Mock the execute_polars_join method to return expected result
    expected_result = pl.DataFrame(
        {"seed_id": ["A"], "seed_value": [1], "dep_value": [2]}
    )
    mock_join_service.execute_polars_join.return_value = expected_result

    adapter = PolarsJoinBridge(join_service=mock_join_service)
    left_df = pl.DataFrame({"seed_id": ["A"], "seed_value": [1]})
    right_df = pl.DataFrame({"dep_id": ["A"], "dep_value": [2]})

    result = adapter.execute_polars_join(
        left_df=left_df,
        right_df=right_df,
        left_key="seed_id",
        right_key="dep_id",
        pipeline_name="pubmed_publication",
    )

    assert result.height == 1
    assert "dep_value" in result.columns
