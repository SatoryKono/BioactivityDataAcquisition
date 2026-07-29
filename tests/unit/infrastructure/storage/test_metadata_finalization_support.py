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
"""Focused coverage tests for Silver metadata finalization support helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.infrastructure.storage.delta.table_ops import (
    normalize_delta_filesystem_path,
)
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_result_finalization import (
    _build_silver_write_result as _build_metadata_result,
    _prepare_silver_write_finalization_context as _prepare_metadata_result_context,
    _read_delta_version,
)
from bioetl.infrastructure.storage.silver.operations.metadata_finalization_support import (
    _build_silver_write_result as _build_support_result,
    _finalize_silver_write_result,
    _prepare_silver_write_finalization_context,
    _require_metadata_coordinator,
    _source_batch_ids,
)
from bioetl.infrastructure.storage.silver.prepared_operation_models import (
    _PreparedSilverWriteFinalizationContext,
)


@pytest.mark.unit
def test_require_metadata_coordinator_rejects_missing_value() -> None:
    with pytest.raises(
        RuntimeError,
        match="MetadataCoordinatorPort is required for Silver metadata publication",
    ):
        _require_metadata_coordinator(None)


@pytest.mark.unit
def test_source_batch_ids_normalizes_optional_identity() -> None:
    assert _source_batch_ids(None) is None
    assert _source_batch_ids(123) == ["123"]


@pytest.mark.unit
def test_build_silver_write_result_helpers_cover_none_and_success_cases() -> None:
    assert (
        _build_metadata_result(
            table_name="chembl.activity",
            table_path="/tmp/silver/chembl/activity",
            version_after=None,
            records_count=2,
        )
        is None
    )
    support_result = _build_support_result(
        table_name="chembl.activity",
        table_path="/tmp/silver/chembl/activity",
        version_after=7,
        records_count=2,
    )
    assert support_result is not None
    assert support_result.delta_version == 7
    assert support_result.record_count == 2


@pytest.mark.asyncio
async def test_prepare_metadata_result_context_uses_request_and_perf_counter() -> None:
    started_at = datetime(2026, 1, 1, tzinfo=UTC)
    host = SimpleNamespace(
        _compute_dq_metrics=AsyncMock(return_value=BatchDQMetrics(total_records=2)),
        _get_delta_version=AsyncMock(return_value=11),
    )
    request = _SilverWriteFinalizationPreparationRequest(
        table_name="chembl.activity",
        records=[{"entity_id": "CHEMBL1"}],
        table_path="/tmp/silver/chembl/activity",
        started_at=started_at,
        start_perf=10.0,
        quarantined_count=3,
        validation_errors=("missing",),
    )

    context = await _prepare_metadata_result_context(
        host,
        request,
        perf_counter=lambda: 14.5,
    )

    host._compute_dq_metrics.assert_awaited_once_with(
        "chembl.activity",
        [{"entity_id": "CHEMBL1"}],
        quarantined_count=3,
        validation_errors=("missing",),
    )
    host._get_delta_version.assert_awaited_once_with("/tmp/silver/chembl/activity")
    assert context.version_after == 11
    assert context.completed_at == started_at + timedelta(seconds=4.5)


@pytest.mark.unit
def test_read_delta_version_delegates_to_delta_table() -> None:
    table = MagicMock()
    table.version.return_value = 12

    with patch(
        "bioetl.infrastructure.storage.silver.metadata_result_finalization.DeltaTable",
        return_value=table,
    ) as delta_table:
        result = _read_delta_version("/tmp/silver/chembl/activity")

    delta_table.assert_called_once_with(
        normalize_delta_filesystem_path("/tmp/silver/chembl/activity")
    )
    assert result == 12


@pytest.mark.asyncio
async def test_prepare_silver_write_finalization_context_collects_dq_version_and_time() -> (
    None
):
    metadata_ops = SimpleNamespace(
        _resolve_finalization_dq_metrics=AsyncMock(
            return_value=BatchDQMetrics(total_records=3)
        ),
        _resolve_version_after=AsyncMock(return_value=5),
    )
    started_at = datetime(2026, 1, 1, tzinfo=UTC)
    request = _SilverWriteFinalizationPreparationRequest(
        table_name="chembl.activity",
        records=[{"entity_id": "CHEMBL1"}],
        table_path="/tmp/silver/chembl/activity",
        started_at=started_at,
        start_perf=100.0,
        quarantined_count=2,
        validation_errors=("missing",),
        primary_keys=["entity_id"],
        validated_mode=SilverWriteMode.APPEND,
    )

    context = await _prepare_silver_write_finalization_context(
        metadata_ops,
        request,
        perf_counter=lambda: 102.25,
    )

    metadata_ops._resolve_finalization_dq_metrics.assert_awaited_once_with(
        table_name="chembl.activity",
        records=[{"entity_id": "CHEMBL1"}],
        quarantined_count=2,
        validation_errors=("missing",),
    )
    metadata_ops._resolve_version_after.assert_awaited_once_with(
        "/tmp/silver/chembl/activity"
    )
    assert context == _PreparedSilverWriteFinalizationContext(
        dq_metrics=BatchDQMetrics(total_records=3),
        version_after=5,
        completed_at=started_at + timedelta(seconds=2.25),
    )


@pytest.mark.asyncio
async def test_finalize_silver_write_result_persists_metadata_and_returns_result() -> (
    None
):
    started_at = datetime(2026, 1, 1, tzinfo=UTC)
    prepared_context = _PreparedSilverWriteFinalizationContext(
        dq_metrics=BatchDQMetrics(total_records=2, valid_records=2),
        version_after=9,
        completed_at=started_at + timedelta(seconds=3),
    )
    metadata = object()
    coordinator = MagicMock()
    coordinator.create_silver_metadata.return_value = metadata
    metadata_ops = SimpleNamespace(
        _metadata_coordinator=coordinator,
        _prepare_silver_write_finalization_context=AsyncMock(
            return_value=prepared_context
        ),
        _persist_silver_metadata=AsyncMock(return_value=None),
    )
    request = _SilverWriteResultFinalizationRequest(
        table_name="chembl.activity",
        records=[{"entity_id": "CHEMBL1"}, {"entity_id": "CHEMBL2"}],
        table_path="/tmp/silver/chembl/activity",
        primary_keys=["entity_id"],
        validated_mode=SilverWriteMode.MERGE,
        bronze_refs=[],
        partition_cols=["year"],
        source_batch_id="batch-1",
        started_at=started_at,
        start_perf=10.0,
        quarantined_count=1,
        validation_errors=("missing",),
    )

    result = await _finalize_silver_write_result(metadata_ops, request)

    metadata_ops._prepare_silver_write_finalization_context.assert_awaited_once()
    prepared_request = (
        metadata_ops._prepare_silver_write_finalization_context.await_args.args[0]
    )
    assert prepared_request.table_name == request.table_name
    assert prepared_request.primary_keys == request.primary_keys
    assert prepared_request.validated_mode is request.validated_mode
    silver_input = coordinator.create_silver_metadata.call_args.args[0]
    assert silver_input.source_batch_ids == ["batch-1"]
    assert silver_input.version_after == 9
    assert silver_input.partition_by == ["year"]
    metadata_ops._persist_silver_metadata.assert_awaited_once_with(
        metadata=metadata,
        table_name="chembl.activity",
        table_path="/tmp/silver/chembl/activity",
    )
    assert result is not None
    assert result.delta_version == 9
    assert result.record_count == 2
