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
"""Unit tests for batch transformer quarantine routing (#7838)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite

from bioetl.application.core.batch_transformer_quarantine import (
    flush_dq_records,
    flush_filtered_records,
    route_single_transform_attempt,
)
from bioetl.application.core.batch_transformer_state import RecordTransformOutcome
from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
)
from bioetl.domain.types import ErrorType


def _context() -> MagicMock:
    context = MagicMock()
    context.run_id = "run-1"
    context.started_at = MagicMock()
    context.logger = MagicMock()
    return context


@pytest.mark.unit
@pytest.mark.asyncio
async def test_flush_filtered_records_nominal() -> None:
    quarantine = AsyncMock()
    batch_id = deterministic_batch_uuid_from_callsite("flush_filtered_nominal")
    records = [FilteredQuarantineEntry({"id": "1"}, "why")]

    failed = await flush_filtered_records(
        context=_context(),
        quarantine_manager=quarantine,
        records=records,
        batch_id=batch_id,
    )

    assert failed == 0
    quarantine.quarantine_filtered_records.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_flush_filtered_records_empty_is_noop() -> None:
    quarantine = AsyncMock()
    failed = await flush_filtered_records(
        context=_context(),
        quarantine_manager=quarantine,
        records=[],
        batch_id=deterministic_batch_uuid_from_callsite("flush_filtered_empty"),
    )
    assert failed == 0
    quarantine.quarantine_filtered_records.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_flush_dq_records_nominal() -> None:
    quarantine = AsyncMock()
    batch_id = deterministic_batch_uuid_from_callsite("flush_dq_nominal")
    records = [DQQuarantineEntry({"id": "1"}, ErrorType.INVALID_DATA, "bad")]

    failed = await flush_dq_records(
        context=_context(),
        quarantine_manager=quarantine,
        records=records,
        batch_id=batch_id,
    )

    assert failed == 0
    quarantine.quarantine_records.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_single_transform_attempt_success() -> None:
    routed = await route_single_transform_attempt(
        context=_context(),
        quarantine_manager=AsyncMock(),
        attempt=RecordTransformOutcome(
            silver_record={"id": "1"},
            gold_record={"id": "1", "gold": True},
        ),
        batch_id=deterministic_batch_uuid_from_callsite("route_success"),
    )
    assert routed.silver_record == {"id": "1"}
    assert routed.gold_record == {"id": "1", "gold": True}
    assert routed.is_quarantined is False
    assert routed.is_filtered_out is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_single_transform_attempt_filtered() -> None:
    quarantine = AsyncMock()
    routed = await route_single_transform_attempt(
        context=_context(),
        quarantine_manager=quarantine,
        attempt=RecordTransformOutcome(
            silver_record=None,
            gold_record=None,
            filtered_entry=FilteredQuarantineEntry({"id": "f"}, "why"),
        ),
        batch_id=deterministic_batch_uuid_from_callsite("route_filtered"),
    )
    assert routed.is_filtered_out is True
    assert routed.is_quarantined is False
    quarantine.quarantine_filtered_records.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_route_single_transform_attempt_dq() -> None:
    quarantine = AsyncMock()
    routed = await route_single_transform_attempt(
        context=_context(),
        quarantine_manager=quarantine,
        attempt=RecordTransformOutcome(
            silver_record=None,
            gold_record=None,
            dq_entry=DQQuarantineEntry({"id": "q"}, ErrorType.INVALID_DATA, "err"),
        ),
        batch_id=deterministic_batch_uuid_from_callsite("route_dq"),
    )
    assert routed.is_quarantined is True
    assert routed.is_filtered_out is False
    quarantine.quarantine_records.assert_awaited_once()
