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
    assert adapter.get_polars_join_type() == "left"
    mock_join_service.get_polars_join_type.assert_called_once_with()


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


@pytest.mark.unit
def test_polars_join_adapter_delegates_composite_key_join() -> None:
    """Composite-key joins should stay delegated to JoinExecutorService."""
    expected_result = pl.DataFrame({"seed_id": ["A"], "dep_value": [2]})
    mock_join_service = MagicMock(spec=JoinExecutorService)
    mock_join_service.execute_composite_key_join.return_value = expected_result

    adapter = PolarsJoinBridge(join_service=mock_join_service)
    left_df = pl.DataFrame({"seed_id": ["A"]})
    right_df = pl.DataFrame({"dep_id": ["A"]})

    assert (
        adapter.execute_composite_key_join(
            left_df=left_df,
            right_df=right_df,
            left_keys=["seed_id"],
            right_keys=["dep_id"],
            pipeline_name="pubmed_publication",
        )
        is expected_result
    )
    mock_join_service.execute_composite_key_join.assert_called_once_with(
        left_df,
        right_df,
        ["seed_id"],
        ["dep_id"],
        "pubmed_publication",
    )
