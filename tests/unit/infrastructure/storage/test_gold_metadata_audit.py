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
"""Unit tests for Gold metadata audit entry mapping (#7988)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditLayer, AuditOperation
from bioetl.infrastructure.storage.gold.metadata_audit import (
    _GoldAuditWriteRequest,
    _build_gold_audit_entry,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("mode", "expected_operation"),
    [
        (GoldWriteMode.OVERWRITE, AuditOperation.OVERWRITE),
        (GoldWriteMode.APPEND, AuditOperation.APPEND),
        (GoldWriteMode.SCD2, AuditOperation.MERGE),
    ],
)
def test_build_gold_audit_entry_maps_all_write_modes(
    mode: GoldWriteMode,
    expected_operation: AuditOperation,
) -> None:
    host = SimpleNamespace(logger=MagicMock())
    ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    request = _GoldAuditWriteRequest(
        table_name="chembl_activity_gold",
        records=[{"id": "1"}, {"id": "2"}],
        mode=mode,
        ingestion_ts=ts,
        run_id="run-123",  # type: ignore[arg-type]
    )

    entry = _build_gold_audit_entry(host, request)

    assert entry.run_id == "run-123"
    assert entry.timestamp == ts
    assert entry.layer is AuditLayer.GOLD
    assert entry.table_name == "chembl_activity_gold"
    assert entry.operation is expected_operation
    assert entry.records_count == 2
    assert entry.metadata == {"write_mode": mode.value}
