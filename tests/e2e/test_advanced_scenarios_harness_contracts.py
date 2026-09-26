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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Deterministic fixture-mode harness contracts for advanced E2E quarantine flows."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from bioetl.domain.types import BatchID
from tests.helpers.deterministic_ids import deterministic_uuid
from tests.e2e.test_advanced_scenarios_e2e import (
    _make_threadless_quarantine_harness_adapter,
)


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_quarantine_records_are_persisted_via_harness_adapter_contract(
    e2e_data_dir: Path,
):
    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.domain.types import ErrorType
    from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter

    quarantine_path = e2e_data_dir / "quarantine"
    quarantine_path.mkdir(exist_ok=True)
    quarantine = _make_threadless_quarantine_harness_adapter(
        UnifiedQuarantineAdapter(base_path=str(quarantine_path))
    )
    manager = QuarantineRuntimeService(
        quarantine_port=quarantine, pipeline_name="test_pipeline"
    )

    await manager.quarantine_record(
        record={"entity_id": "test_entity_1", "data": {"value": 123}},
        error_type=ErrorType.DATA_QUALITY,
        batch_id=BatchID(deterministic_uuid("advanced.harness.quarantine.batch")),
        error_details="Test DQ error",
        ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    assert (quarantine_path / "_delta_log").exists()


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.timeout(600)
async def test_quarantine_can_be_inspected_via_harness_adapter_contract(
    e2e_data_dir: Path,
):
    from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter

    quarantine_path = e2e_data_dir / "quarantine"
    quarantine_path.mkdir(exist_ok=True)
    quarantine = _make_threadless_quarantine_harness_adapter(
        UnifiedQuarantineAdapter(base_path=str(quarantine_path))
    )

    for i in range(3):
        await quarantine.write(
            pipeline="test_pipeline",
            error_code="DataQualityError",
            payload={"entity_id": f"entity_{i}"},
            bronze_batch_id=BatchID(
                deterministic_uuid("advanced.harness.quarantine.batch")
            ),
            metadata={"error_message": f"Error {i}"},
            ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

    entries = await quarantine.inspect(pipeline="test_pipeline")
    assert len(entries) >= 3, f"Expected at least 3 entries, got {len(entries)}"
