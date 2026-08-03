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
"""Unit tests for Silver merge timeout retry exhaustion paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.exceptions import DeltaTransactionError
from bioetl.infrastructure.storage.delta.resilience import (
    AdaptiveRetryPolicy,
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.delta_helpers import (
    _MergeExecutionTimeoutError,
)
from bioetl.infrastructure.storage.silver.merge_resilience_helpers import (
    _handle_timeout_retry,
    _emit_merge_final_event,
)

pytestmark = pytest.mark.unit


def _timeout_policy(*, max_retries: int = 0) -> SilverMergeResiliencePolicy:
    return SilverMergeResiliencePolicy(
        execution_timeout_seconds=1.0,
        commit_retry=AdaptiveRetryPolicy(
            enabled=True,
            max_retries=0,
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
            jitter_seconds=0.0,
            adaptive=False,
        ),
        timeout_retry=AdaptiveRetryPolicy(
            enabled=True,
            max_retries=max_retries,
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
            jitter_seconds=0.0,
            adaptive=False,
        ),
    )


@pytest.mark.asyncio
async def test_handle_timeout_retry_exhaustion_raises_delta_transaction_error() -> None:
    """Timeout retries exhausted must surface DeltaTransactionError with table path."""
    logger = MagicMock()
    emit_final = MagicMock()
    emit_retry = MagicMock()
    cause = _MergeExecutionTimeoutError(timeout_seconds=1.0)

    with pytest.raises(DeltaTransactionError, match="timed out"):
        await _handle_timeout_retry(
            table_path="silver/chembl/activity",
            policy=_timeout_policy(max_retries=0),
            retry_count=0,
            cause=cause,
            emit_final=emit_final,
            emit_retry=emit_retry,
            logger=logger,
        )

    emit_final.assert_called_once()
    assert emit_final.call_args.kwargs["final_reason"] == "timeout_retries_exhausted"
    logger.warning.assert_called_once_with(
        "silver_merge_timeout",
        table_path="silver/chembl/activity",
        timeout_seconds=1.0,
        retry_count=0,
    )


@pytest.mark.asyncio
async def test_handle_timeout_retry_increments_counter_when_retries_remain(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Remaining timeout retries must increment counter without emitting final failure."""
    sleep_mock = AsyncMock()
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.silver.merge_resilience_helpers.asyncio.sleep",
        sleep_mock,
    )
    logger = MagicMock()
    emit_final = MagicMock()
    emit_retry = MagicMock()
    cause = _MergeExecutionTimeoutError(timeout_seconds=2.0)

    next_count = await _handle_timeout_retry(
        table_path="silver/test.table",
        policy=_timeout_policy(max_retries=2),
        retry_count=0,
        cause=cause,
        emit_final=emit_final,
        emit_retry=emit_retry,
        logger=logger,
    )

    assert next_count == 1
    emit_final.assert_not_called()
    emit_retry.assert_called_once()


def test_emit_merge_final_event_increments_failure_metric() -> None:
    """Final merge failure must increment silver_merge_failures_total when metrics wired."""
    logger = MagicMock()
    metrics = MagicMock()

    _emit_merge_final_event(
        logger=logger,
        metrics=metrics,
        table_path="silver/chembl/activity",
        final_reason="timeout_retries_exhausted",
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_silver_merge_failures_total",
        1,
        {
            "pipeline": "activity",
            "final_reason": "timeout_retries_exhausted",
        },
    )
