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
"""Unit tests for QuarantineRuntimeService."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_run_uuid_from_callsite,
)

import pytest

from bioetl.application.core.quarantine_manager import (
    DQQuarantineEntry,
    FilteredQuarantineEntry,
    QuarantineRuntimeService,
)
from bioetl.domain.aggregates.events import QuarantineEntryCreated, RecordQuarantined
from bioetl.domain.types import ErrorType


@pytest.fixture
def quarantine_port() -> MagicMock:
    """Create a mock quarantine port."""
    port = MagicMock()
    port.write = AsyncMock()
    port.write_many = AsyncMock()
    return port


@pytest.fixture
def metrics() -> MagicMock:
    """Create a mock metrics port."""
    return MagicMock()


@pytest.mark.unit
class TestQuarantineManagerBulkWrites:
    """Tests for batch quarantine helpers."""

    @pytest.mark.asyncio
    async def test_quarantine_filtered_records_batches_writes_and_metrics(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        batch_id = deterministic_batch_uuid_from_callsite("test_quarantine_manager")
        run_id = deterministic_run_uuid_from_callsite("test_quarantine_manager")
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_filtered_records(
            [
                FilteredQuarantineEntry({"activity_id": "1"}, "filtered"),
                FilteredQuarantineEntry({"activity_id": "2"}, "filtered"),
            ],
            batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

        quarantine_port.write_many.assert_awaited_once()
        requests = quarantine_port.write_many.await_args.args[0]
        assert requests[0]["run_id"] == run_id
        assert requests[0]["metadata"]["classification"] == "filter_rejection"
        assert requests[0]["metadata"]["quarantine_category"] == "silver_filter"
        assert "quasi_quarantine" not in requests[0]["metadata"]
        metrics.increment_counter.assert_any_call(
            "bioetl_quarantine_records_total",
            2,
            {
                "pipeline": "chembl_activity",
                "reason": "FILTERED_OUT_SILVER",
            },
        )

    @pytest.mark.asyncio
    async def test_quarantine_filtered_record_preserves_structured_details_and_ignores_message_override(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Structured reason fields should survive without replacing display text."""
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        batch_id = deterministic_batch_uuid_from_callsite("test_quarantine_manager")
        run_id = deterministic_run_uuid_from_callsite("test_quarantine_manager")
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_filtered_record(
            record={"activity_id": "1"},
            batch_id=batch_id,
            error_details="display text",
            run_id=run_id,
            details={
                "message": "unstable text that must not override display message",
                "reason_code": "required_field_missing",
                "rule_type": "required_fields",
                "field": "activity_id",
                "operator": "is_not_null",
            },
            ingestion_ts=ingestion_ts,
        )

        quarantine_port.write.assert_awaited_once()
        request = quarantine_port.write.await_args.kwargs
        assert request["run_id"] == run_id
        assert request["metadata"]["error_details"] == {
            "message": "display text",
            "reason_code": "required_field_missing",
            "rule_type": "required_fields",
            "field": "activity_id",
            "operator": "is_not_null",
        }
        assert request["metadata"]["classification"] == "filter_rejection"
        assert request["metadata"]["quarantine_category"] == "silver_filter"

    @pytest.mark.asyncio
    async def test_quarantine_records_aggregates_metrics_by_error_type(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        batch_id = deterministic_batch_uuid_from_callsite("test_quarantine_manager")
        run_id = deterministic_run_uuid_from_callsite("test_quarantine_manager")
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_records(
            [
                ({"activity_id": "1"}, ErrorType.INVALID_DATA, "bad"),
                ({"activity_id": "2"}, ErrorType.INVALID_DATA, "bad"),
                ({"activity_id": "3"}, ErrorType.MISSING_REQUIRED_FIELD, "missing"),
            ],
            batch_id,
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

        quarantine_port.write_many.assert_awaited_once()
        requests = quarantine_port.write_many.await_args.args[0]
        assert requests[0]["run_id"] == run_id
        metrics.increment_counter.assert_any_call(
            "bioetl_quarantine_records_total",
            2,
            {
                "pipeline": "chembl_activity",
                "reason": ErrorType.INVALID_DATA.value,
            },
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_quarantine_records_total",
            1,
            {
                "pipeline": "chembl_activity",
                "reason": ErrorType.MISSING_REQUIRED_FIELD.value,
            },
        )

    @pytest.mark.asyncio
    async def test_quarantine_record_single_writes_and_increments_metric(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Single-record quarantine writes to port and increments metrics."""
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        batch_id = deterministic_batch_uuid_from_callsite("test_quarantine_manager")
        run_id = deterministic_run_uuid_from_callsite("test_quarantine_manager")
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_record(
            record={"activity_id": "1"},
            error_type=ErrorType.INVALID_DATA,
            batch_id=batch_id,
            error_details="bad value",
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

        quarantine_port.write.assert_awaited_once()
        assert quarantine_port.write.await_args.kwargs["run_id"] == run_id
        # MetricsPort emits counters directly (track_* lives on batch_metrics).
        metrics.increment_counter.assert_any_call(
            "bioetl_dq_records_quarantined_total",
            1,
            {
                "pipeline": "chembl_activity",
                "error_type": ErrorType.INVALID_DATA.value,
                "run_type": "unknown",
            },
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_records_processed_total",
            1,
            {
                "pipeline": "chembl_activity",
                "stage": "quarantined",
                "run_type": "unknown",
            },
        )

    @pytest.mark.asyncio
    async def test_runtime_batch_metrics_path_emits_run_type_labels(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Runtime DI path should delegate quarantine counters to batch metrics."""
        from bioetl.application.core.batch_metrics import BatchMetricsRecorderService

        batch_metrics = BatchMetricsRecorderService(
            metrics=metrics,
            pipeline_label="chembl_activity",
            run_type_label="incremental",
        )
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
            batch_metrics=batch_metrics,
            run_type="incremental",
        )
        batch_id = deterministic_batch_uuid_from_callsite("test_quarantine_manager")
        run_id = deterministic_run_uuid_from_callsite("test_quarantine_manager")
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_record(
            record={"activity_id": "1"},
            error_type=ErrorType.INVALID_DATA,
            batch_id=batch_id,
            error_details="bad value",
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

        metrics.increment_counter.assert_any_call(
            "bioetl_dq_records_quarantined_total",
            1,
            {
                "pipeline": "chembl_activity",
                "error_type": ErrorType.INVALID_DATA.value,
                "run_type": "incremental",
            },
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_records_processed_total",
            1,
            {
                "pipeline": "chembl_activity",
                "stage": "quarantined",
                "run_type": "incremental",
            },
        )

    @pytest.mark.asyncio
    async def test_quarantine_record_emits_typed_quarantine_events(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Single-record quarantine should publish creation and quarantine events."""
        event_emitter = MagicMock()
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
            domain_event_emitter=event_emitter,
        )
        batch_id = deterministic_batch_uuid_from_callsite("test_quarantine_manager")
        run_id = deterministic_run_uuid_from_callsite("test_quarantine_manager")
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_record(
            record={"activity_id": "1"},
            error_type=ErrorType.INVALID_DATA,
            batch_id=batch_id,
            error_details="bad value",
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

        emitted_events = [
            call.args[0] for call in event_emitter.emit_domain_event.call_args_list
        ]
        assert any(
            isinstance(event, QuarantineEntryCreated) for event in emitted_events
        )
        assert any(isinstance(event, RecordQuarantined) for event in emitted_events)

    @pytest.mark.asyncio
    async def test_quarantine_record_prefers_activity_id_over_shared_record_id(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Activity quarantine events should expose the entity PK, not shared source ids."""
        event_emitter = MagicMock()
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
            domain_event_emitter=event_emitter,
        )
        batch_id = deterministic_batch_uuid_from_callsite("test_quarantine_manager")
        run_id = deterministic_run_uuid_from_callsite("test_quarantine_manager")
        ingestion_ts = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        await manager.quarantine_filtered_record(
            record={"activity_id": "CHEMBL-ACT-1", "record_id": "250193"},
            batch_id=batch_id,
            error_details="filtered",
            run_id=run_id,
            ingestion_ts=ingestion_ts,
        )

        record_event = next(
            call.args[0]
            for call in event_emitter.emit_domain_event.call_args_list
            if isinstance(call.args[0], RecordQuarantined)
        )
        assert record_event.record_id == "CHEMBL-ACT-1"

    @pytest.mark.asyncio
    async def test_quarantine_records_empty_list_is_noop(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Empty DQ record list should not call write_many."""
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        await manager.quarantine_records(
            [],
            deterministic_batch_uuid_from_callsite("test_quarantine_manager"),
            ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        quarantine_port.write_many.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_quarantine_filtered_records_empty_list_is_noop(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """Empty filtered record list should not call write_many."""
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="chembl_activity",
            metrics=metrics,
        )
        await manager.quarantine_filtered_records(
            [],
            deterministic_batch_uuid_from_callsite("test_quarantine_manager"),
            ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        quarantine_port.write_many.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_quarantine_record_without_metrics_does_not_fail(
        self,
        quarantine_port: MagicMock,
    ) -> None:
        """Single-record quarantine without metrics port should succeed."""
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="test",
            metrics=None,
        )
        await manager.quarantine_record(
            record={"id": "1"},
            error_type=ErrorType.INVALID_DATA,
            batch_id=deterministic_batch_uuid_from_callsite("test_quarantine_manager"),
            error_details="bad",
            ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        quarantine_port.write.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_namedtuple_entries_unpack_correctly_in_bulk_write(
        self,
        quarantine_port: MagicMock,
        metrics: MagicMock,
    ) -> None:
        """NamedTuple entries should unpack correctly in quarantine_records."""
        manager = QuarantineRuntimeService(
            quarantine_port=quarantine_port,
            pipeline_name="test",
            metrics=metrics,
        )
        entries = [
            DQQuarantineEntry(
                record={"id": "1"},
                error_type=ErrorType.INVALID_DATA,
                error_details="bad",
            ),
        ]
        await manager.quarantine_records(
            entries,
            deterministic_batch_uuid_from_callsite("test_quarantine_manager"),
            ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        quarantine_port.write_many.assert_awaited_once()
        request = quarantine_port.write_many.call_args[0][0][0]
        assert request["error_code"] == ErrorType.INVALID_DATA.value
        assert request["payload"] == {"id": "1"}
