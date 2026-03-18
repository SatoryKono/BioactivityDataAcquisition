"""Unit tests for the composition-facing PolarsJoinAdapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.application.composite.protocols import JoinExecutorProtocol
from bioetl.composition.factories.services.polars_join_adapter import PolarsJoinAdapter


@pytest.mark.unit
def test_polars_join_adapter_is_join_executor_service() -> None:
    """Adapter remains a thin DI-friendly alias over JoinExecutorService."""
    adapter = PolarsJoinAdapter(
        logger=MagicMock(),
        join_type_resolver=lambda: "left",
    )

    assert isinstance(adapter, JoinExecutorService)
    assert isinstance(adapter, JoinExecutorProtocol)


@pytest.mark.unit
def test_polars_join_adapter_executes_inherited_join_logic() -> None:
    """Adapter exposes inherited join execution behavior unchanged."""
    adapter = PolarsJoinAdapter(
        logger=MagicMock(),
        join_type_resolver=lambda: "left",
    )
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
