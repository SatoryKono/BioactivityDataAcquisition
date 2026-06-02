"""Unit tests for Silver metadata operations service."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _SilverMetadataWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations.metadata_operations import (
    SilverMetadataOperations,
)


def _metadata_coordinator(
    *,
    started_at: datetime | None = None,
) -> MetadataCoordinator:
    """Build a canonical Silver metadata coordinator with control-plane anchors."""
    context = RunContext.create(
        run_id=deterministic_run_uuid_from_callsite(
            "test_silver_metadata_operations_service"
        ),
        run_type=RunType.INCREMENTAL,
        started_at=started_at or datetime(2025, 1, 15, 12, 0, tzinfo=UTC),
        provider="chembl",
        entity="activity",
        manifest_id="manifest-canonical",
        execution_fingerprint="fingerprint-canonical",
        effective_config_hash="effective-config-canonical",
        effective_config_artifact_id="effective-config-artifact-canonical",
        contract_ref="contracts/chembl/activity",
        contract_version="1.2.3",
        dq_contract_compatibility_hash="dq-compat-canonical",
    )
    return MetadataCoordinator(context)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_metadata_uses_record_ingestion_anchor_when_explicit_time_missing() -> (
    None
):
    """Metadata runtime timestamps should reuse deterministic record anchors."""
    expected = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
    captured: dict[str, object] = {}

    async def capture_write(**kwargs):
        await asyncio.sleep(0)
        captured.update(kwargs)
        return None

    metadata_writer = MagicMock()
    metadata_writer.write_silver_metadata = capture_write
    ops = SilverMetadataOperations(
        _logger=MagicMock(),
        _metadata_writer=metadata_writer,
        _metadata_coordinator=_metadata_coordinator(started_at=expected),
    )

    await ops.write_silver_metadata(
        table_name="chembl.activity",
        dq_metrics=BatchDQMetrics(
            total_records=1,
            valid_records=1,
            error_records=0,
            warning_records=0,
        ),
        records=[
            {
                "entity_id": "CHEMBL1",
                "_ingestion_ts": expected.isoformat(),
            }
        ],
    )

    metadata = captured["metadata"]
    assert metadata.runtime.started_at_utc == expected
    assert metadata.runtime.completed_at_utc == expected


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_metadata_emits_canonical_success_metric() -> None:
    """Silver metadata write success should use the registered storage metric."""
    metadata_writer = MagicMock()

    async def capture_write(**kwargs):
        await asyncio.sleep(0)
        return None

    metadata_writer.write_silver_metadata = capture_write
    metrics = MagicMock()
    ops = SilverMetadataOperations(
        _logger=MagicMock(),
        _metadata_writer=metadata_writer,
        _metadata_coordinator=_metadata_coordinator(),
        _metrics=metrics,
    )

    await ops.write_silver_metadata(
        table_name="chembl.activity",
        dq_metrics=BatchDQMetrics(
            total_records=1,
            valid_records=1,
            error_records=0,
            warning_records=0,
        ),
        records=[
            {
                "entity_id": "CHEMBL1",
                "_ingestion_ts": datetime(2025, 1, 15, 12, 0, tzinfo=UTC).isoformat(),
            }
        ],
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_metadata_write_outcomes_total",
        1,
        {
            "layer": "silver",
            "provider": "chembl",
            "pipeline": "chembl_activity",
            "status": "success",
            "final_reason": "completed",
        },
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_metadata_uses_coordinator_control_plane_anchors() -> None:
    """Silver sidecar support must not derive provenance from record payloads."""
    captured: dict[str, object] = {}

    async def capture_write(**kwargs):
        await asyncio.sleep(0)
        captured.update(kwargs)
        return None

    metadata_writer = MagicMock()
    metadata_writer.write_silver_metadata = capture_write
    ops = SilverMetadataOperations(
        _logger=MagicMock(),
        _metadata_writer=metadata_writer,
        _metadata_coordinator=_metadata_coordinator(),
    )

    await ops.write_silver_metadata(
        table_name="chembl.activity",
        dq_metrics=BatchDQMetrics(
            total_records=1,
            valid_records=1,
            error_records=0,
            warning_records=0,
        ),
        records=[
            {
                "entity_id": "CHEMBL1",
                "_ingestion_ts": datetime(2025, 1, 15, 12, 0, tzinfo=UTC).isoformat(),
                "_manifest_id": "manifest-from-record",
                "_execution_fingerprint": "fingerprint-from-record",
                "_effective_config_hash": "effective-config-from-record",
                "_effective_config_artifact_id": "artifact-from-record",
                "_contract_ref": "contracts/from-record",
                "_contract_version": "9.9.9",
                "_dq_contract_compatibility_hash": "dq-compat-from-record",
            }
        ],
    )

    metadata = captured["metadata"]
    assert metadata.runtime.manifest_id == "manifest-canonical"
    assert metadata.pipeline.execution_fingerprint == "fingerprint-canonical"
    assert metadata.pipeline.effective_config_hash == "effective-config-canonical"
    assert (
        metadata.pipeline.effective_config_artifact_id
        == "effective-config-artifact-canonical"
    )
    assert metadata.pipeline.contract_ref == "contracts/chembl/activity"
    assert metadata.pipeline.contract_version == "1.2.3"
    assert metadata.pipeline.dq_contract_compatibility_hash == "dq-compat-canonical"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_finalization_dq_metrics_normalizes_mixed_struct_and_string_values() -> (
    None
):
    """Mixed structured/string column values should not break DQ metrics finalization."""
    dq_calculator = MagicMock()
    dq_calculator.calculate.return_value = BatchDQMetrics(
        total_records=2,
        valid_records=2,
        error_records=0,
        warning_records=0,
    )
    ops = SilverMetadataOperations(
        _logger=MagicMock(),
        _dq_calculator=dq_calculator,
    )

    records = [
        {
            "entity_id": "CHEMBL1",
            "assay_taxonomy": {
                "assay_class_id": 322,
                "class_type": "In vivo efficacy",
            },
        },
        {
            "entity_id": "CHEMBL2",
            "assay_taxonomy": '{"assay_class_id":322,"class_type":"In vivo efficacy"}',
        },
    ]

    metrics = await ops._resolve_finalization_dq_metrics(
        table_name="chembl.assay",
        records=records,
    )

    assert metrics.total_records == 2
    dq_input = dq_calculator.calculate.call_args.args[0]
    normalized_records = dq_input.records
    assert all(isinstance(row["assay_taxonomy"], str) for row in normalized_records)
    assert dq_input.validation_errors is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_compute_dq_metrics_passes_explicit_validation_context() -> None:
    """Explicit DQ validation context should reach the calculator input."""
    import pyarrow as pa

    dq_calculator = MagicMock()
    dq_calculator.calculate.return_value = BatchDQMetrics(
        total_records=3,
        valid_records=2,
        error_records=1,
        warning_records=0,
    )
    ops = SilverMetadataOperations(
        _logger=MagicMock(),
        _dq_calculator=dq_calculator,
    )

    await ops.compute_dq_metrics(
        arrow_data=pa.Table.from_pylist(
            [
                {"entity_id": "CHEMBL1"},
                {"entity_id": "CHEMBL2"},
            ]
        ),
        quarantined_count=1,
        validation_errors=("missing required activity_id",),
    )

    dq_input = dq_calculator.calculate.call_args.args[0]
    assert dq_input.quarantined_count == 1
    assert dq_input.validation_errors == ["missing required activity_id"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_finalization_context_passes_explicit_validation_context(
    tmp_path,
) -> None:
    """Finalization prep should forward validation context into DQ resolution."""
    started_at = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
    dq_metrics = BatchDQMetrics(
        total_records=3,
        valid_records=2,
        error_records=1,
        warning_records=0,
    )
    ops = SilverMetadataOperations(_logger=MagicMock())
    resolve_finalization_dq_metrics = AsyncMock(return_value=dq_metrics)
    resolve_version_after = AsyncMock(return_value=7)

    with (
        patch.object(
            SilverMetadataOperations,
            "_resolve_finalization_dq_metrics",
            resolve_finalization_dq_metrics,
        ),
        patch.object(
            SilverMetadataOperations,
            "_resolve_version_after",
            resolve_version_after,
        ),
    ):
        context = await ops._prepare_silver_write_finalization_context(
            table_name="chembl.activity",
            records=[{"activity_id": "A1"}, {"activity_id": "A2"}],
            table_path=str(tmp_path / "chembl" / "activity"),
            primary_keys=["activity_id"],
            validated_mode=SilverWriteMode.MERGE,
            quarantined_count=1,
            validation_errors=("missing required activity_id",),
            started_at=started_at,
            start_perf=0.0,
        )

    resolve_finalization_dq_metrics.assert_awaited_once_with(
        table_name="chembl.activity",
        records=[{"activity_id": "A1"}, {"activity_id": "A2"}],
        quarantined_count=1,
        validation_errors=("missing required activity_id",),
    )
    assert context.dq_metrics is dq_metrics
    assert context.version_after == 7
    assert context.completed_at >= started_at


@pytest.mark.unit
@pytest.mark.asyncio
async def test_internal_write_silver_metadata_uses_canonical_execution_path(
    tmp_path,
) -> None:
    """Composition-backed metadata ops should delegate sidecar writes to canonical helpers."""
    metadata_coordinator = MagicMock()
    metadata_writer = MagicMock()
    ops = SilverMetadataOperations(
        _logger=MagicMock(),
        _metadata_writer=metadata_writer,
        _metadata_coordinator=metadata_coordinator,
    )
    execute_silver_metadata_write = AsyncMock()

    with patch(
        "bioetl.infrastructure.storage.silver.operations.metadata_operations."
        "_execute_silver_metadata_write",
        execute_silver_metadata_write,
    ):
        await ops._write_silver_metadata(
            _SilverMetadataWriteRequest(
                table_path=str(tmp_path / "silver" / "chembl" / "activity"),
                table_name="chembl.activity",
                records=[{"activity_id": "A1"}],
                primary_keys=["activity_id"],
                mode=SilverWriteMode.MERGE,
            )
        )

    execute_silver_metadata_write.assert_awaited_once()
