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

from tests.helpers.synthetic_paths import synthetic_test_root
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pyarrow as pa
import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.operations.postwrite_operations import (
    SilverPostwriteOperations,
)
from bioetl.infrastructure.storage.silver.postwrite_mixin import (
    SilverWriterPostwriteMixin,
)
from bioetl.infrastructure.storage.silver.validation_operations import (
    _PreparedSilverWritePayload,
)

TEST_ROOT = synthetic_test_root("bioetl-silver-postwrite")
SILVER_ROOT = str(TEST_ROOT / "silver")
SILVER_TABLE_PATH = str(TEST_ROOT / "silver" / "test.table")
SILVER_EXPORT_PATH = str(TEST_ROOT / "silver" / "test.table.csv")


def _build_payload() -> _PreparedSilverWritePayload:
    records = [{"entity_id": "CHEMBL1", "value": 1.0}]
    return _PreparedSilverWritePayload(
        records=records,
        validated_mode=SilverWriteMode.MERGE,
        table_path=SILVER_TABLE_PATH,
        arrow_data=pa.Table.from_pylist(records),
        schema_mode=None,
        merge_schema=False,
    )


def _build_context() -> SimpleNamespace:
    return SimpleNamespace(
        table_name="test.table",
        mode="merge",
        primary_keys=["entity_id"],
        bronze_refs=None,
        partition_cols=["entity_id"],
        run_id="run-123",
        run_type="incremental",
        source_batch_id="batch-456",
        ingestion_ts=datetime(2026, 4, 18, 12, 0, tzinfo=UTC),
        started_at=datetime(2026, 4, 18, 11, 59, tzinfo=UTC),
        start_perf=1.5,
    )


class _PostwriteMixinHarness(SilverWriterPostwriteMixin):
    def __init__(self) -> None:
        self._maybe_export_csv = AsyncMock()
        self._maybe_log_silver_audit = AsyncMock()
        self._finalize_silver_write_result = AsyncMock(return_value="finalized")


@pytest.mark.asyncio
async def test_postwrite_mixin_routes_through_compatibility_hooks() -> None:
    payload = _build_payload()
    ctx = _build_context()
    harness = _PostwriteMixinHarness()

    result = await harness._complete_silver_write_pipeline(
        ctx=ctx,
        payload=payload,
    )

    assert result == "finalized"
    harness._maybe_export_csv.assert_awaited_once_with(
        table_name="test.table",
        arrow_data=payload.arrow_data,
        mode="merge",
        validated_mode=SilverWriteMode.MERGE,
        primary_keys=["entity_id"],
    )
    harness._maybe_log_silver_audit.assert_awaited_once_with(
        table_name="test.table",
        records=payload.records,
        mode=SilverWriteMode.MERGE,
        run_id="run-123",
        run_type="incremental",
        source_batch_id="batch-456",
        ingestion_ts=ctx.ingestion_ts,
    )
    harness._finalize_silver_write_result.assert_awaited_once()
    finalize_request = harness._finalize_silver_write_result.await_args.args[0]
    assert isinstance(finalize_request, _SilverWriteResultFinalizationRequest)
    assert finalize_request.table_name == "test.table"
    assert finalize_request.records == payload.records
    assert finalize_request.table_path == SILVER_TABLE_PATH
    assert finalize_request.primary_keys == ["entity_id"]
    assert finalize_request.validated_mode is SilverWriteMode.MERGE
    assert finalize_request.bronze_refs is None
    assert finalize_request.partition_cols == ["entity_id"]
    assert finalize_request.source_batch_id == "batch-456"
    assert finalize_request.started_at == ctx.started_at
    assert finalize_request.start_perf == 1.5


@pytest.mark.asyncio
async def test_postwrite_operations_preserve_service_specific_export_and_audit() -> (
    None
):
    payload = _build_payload()
    ctx = _build_context()
    maintenance = Mock()
    maintenance.maybe_export_csv = AsyncMock()
    metadata = Mock()
    metadata.log_silver_audit = AsyncMock()
    host = SimpleNamespace(
        base_path=SILVER_ROOT,
        _maintenance=maintenance,
        _metadata=metadata,
        _maybe_export_csv=AsyncMock(),
        _maybe_log_silver_audit=AsyncMock(),
        _finalize_silver_write_result=AsyncMock(return_value="finalized"),
    )
    operations = SilverPostwriteOperations(host)

    result = await operations._complete_silver_write_pipeline(
        ctx=ctx,
        payload=payload,
    )

    assert result == "finalized"
    # Check that maybe_export_csv was called with correct parameters
    # Use path normalization to handle different path separators across platforms
    maintenance.maybe_export_csv.assert_awaited_once()
    call_kwargs = maintenance.maybe_export_csv.call_args.kwargs

    assert call_kwargs["table_name"] == "test.table"
    assert call_kwargs["arrow_data"] is payload.arrow_data
    assert call_kwargs["primary_keys"] == ["entity_id"]
    assert call_kwargs["audit_timestamp"] == ctx.ingestion_ts
    # Normalize paths for comparison to handle different separators
    expected_path = str(Path(SILVER_EXPORT_PATH).resolve())
    actual_path = str(Path(call_kwargs["export_path"]).resolve())
    assert expected_path == actual_path, f"Expected {expected_path}, got {actual_path}"
    host._maybe_export_csv.assert_not_awaited()
    metadata.log_silver_audit.assert_awaited_once_with(
        table_name="test.table",
        records=payload.records,
        mode="merge",
        validated_mode=SilverWriteMode.MERGE,
        run_id="run-123",
        run_type="incremental",
        source_batch_id="batch-456",
        ingestion_ts=ctx.ingestion_ts,
    )
    host._finalize_silver_write_result.assert_awaited_once()
    finalize_request = host._finalize_silver_write_result.await_args.args[0]
    assert isinstance(finalize_request, _SilverWriteResultFinalizationRequest)
    assert finalize_request.table_name == "test.table"
    assert finalize_request.records == payload.records
    assert finalize_request.table_path == SILVER_TABLE_PATH
    assert finalize_request.primary_keys == ["entity_id"]
    assert finalize_request.validated_mode is SilverWriteMode.MERGE
    assert finalize_request.bronze_refs is None
    assert finalize_request.partition_cols == ["entity_id"]
    assert finalize_request.source_batch_id == "batch-456"
    assert finalize_request.started_at == ctx.started_at
    assert finalize_request.start_perf == 1.5
