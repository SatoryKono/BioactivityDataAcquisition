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
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.services.export_lineage.audit_inspection_service import (
    AuditInspectionService,
)
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import RunID

ENTRY_RUN_ID = UUID("44444444-4444-4444-8444-444444444444")
QUERY_RUN_ID = UUID("55555555-5555-4555-8555-555555555555")


@pytest.fixture
def mock_audit_port() -> MagicMock:
    port = MagicMock()
    port.get_entries = AsyncMock(return_value=[])
    port.aclose = AsyncMock()
    return port


@pytest.fixture
def service(mock_audit_port: MagicMock) -> AuditInspectionService:
    return AuditInspectionService(audit_port=mock_audit_port)


def _entry() -> AuditEntry:
    return AuditEntry(
        run_id=RunID(ENTRY_RUN_ID),
        timestamp=datetime(2026, 4, 10, 10, 0, 0),
        layer=AuditLayer.SILVER,
        table_name="chembl_activity",
        operation=AuditOperation.MERGE,
        records_count=42,
        metadata={"provider": "chembl"},
    )


@pytest.mark.asyncio
async def test_inspect_run_queries_audit_port_with_parsed_run_id(
    service: AuditInspectionService,
    mock_audit_port: MagicMock,
) -> None:
    mock_audit_port.get_entries.return_value = [_entry()]

    result = await service.inspect_run(str(QUERY_RUN_ID), limit=7)

    assert len(result.entries) == 1
    mock_audit_port.get_entries.assert_awaited_once_with(
        run_id=RunID(QUERY_RUN_ID),
        layer=None,
        table_name=None,
        start_time=None,
        end_time=None,
        limit=7,
    )


@pytest.mark.asyncio
async def test_inspect_table_resolves_string_layer(
    service: AuditInspectionService,
    mock_audit_port: MagicMock,
) -> None:
    await service.inspect_table("chembl_activity", layer="silver", limit=9)

    mock_audit_port.get_entries.assert_awaited_once_with(
        run_id=None,
        layer=AuditLayer.SILVER,
        table_name="chembl_activity",
        start_time=None,
        end_time=None,
        limit=9,
    )


@pytest.mark.asyncio
async def test_list_entries_rejects_invalid_run_id(
    service: AuditInspectionService,
) -> None:
    with pytest.raises(ValueError, match="Invalid run_id"):
        await service.list_entries(run_id="not-a-uuid")


@pytest.mark.asyncio
async def test_aclose_delegates_to_port(
    service: AuditInspectionService,
    mock_audit_port: MagicMock,
) -> None:
    await service.aclose()

    mock_audit_port.aclose.assert_awaited_once_with()
