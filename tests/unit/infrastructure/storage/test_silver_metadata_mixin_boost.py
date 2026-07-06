"""Coverage boost tests for Silver metadata mixin helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.infrastructure.storage.silver.finalization_models import (
    _SilverWriteFinalizationPreparationRequest,
    _SilverWriteResultFinalizationRequest,
)
from bioetl.infrastructure.storage.silver.metadata_mixin import (
    SilverWriterMetadataMixin,
)
from bioetl.infrastructure.storage.silver.metadata_result_finalization import (
    _build_silver_write_result,
)


class _Host(SilverWriterMetadataMixin):
    """Minimal host exposing the mixin surface for isolated tests."""

    def __init__(self) -> None:
        self._dq_calculator = MagicMock()
        self._metadata_writer = MagicMock()
        self._metadata_writer.write_silver_metadata = AsyncMock()
        self._metadata_coordinator = object()
        self._flat_structure = True
        self._audit = MagicMock()
        self._get_table_schema = AsyncMock(return_value=None)


@pytest.mark.unit
class TestSilverWriterMetadataMixinBoost:
    """Focused tests for the mixin-owned metadata helpers."""

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_passes_existing_schema_and_validation_errors(
        self,
    ) -> None:
        host = _Host()
        expected_metrics = BatchDQMetrics(total_records=1, valid_records=1)
        host._dq_calculator.calculate.return_value = expected_metrics
        host._get_table_schema.return_value = SimpleNamespace(names=("entity_id",))

        result = await host._compute_dq_metrics(
            "chembl.activity",
            [{"entity_id": "CHEMBL1"}],
            quarantined_count=2,
            validation_errors=("missing field",),
        )

        assert result is expected_metrics
        dq_input = host._dq_calculator.calculate.call_args.args[0]
        assert dq_input.existing_schema_fields == {"entity_id"}
        assert dq_input.quarantined_count == 2
        assert dq_input.validation_errors == ["missing field"]

    @pytest.mark.asyncio
    async def test_log_silver_audit_delegates_to_support_layer(self) -> None:
        host = _Host()
        log_event = AsyncMock()

        with patch(
            "bioetl.infrastructure.storage.silver.metadata_mixin._log_silver_audit_event",
            new=log_event,
        ):
            await host._log_silver_audit(
                table_name="chembl.activity",
                records=[{"entity_id": "CHEMBL1"}],
                mode=SilverWriteMode.MERGE,
                run_id=None,
                run_type=None,
                source_batch_id=None,
                ingestion_ts=None,
            )

        assert log_event.call_count == 1
        request = log_event.call_args.args[1]
        assert request.table_name == "chembl.activity"
        assert request.mode is SilverWriteMode.MERGE

    @pytest.mark.asyncio
    async def test_get_delta_version_returns_none_when_table_missing(self) -> None:
        host = _Host()

        with patch(
            "bioetl.infrastructure.storage.silver.metadata_mixin._read_delta_version",
            side_effect=DeltaTableNotFoundError("missing"),
        ) as read_delta_version:
            result = await host._get_delta_version("/tmp/silver/table")

        assert result is None
        read_delta_version.assert_called_once_with("/tmp/silver/table")

    def test_should_skip_silver_metadata_write_covers_guard_paths(self) -> None:
        host = _Host()

        assert (
            host._should_skip_silver_metadata_write(
                records=[],
                table_path="/tmp/silver/table",
                event_name="silver_metadata_skipped",
            )
            is True
        )

        host._metadata_writer = NoOpMetadataWriter()
        assert (
            host._should_skip_silver_metadata_write(
                records=[{"entity_id": "CHEMBL1"}],
                table_path="/tmp/silver/table",
                event_name="silver_metadata_skipped",
            )
            is True
        )

        host._metadata_writer = MagicMock()
        host._metadata_coordinator = None
        with pytest.raises(
            RuntimeError,
            match="MetadataCoordinator with create_silver_metadata_bundle is required",
        ):
            host._should_skip_silver_metadata_write(
                records=[{"entity_id": "CHEMBL1"}],
                table_path="/tmp/silver/table",
                event_name="silver_metadata_skipped",
            )

        host._metadata_coordinator = object()
        assert (
            host._should_skip_silver_metadata_write(
                records=[{"entity_id": "CHEMBL1"}],
                table_path="/tmp/silver/table",
                event_name="silver_metadata_skipped",
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_delegates_to_execute_helper(self) -> None:
        host = _Host()
        request = SimpleNamespace(records=[{"entity_id": "CHEMBL1"}], table_path="/tmp")

        with (
            patch.object(
                host,
                "_should_skip_silver_metadata_write",
                return_value=False,
            ) as should_skip,
            patch(
                "bioetl.infrastructure.storage.silver.metadata_mixin._execute_silver_metadata_write",
                new=AsyncMock(),
            ) as execute_write,
        ):
            await host._write_silver_metadata(request)

        should_skip.assert_called_once()
        execute_write.assert_awaited_once()
        assert execute_write.await_args.kwargs["request"] is request

    @pytest.mark.asyncio
    async def test_write_silver_merged_metadata_builds_request_and_delegates(
        self,
    ) -> None:
        host = _Host()
        merged_request = SimpleNamespace(records=[{"entity_id": "CHEMBL1"}])

        with (
            patch.object(
                host,
                "_should_skip_silver_metadata_write",
                return_value=False,
            ),
            patch(
                "bioetl.infrastructure.storage.silver.metadata_mixin._build_silver_merged_metadata_write_request",
                return_value=merged_request,
            ) as build_request,
            patch(
                "bioetl.infrastructure.storage.silver.metadata_mixin._execute_silver_metadata_write",
                new=AsyncMock(),
            ) as execute_write,
        ):
            await host._write_silver_merged_metadata(
                table_path="/tmp/silver/chembl/activity",
                table_name="chembl.activity",
                records=[{"entity_id": "CHEMBL1"}],
                primary_keys=["entity_id"],
                completed_at=datetime(2026, 1, 1, tzinfo=UTC),
                run_id="run-1",
                sources_used=["chembl"],
            )

        build_request.assert_called_once()
        assert execute_write.await_args.kwargs["request"] is merged_request

    @pytest.mark.asyncio
    async def test_write_silver_metadata_file_uses_flat_structure_and_identity(
        self,
    ) -> None:
        host = _Host()
        metadata = MagicMock()

        await host._write_silver_metadata_file(
            table_path="/tmp/silver/chembl/activity",
            metadata=metadata,
            table_name="chembl.activity",
            provider_name="chembl",
            entity_name="activity",
        )

        host._metadata_writer.write_silver_metadata.assert_awaited_once_with(
            "/tmp/silver/chembl/activity",
            metadata,
            table_name="chembl.activity",
            flat_structure=True,
            provider="chembl",
            entity="activity",
        )

    @pytest.mark.asyncio
    async def test_maybe_log_silver_audit_only_runs_when_enabled_and_records_present(
        self,
    ) -> None:
        host = _Host()
        host._log_silver_audit = AsyncMock()

        await host._maybe_log_silver_audit(
            table_name="chembl.activity",
            records=[],
            mode=SilverWriteMode.MERGE,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
        host._log_silver_audit.assert_not_awaited()

        await host._maybe_log_silver_audit(
            table_name="chembl.activity",
            records=[{"entity_id": "CHEMBL1"}],
            mode=SilverWriteMode.MERGE,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
        host._log_silver_audit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_finalize_and_prepare_wrappers_delegate_to_operations(self) -> None:
        host = _Host()
        final_result = MagicMock()
        prep_context = MagicMock()
        started_at = datetime(2026, 1, 1, tzinfo=UTC)
        finalize_request = _SilverWriteResultFinalizationRequest(
            table_name="chembl.activity",
            records=[{"entity_id": "CHEMBL1"}],
            table_path="/tmp/silver/chembl/activity",
            primary_keys=["entity_id"],
            validated_mode=SilverWriteMode.MERGE,
            bronze_refs=None,
            partition_cols=None,
            source_batch_id=None,
            started_at=started_at,
            start_perf=0.0,
        )
        prepare_request = _SilverWriteFinalizationPreparationRequest(
            table_name="chembl.activity",
            records=[{"entity_id": "CHEMBL1"}],
            table_path="/tmp/silver/chembl/activity",
            started_at=started_at,
            start_perf=0.0,
        )

        with (
            patch(
                "bioetl.infrastructure.storage.silver.metadata_mixin.finalize_silver_write_result_operation",
                new=AsyncMock(return_value=final_result),
            ) as finalize_op,
            patch(
                "bioetl.infrastructure.storage.silver.metadata_mixin.prepare_silver_write_finalization_context_operation",
                new=AsyncMock(return_value=prep_context),
            ) as prepare_op,
        ):
            assert (
                await host._finalize_silver_write_result(finalize_request)
                is final_result
            )
            assert (
                await host._prepare_silver_write_finalization_context(prepare_request)
                is prep_context
            )

        finalize_op.assert_awaited_once_with(host, finalize_request)
        prepare_op.assert_awaited_once_with(
            host,
            prepare_request,
            perf_counter=ANY,
        )

    def test_build_silver_write_result_returns_result_only_with_version(self) -> None:
        assert (
            _build_silver_write_result(
                table_name="chembl.activity",
                table_path="/tmp/silver/chembl/activity",
                version_after=None,
                records_count=1,
            )
            is None
        )
        result = _build_silver_write_result(
            table_name="chembl.activity",
            table_path="/tmp/silver/chembl/activity",
            version_after=5,
            records_count=1,
        )
        assert result is not None
        assert result.delta_version == 5
