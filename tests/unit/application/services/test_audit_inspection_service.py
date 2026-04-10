from __future__ import annotations

from datetime import UTC, datetime
from unittest import mock
from uuid import UUID, uuid4

import pytest

from bioetl.application.services.audit_inspection_service import AuditInspectionService
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import RunID


@pytest.mark.asyncio
async def test_inspect_run_parses_uuid_and_delegates() -> None:
    run_id = str(uuid4())
    audit_port = mock.AsyncMock()
    entry = AuditEntry(
        run_id=RunID(uuid4()),
        timestamp=datetime.now(UTC),
        layer=AuditLayer.SILVER,
        table_name="chembl_activity",
        operation=AuditOperation.MERGE,
        records_count=10,
    )
    audit_port.get_entries.return_value = [entry]

    service = AuditInspectionService(audit_port=audit_port)
    result = await service.inspect_run(run_id, limit=25)

    assert result.entries == (entry,)
    audit_port.get_entries.assert_awaited_once_with(
        run_id=RunID(UUID(run_id)),
        layer=None,
        table_name=None,
        start_time=None,
        end_time=None,
        limit=25,
    )


@pytest.mark.asyncio
async def test_inspect_table_resolves_layer() -> None:
    audit_port = mock.AsyncMock()
    audit_port.get_entries.return_value = []
    service = AuditInspectionService(audit_port=audit_port)

    await service.inspect_table("chembl_activity", layer="silver", limit=5)

    audit_port.get_entries.assert_awaited_once_with(
        run_id=None,
        layer=AuditLayer.SILVER,
        table_name="chembl_activity",
        start_time=None,
        end_time=None,
        limit=5,
    )


@pytest.mark.asyncio
async def test_invalid_run_id_raises() -> None:
    service = AuditInspectionService(audit_port=mock.AsyncMock())

    with pytest.raises(ValueError, match="Invalid run_id"):
        await service.inspect_run("not-a-uuid")


@pytest.mark.asyncio
async def test_aclose_delegates() -> None:
    audit_port = mock.AsyncMock()
    service = AuditInspectionService(audit_port=audit_port)

    await service.aclose()

    audit_port.aclose.assert_awaited_once_with()
