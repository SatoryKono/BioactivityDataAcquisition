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
"""Unit tests for Silver maintenance operations timestamp injection seams."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.silver.operations.maintenance_operations import (
    SilverMaintenanceOperations,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maybe_export_csv_uses_explicit_audit_timestamp() -> None:
    csv_exporter = MagicMock()
    csv_exporter.export = AsyncMock(return_value=None)
    retention_manager = MagicMock()
    metrics = MagicMock()
    audit = MagicMock()
    fallback_timestamp = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    timestamp_factory = MagicMock(return_value=fallback_timestamp)
    explicit_timestamp = datetime(2026, 5, 2, 9, 30, tzinfo=UTC)
    operations = SilverMaintenanceOperations(
        csv_exporter=csv_exporter,
        retention_manager=retention_manager,
        pipeline_name="chembl_activity",
        metrics=metrics,
        audit=audit,
        audit_timestamp_factory=timestamp_factory,
    )

    await operations.maybe_export_csv(
        table_name="chembl.activity",
        arrow_data=pa.table({"id": [1], "value": [1.0]}),
        export_path="silver/chembl/activity.csv",
        audit_timestamp=explicit_timestamp,
        primary_keys=["id"],
    )

    timestamp_factory.assert_not_called()
    audit.log_event.assert_called_once()
    assert audit.log_event.call_args.kwargs["timestamp"] == explicit_timestamp


@pytest.mark.unit
@pytest.mark.asyncio
async def test_maybe_export_csv_failure_logs_explicit_timestamp() -> None:
    csv_exporter = MagicMock()
    csv_exporter.export = AsyncMock(side_effect=RuntimeError("csv boom"))
    retention_manager = MagicMock()
    metrics = MagicMock()
    audit = MagicMock()
    timestamp_factory = MagicMock(return_value=datetime(2026, 5, 1, 12, 0, tzinfo=UTC))
    explicit_timestamp = datetime(2026, 5, 2, 10, 45, tzinfo=UTC)
    operations = SilverMaintenanceOperations(
        csv_exporter=csv_exporter,
        retention_manager=retention_manager,
        pipeline_name="chembl_activity",
        metrics=metrics,
        audit=audit,
        audit_timestamp_factory=timestamp_factory,
    )

    with pytest.raises(RuntimeError, match="csv boom"):
        await operations.maybe_export_csv(
            table_name="chembl.activity",
            arrow_data=pa.table({"id": [1], "value": [1.0]}),
            export_path="silver/chembl/activity.csv",
            audit_timestamp=explicit_timestamp,
            primary_keys=["id"],
        )

    timestamp_factory.assert_not_called()
    audit.log_event.assert_called_once()
    assert audit.log_event.call_args.kwargs["timestamp"] == explicit_timestamp


@pytest.mark.unit
@pytest.mark.asyncio
async def test_vacuum_uses_injected_timestamp_factory_when_missing() -> None:
    csv_exporter = MagicMock()
    retention_manager = MagicMock()
    retention_manager.vacuum = AsyncMock(return_value=["a", "b"])
    metrics = MagicMock()
    audit = MagicMock()
    fallback_timestamp = datetime(2026, 5, 2, 11, 15, tzinfo=UTC)
    timestamp_factory = MagicMock(return_value=fallback_timestamp)
    operations = SilverMaintenanceOperations(
        csv_exporter=csv_exporter,
        retention_manager=retention_manager,
        pipeline_name="chembl_activity",
        metrics=metrics,
        audit=audit,
        audit_timestamp_factory=timestamp_factory,
    )

    await operations.vacuum("chembl.activity", 24, dry_run=True)

    timestamp_factory.assert_called_once_with()
    audit.log_event.assert_called_once()
    assert audit.log_event.call_args.kwargs["timestamp"] == fallback_timestamp


@pytest.mark.unit
@pytest.mark.asyncio
async def test_optimize_prefers_explicit_timestamp_over_factory() -> None:
    csv_exporter = MagicMock()
    retention_manager = MagicMock()
    retention_manager.optimize = AsyncMock(return_value={"optimized": 3})
    metrics = MagicMock()
    audit = MagicMock()
    timestamp_factory = MagicMock(return_value=datetime(2026, 5, 2, 12, 0, tzinfo=UTC))
    explicit_timestamp = datetime(2026, 5, 2, 12, 1, tzinfo=UTC)
    operations = SilverMaintenanceOperations(
        csv_exporter=csv_exporter,
        retention_manager=retention_manager,
        pipeline_name="chembl_activity",
        metrics=metrics,
        audit=audit,
        audit_timestamp_factory=timestamp_factory,
    )

    await operations.optimize(
        "chembl.activity",
        zorder_by=["id"],
        audit_timestamp=explicit_timestamp,
        target_size=1024,
    )

    timestamp_factory.assert_not_called()
    audit.log_event.assert_called_once()
    assert audit.log_event.call_args.kwargs["timestamp"] == explicit_timestamp
