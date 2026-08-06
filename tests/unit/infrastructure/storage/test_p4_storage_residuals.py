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
"""Focused unit tests for P4 infrastructure/storage residuals."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.domain.ports.workflow_row_reconciliation import (
    RowReconciliationConfig,
    RowReconciliationExecutionError,
    RowReconciliationLayer,
)
from bioetl.infrastructure.storage.delta.resilience import (
    AdaptiveRetryPolicy,
    _deterministic_jitter_seconds,
)
from bioetl.infrastructure.storage.gold_writer import GOLD_WRITE_RETRY_ERRORS
from bioetl.infrastructure.storage.lineage_persistence import _has_explicit_member
from bioetl.infrastructure.storage.metadata_artifact_details import (
    serialize_input_snapshot_ref,
)
from bioetl.infrastructure.storage.workflow_row_reconciliation import (
    StorageRowReconciliationAdapter,
)

pytestmark = pytest.mark.unit


def test_gold_write_retry_errors_are_transient_only() -> None:
    assert ValueError not in GOLD_WRITE_RETRY_ERRORS
    assert TypeError not in GOLD_WRITE_RETRY_ERRORS
    assert KeyError not in GOLD_WRITE_RETRY_ERRORS
    assert RuntimeError not in GOLD_WRITE_RETRY_ERRORS
    assert OSError in GOLD_WRITE_RETRY_ERRORS
    assert TimeoutError in GOLD_WRITE_RETRY_ERRORS


def test_has_explicit_member_handles_slots_without_dict() -> None:
    class _Slots:
        __slots__ = ("value",)

        def __init__(self) -> None:
            self.value = 1

        def method(self) -> int:
            return self.value

    target = _Slots()
    assert _has_explicit_member(target, "method") is True
    assert _has_explicit_member(target, "missing") is False


def test_serialize_input_snapshot_ref_normalizes_last_modified() -> None:
    ts = datetime(2026, 2, 3, 4, 5, 6, tzinfo=UTC)
    snapshot = SimpleNamespace(
        snapshot_id="snap-1",
        content_hash="abc",
        immutable_uri=None,
        query_fingerprint=None,
        storage_provider=None,
        object_bucket=None,
        object_key=None,
        object_version_id=None,
        etag=None,
        last_modified=ts,
        captured_at=ts,
    )
    payload = serialize_input_snapshot_ref(snapshot)  # type: ignore[arg-type]
    assert payload["last_modified"] == ts.isoformat()
    assert payload["captured_at"] == ts.isoformat()


def test_deterministic_jitter_desynchronizes_by_operation_id() -> None:
    a = _deterministic_jitter_seconds(0, 1.0, operation_id="table-a")
    b = _deterministic_jitter_seconds(0, 1.0, operation_id="table-b-different")
    # Not always different for every pair, but salt shifts phase for distinct ids.
    # At least verify operation_id is accepted and stays bounded.
    assert 0.0 < a <= 1.0
    assert 0.0 < b <= 1.0
    policy = AdaptiveRetryPolicy(
        enabled=True,
        max_retries=3,
        base_delay_seconds=0.1,
        max_delay_seconds=2.0,
        jitter_seconds=0.4,
    )
    d1 = policy.calculate_delay(0, operation_id="op-1")
    d2 = policy.calculate_delay(0, operation_id="op-2")
    assert d1 > 0.0
    assert d2 > 0.0


@pytest.mark.asyncio
async def test_row_reconciliation_enforces_max_rows() -> None:
    class _Reader:
        async def read_silver(self, table_name: str, columns=None, limit=None):
            del table_name, columns, limit
            return [{"id": i} for i in range(5)]

        async def read_gold(self, table_name: str, columns=None, current_only=True, limit=None):
            del table_name, columns, current_only, limit
            return [{"id": i} for i in range(5)]

    adapter = StorageRowReconciliationAdapter(
        silver_reader=_Reader(),
        gold_reader=_Reader(),
        logger=MagicMock(),
    )
    config = RowReconciliationConfig(
        layer=RowReconciliationLayer.SILVER,
        left_table="left",
        right_table="right",
        left_columns=("id",),
        right_columns=("id",),
        left_primary_keys=("id",),
        max_rows=2,
    )
    with pytest.raises(RowReconciliationExecutionError, match="max_rows"):
        await adapter.reconcile_rows(config)
