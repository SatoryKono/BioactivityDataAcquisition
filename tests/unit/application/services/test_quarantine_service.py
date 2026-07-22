"""Unit tests for QuarantineService.

Tests the quarantine administrative service.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.quarantine_service import (
    QuarantineRecord,
    QuarantineService,
)
from bioetl.domain.control_plane.run_ledger import RUN_FINISHED_EVENT
from bioetl.domain.types import QuarantineRecordStatus
from tests.helpers.clock import FixedClock


def _make_mock_tracer() -> MagicMock:
    """Create a tracing port mock with an inspectable span context."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=None)
    mock_span.set_attribute = MagicMock()
    mock_span.record_exception = MagicMock()

    mock_otel_tracer = MagicMock()
    mock_otel_tracer.start_as_current_span = MagicMock(return_value=mock_span)

    mock_tracer = MagicMock()
    mock_tracer.get_tracer = MagicMock(return_value=mock_otel_tracer)
    mock_tracer.flush = MagicMock()
    return mock_tracer


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.debug = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.fixture
def mock_quarantine_port():
    """Create a mock quarantine port."""
    from unittest.mock import AsyncMock

    port = MagicMock()
    port.inspect = AsyncMock(return_value=[])
    port.get_stats = AsyncMock(return_value={})
    port.list_filtered_records = AsyncMock(return_value={"items": [], "total": 0})
    port.get_filtered_record = AsyncMock(return_value=None)
    port.get_filtered_stats = AsyncMock(return_value={"total": 0})
    port.get_filtered_timeseries = AsyncMock(return_value={"bucket": "1h", "rows": []})
    port.get_filtered_filter_options = AsyncMock(
        return_value={
            "pipelines": [],
            "run_types": [],
            "reason_codes": [],
            "fields": [],
            "run_ids": [],
        }
    )
    port.aclose = AsyncMock()
    # New synchronous methods
    port.replay = MagicMock(return_value=iter([]))
    port.purge = MagicMock(return_value=0)
    port.update_status = MagicMock(return_value=True)
    return port


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port."""
    metrics = MagicMock()
    metrics.increment_counter = MagicMock()
    metrics.observe_histogram = MagicMock()
    return metrics


@pytest.fixture
def mock_tracer():
    """Create a mock tracing port."""
    return _make_mock_tracer()


@pytest.fixture
def quarantine_service(mock_quarantine_port, mock_logger, mock_metrics, mock_tracer):
    """Create a QuarantineService instance."""
    return QuarantineService(
        quarantine_port=mock_quarantine_port,
        logger=mock_logger,
        clock=FixedClock(datetime(2026, 4, 24, 12, 0, tzinfo=UTC)),
        metrics=mock_metrics,
        tracer=mock_tracer,
    )


@pytest.mark.unit
class TestQuarantineRecord:
    """Test QuarantineRecord dataclass."""

    def test_quarantine_record_creation(self):
        """Test QuarantineRecord can be created."""
        now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        record = QuarantineRecord(
            error_code="DQ_MISSING_FIELD",
            payload={"id": 123},
            batch_id="batch-123",
            pipeline="test_pipeline",
            ingestion_ts=now,
            metadata={"error_details": "Missing required field"},
        )

        assert record.error_code == "DQ_MISSING_FIELD"
        assert record.payload == {"id": 123}
        assert record.batch_id == "batch-123"
        assert record.pipeline == "test_pipeline"
        assert record.ingestion_ts == now


@pytest.mark.unit
class TestQuarantineServiceInspect:
    """Test QuarantineService.inspect method."""

    @pytest.mark.asyncio
    async def test_inspect_empty(self, quarantine_service, mock_quarantine_port):
        """Test inspecting quarantine when empty."""
        mock_quarantine_port.inspect.return_value = []

        result = await quarantine_service.inspect("pipeline1", limit=10)

        assert result == []
        mock_quarantine_port.inspect.assert_called_once_with(
            pipeline="pipeline1",
            limit=10,
            error_code=None,
        )
        quarantine_service.metrics.increment_counter.assert_called_with(
            "bioetl_quarantine_operator_operations_total",
            1,
            labels={"operation": "inspect", "status": "success"},
        )
        quarantine_service.metrics.observe_histogram.assert_called_with(
            "bioetl_quarantine_operator_duration_seconds",
            pytest.approx(0.0, abs=1.0),
            labels={"operation": "inspect", "status": "success"},
        )

    @pytest.mark.asyncio
    async def test_inspect_with_records(self, quarantine_service, mock_quarantine_port):
        """Test inspecting quarantine with records."""
        now = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        mock_quarantine_port.inspect.return_value = [
            {
                "error_code": "DQ_MISSING_FIELD",
                "payload": {"id": 1},
                "bronze_batch_id": "batch-1",
                "ingestion_ts": now,
                "metadata": {},
            },
            {
                "error_code": "DQ_INVALID_SMILES",
                "payload": {"id": 2},
                "bronze_batch_id": "batch-2",
                "ingestion_ts": now,
                "metadata": {"error_details": "Invalid SMILES"},
            },
        ]

        result = await quarantine_service.inspect("pipeline1", limit=100)

        assert len(result) == 2
        assert result[0].error_code == "DQ_MISSING_FIELD"
        assert result[0].payload == {"id": 1}
        assert result[1].error_code == "DQ_INVALID_SMILES"

    @pytest.mark.asyncio
    async def test_inspect_with_error_code_filter(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test inspecting quarantine with error code filter."""
        mock_quarantine_port.inspect.return_value = []

        await quarantine_service.inspect(
            "pipeline1", limit=10, error_code="DQ_MISSING_FIELD"
        )

        mock_quarantine_port.inspect.assert_called_once_with(
            pipeline="pipeline1",
            limit=10,
            error_code="DQ_MISSING_FIELD",
        )

    @pytest.mark.asyncio
    async def test_inspect_creates_trace_span(self, quarantine_service, mock_tracer):
        """Inspect should create a bounded admin trace span."""
        await quarantine_service.inspect("pipeline1", limit=10)

        mock_tracer.get_tracer.assert_called_once_with("bioetl.quarantine_admin")
        args = mock_tracer.get_tracer.return_value.start_as_current_span.call_args
        assert args[0][0] == "quarantine.inspect"


@pytest.mark.unit
class TestQuarantineServiceGetStats:
    """Test QuarantineService.get_stats method."""

    @pytest.mark.asyncio
    async def test_get_stats(self, quarantine_service, mock_quarantine_port):
        """Test getting quarantine statistics."""
        mock_quarantine_port.get_stats.return_value = {
            "total_count": 100,
            "by_error_code": {
                "DQ_MISSING_FIELD": 60,
                "DQ_INVALID_SMILES": 40,
            },
        }

        result = await quarantine_service.get_stats("pipeline1")

        assert result["total_count"] == 100
        assert result["by_error_code"]["DQ_MISSING_FIELD"] == 60
        mock_quarantine_port.get_stats.assert_called_once_with("pipeline1", None)


@pytest.mark.unit
class TestQuarantineServiceFilteredExplorer:
    """Test record-level explorer APIs in QuarantineService."""

    @pytest.mark.asyncio
    async def test_list_filtered_records(
        self, quarantine_service, mock_quarantine_port
    ):
        """Service should delegate filtered list query to the port."""
        mock_quarantine_port.list_filtered_records.return_value = {
            "items": [{"payload_hash": "hash-1"}],
            "total": 1,
            "limit": 50,
            "offset": 0,
        }

        result = await quarantine_service.list_filtered_records(
            pipeline="pipeline1",
            run_type="incremental",
            reason_code="missing_required_field",
            field="canonical_smiles",
            run_id="run-1",
            payload_hash="hash-1",
            from_ts="2026-04-01T00:00:00Z",
            to_ts="2026-04-02T00:00:00Z",
            limit=25,
            offset=10,
            sort="ingestion_ts_desc",
        )

        assert result["total"] == 1
        mock_quarantine_port.list_filtered_records.assert_called_once_with(
            pipeline="pipeline1",
            run_type="incremental",
            reason_code="missing_required_field",
            field="canonical_smiles",
            run_id="run-1",
            payload_hash="hash-1",
            from_ts="2026-04-01T00:00:00Z",
            to_ts="2026-04-02T00:00:00Z",
            limit=25,
            offset=10,
            sort="ingestion_ts_desc",
        )

    @pytest.mark.asyncio
    async def test_get_filtered_record_not_found(
        self, quarantine_service, mock_quarantine_port
    ):
        """Detail lookup should return None when no record exists."""
        mock_quarantine_port.get_filtered_record.return_value = None

        result = await quarantine_service.get_filtered_record(
            payload_hash="missing",
            pipeline="pipeline1",
        )

        assert result is None
        mock_quarantine_port.get_filtered_record.assert_called_once_with(
            payload_hash="missing",
            pipeline="pipeline1",
        )
        quarantine_service.metrics.increment_counter.assert_called_with(
            "bioetl_quarantine_operator_operations_total",
            1,
            labels={"operation": "filtered_get", "status": "not_found"},
        )

    @pytest.mark.asyncio
    async def test_get_filtered_stats(self, quarantine_service, mock_quarantine_port):
        """Service should delegate filtered stats query to the port."""
        mock_quarantine_port.get_filtered_stats.return_value = {
            "total": 12,
            "reject_ratio": 0.1,
        }

        result = await quarantine_service.get_filtered_stats(
            pipeline="pipeline1",
            run_type="incremental",
            reason_code="missing_required_field",
            field="canonical_smiles",
            run_id="run-1",
            payload_hash=None,
            from_ts=None,
            to_ts=None,
        )

        assert result["total"] == 12
        mock_quarantine_port.get_filtered_stats.assert_called_once_with(
            pipeline="pipeline1",
            run_type="incremental",
            reason_code="missing_required_field",
            field="canonical_smiles",
            run_id="run-1",
            payload_hash=None,
            from_ts=None,
            to_ts=None,
        )

    @pytest.mark.asyncio
    async def test_get_filtered_stats_skips_manifest_fanout_for_scoped_rows(
        self, mock_quarantine_port, mock_logger, mock_metrics, mock_tracer
    ) -> None:
        """Scoped reject rows must not fan out across every run manifest."""
        mock_quarantine_port.get_filtered_stats.return_value = {
            "total": 12,
            "bronze_records": 0,
            "reject_ratio": 0.0,
            "run_ids": ["run-2", "run-1", "run-2"],
        }
        mock_run_manifest_service = MagicMock()
        mock_run_manifest_service.manifest_port.list_all.return_value = ()
        mock_run_manifest_service.ledger_port.list_entries_by_run_id.return_value = []
        service = QuarantineService(
            quarantine_port=mock_quarantine_port,
            logger=mock_logger,
            clock=FixedClock(datetime(2026, 4, 24, 12, 0, tzinfo=UTC)),
            metrics=mock_metrics,
            tracer=mock_tracer,
            run_manifest_service=mock_run_manifest_service,
        )

        result = await service.get_filtered_stats(pipeline="pipeline1")

        assert result["total"] == 12
        assert result["bronze_records"] == 0
        assert result["reject_ratio"] == 0.0
        assert "run_ids" not in result
        mock_run_manifest_service.show.assert_not_called()
        mock_run_manifest_service.manifest_port.list_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_filtered_stats_uses_explicit_run_id_for_empty_scope(
        self, mock_quarantine_port, mock_logger, mock_metrics, mock_tracer
    ) -> None:
        """Explicit run_id should still resolve Bronze denominator without reject rows."""
        mock_quarantine_port.get_filtered_stats.return_value = {
            "total": 0,
            "bronze_records": 0,
            "reject_ratio": 0.0,
            "run_ids": [],
        }
        mock_run_manifest_service = MagicMock()
        mock_run_manifest_service.show.return_value = MagicMock(
            ledger_entries=(MagicMock(metrics_snapshot={"records_bronze": 80}),)
        )
        service = QuarantineService(
            quarantine_port=mock_quarantine_port,
            logger=mock_logger,
            clock=FixedClock(datetime(2026, 4, 24, 12, 0, tzinfo=UTC)),
            metrics=mock_metrics,
            tracer=mock_tracer,
            run_manifest_service=mock_run_manifest_service,
        )

        result = await service.get_filtered_stats(
            pipeline="pipeline1",
            run_id="run-1",
        )

        assert result["bronze_records"] == 80
        assert result["reject_ratio"] == 0.0
        mock_run_manifest_service.show.assert_called_once_with("run-1")

    @pytest.mark.asyncio
    async def test_get_filtered_stats_resolves_latest_scope_run_for_zero_reject_scope(
        self, mock_quarantine_port, mock_logger, mock_metrics, mock_tracer
    ) -> None:
        """Zero-reject pipeline scope should keep the latest run Bronze denominator."""
        mock_quarantine_port.get_filtered_stats.return_value = {
            "total": 0,
            "bronze_records": 0,
            "reject_ratio": 0.0,
            "run_ids": [],
        }
        mock_run_manifest_service = MagicMock()
        older_manifest = SimpleNamespace(
            pipeline_name="pipeline1",
            run_type=SimpleNamespace(value="backfill"),
            created_at=datetime(2026, 4, 24, 10, 0, tzinfo=UTC),
            run_id="run-older",
        )
        latest_manifest = SimpleNamespace(
            pipeline_name="pipeline1",
            run_type=SimpleNamespace(value="backfill"),
            created_at=datetime(2026, 4, 24, 11, 0, tzinfo=UTC),
            run_id="run-latest",
        )
        mock_run_manifest_service.manifest_port.list_all.return_value = (
            older_manifest,
            latest_manifest,
        )
        mock_run_manifest_service.ledger_port.list_entries_by_run_id.side_effect = (
            lambda run_id: [
                SimpleNamespace(
                    event_type=RUN_FINISHED_EVENT,
                    occurred_at=(
                        datetime(2026, 4, 24, 10, 30, tzinfo=UTC)
                        if run_id == "run-older"
                        else datetime(2026, 4, 24, 11, 30, tzinfo=UTC)
                    ),
                    entry_id=f"{run_id}-entry",
                    metrics_snapshot={
                        "records_bronze": 80 if run_id == "run-older" else 120
                    },
                )
            ]
        )
        service = QuarantineService(
            quarantine_port=mock_quarantine_port,
            logger=mock_logger,
            clock=FixedClock(datetime(2026, 4, 24, 12, 0, tzinfo=UTC)),
            metrics=mock_metrics,
            tracer=mock_tracer,
            run_manifest_service=mock_run_manifest_service,
        )

        result = await service.get_filtered_stats(
            pipeline="pipeline1",
            run_type="backfill",
        )

        assert result["bronze_records"] == 120
        assert result["reject_ratio"] == 0.0
        mock_run_manifest_service.show.assert_not_called()
        mock_run_manifest_service.manifest_port.list_all.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_get_filtered_filter_options(
        self, quarantine_service, mock_quarantine_port
    ):
        """Service should return scoped filter options from the port."""
        mock_quarantine_port.get_filtered_filter_options.return_value = {
            "pipelines": ["pipeline1"],
            "run_types": ["incremental"],
            "reason_codes": ["missing_required_field"],
            "fields": ["canonical_smiles"],
            "run_ids": ["run-1"],
        }

        result = await quarantine_service.get_filtered_filter_options(
            pipeline="pipeline1",
            run_type=None,
            reason_code=None,
            field=None,
            run_id=None,
            from_ts="2026-04-01T00:00:00Z",
            to_ts="2026-04-02T00:00:00Z",
        )

        assert result["run_types"] == ["incremental"]
        mock_quarantine_port.get_filtered_filter_options.assert_called_once_with(
            pipeline="pipeline1",
            run_type=None,
            reason_code=None,
            field=None,
            run_id=None,
            from_ts="2026-04-01T00:00:00Z",
            to_ts="2026-04-02T00:00:00Z",
        )

    @pytest.mark.asyncio
    async def test_get_filtered_timeseries(
        self, quarantine_service, mock_quarantine_port
    ):
        """Service should delegate filtered-timeseries queries to the port."""
        mock_quarantine_port.get_filtered_timeseries.return_value = {
            "bucket": "1h",
            "rows": [
                {
                    "bucket_start": "2026-04-01T00:00:00+00:00",
                    "reject_count": 2,
                    "bronze_records": 10,
                    "reject_ratio": 0.2,
                }
            ],
        }

        result = await quarantine_service.get_filtered_timeseries(
            pipeline="pipeline1",
            run_type="incremental",
            reason_code="missing_required_field",
            field="canonical_smiles",
            run_id="run-1",
            from_ts="2026-04-01T00:00:00Z",
            to_ts="2026-04-02T00:00:00Z",
            bucket="1h",
        )

        assert result["bucket"] == "1h"
        assert result["rows"][0]["reject_count"] == 2
        mock_quarantine_port.get_filtered_timeseries.assert_called_once_with(
            pipeline="pipeline1",
            run_type="incremental",
            reason_code="missing_required_field",
            field="canonical_smiles",
            run_id="run-1",
            payload_hash=None,
            from_ts="2026-04-01T00:00:00Z",
            to_ts="2026-04-02T00:00:00Z",
            bucket="1h",
        )

    @pytest.mark.asyncio
    async def test_list_filtered_records_all_pipeline_scope(
        self, quarantine_service, mock_quarantine_port
    ):
        """Service should support all-pipeline record listing when pipeline omitted."""
        mock_quarantine_port.list_filtered_records.return_value = {
            "items": [],
            "total": 0,
            "limit": 50,
            "offset": 0,
        }

        result = await quarantine_service.list_filtered_records(
            pipeline=None,
            run_type=None,
            reason_code=None,
            field=None,
            run_id=None,
            payload_hash=None,
            from_ts=None,
            to_ts=None,
            limit=50,
            offset=0,
            sort="ingestion_ts_desc",
        )

        assert result["total"] == 0
        mock_quarantine_port.list_filtered_records.assert_called_once_with(
            pipeline=None,
            run_type=None,
            reason_code=None,
            field=None,
            run_id=None,
            payload_hash=None,
            from_ts=None,
            to_ts=None,
            limit=50,
            offset=0,
            sort="ingestion_ts_desc",
        )


@pytest.mark.unit
class TestQuarantineServiceReplay:
    """Test QuarantineService.replay method."""

    def test_replay_returns_records(self, quarantine_service, mock_quarantine_port):
        """Test replay returns records from port."""
        records = [
            {"payload_hash": "hash1", "error_code": "DQ_ERROR"},
            {"payload_hash": "hash2", "error_code": "DQ_ERROR"},
        ]
        mock_quarantine_port.replay.return_value = iter(records)

        result = quarantine_service.replay("pipeline1", max_age_days=7)

        assert len(result) == 2
        assert result[0]["payload_hash"] == "hash1"
        mock_quarantine_port.replay.assert_called_once()

    def test_replay_uses_sanctioned_timing_anchor(
        self, quarantine_service, mock_quarantine_port
    ) -> None:
        """Replay passes the captured timing anchor into the quarantine port."""
        started_at = datetime(2026, 4, 13, 9, 0, tzinfo=UTC)
        completed_at = datetime(2026, 4, 13, 9, 0, 2, tzinfo=UTC)
        quarantine_service._capture_operator_timing_anchor = MagicMock(
            return_value=(started_at, 10.0)
        )
        quarantine_service._derive_operator_completion = MagicMock(
            return_value=(completed_at, 2.0)
        )
        mock_quarantine_port.replay.return_value = iter([])

        quarantine_service.replay("pipeline1", max_age_days=7)

        assert mock_quarantine_port.replay.call_args.kwargs["now"] == started_at
        quarantine_service.logger.info.assert_any_call(
            "Replay records retrieved",
            pipeline="pipeline1",
            record_count=0,
            completed_at=completed_at.isoformat(),
            duration_seconds=2.0,
        )

    def test_replay_with_error_code_filter(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test replay with error code filter."""
        mock_quarantine_port.replay.return_value = iter([])

        quarantine_service.replay("pipeline1", error_code="DQ_NETWORK_ERROR")

        call_kwargs = mock_quarantine_port.replay.call_args[1]
        assert call_kwargs["error_code"] == "DQ_NETWORK_ERROR"

    def test_replay_records_failed_operator_metric_on_port_error(
        self, quarantine_service, mock_quarantine_port
    ) -> None:
        mock_quarantine_port.replay.side_effect = OSError("unavailable")
        quarantine_service._derive_operator_completion = MagicMock(
            return_value=(datetime(2026, 4, 13, tzinfo=UTC), 1.5)
        )

        with pytest.raises(OSError, match="unavailable"):
            quarantine_service.replay("pipeline1")

        quarantine_service.metrics.increment_counter.assert_any_call(
            "bioetl_quarantine_operator_operations_total",
            1,
            labels={"operation": "replay", "status": "failed"},
        )


@pytest.mark.unit
class TestQuarantineServiceMarkAsReprocessed:
    """Test QuarantineService.mark_as_reprocessed method."""

    def test_mark_as_reprocessed(self, quarantine_service, mock_quarantine_port):
        """Test marking records as reprocessed."""
        records = [
            {"payload_hash": "hash1"},
            {"payload_hash": "hash2"},
        ]

        count = quarantine_service.mark_as_reprocessed(records)

        assert count == 2
        assert mock_quarantine_port.update_status.call_count == 2

    def test_mark_as_reprocessed_skips_missing_hash(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test marking skips records without payload_hash."""
        records = [
            {"payload_hash": "hash1"},
            {"other_field": "value"},  # Missing payload_hash
        ]

        count = quarantine_service.mark_as_reprocessed(records)

        assert count == 1
        assert mock_quarantine_port.update_status.call_count == 1
        quarantine_service.metrics.increment_counter.assert_called_with(
            "bioetl_quarantine_operator_operations_total",
            1,
            labels={"operation": "mark_reprocessed", "status": "partial"},
        )


@pytest.mark.unit
class TestQuarantineServicePurge:
    """Test QuarantineService.purge method."""

    def test_purge_returns_count(self, quarantine_service, mock_quarantine_port):
        """Test purge returns count from port."""
        mock_quarantine_port.purge.return_value = 50

        result = quarantine_service.purge("pipeline1", older_than_days=30)

        assert result == 50
        mock_quarantine_port.purge.assert_called_once()

    def test_purge_with_custom_retention(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test purge with custom retention days."""
        quarantine_service.purge("pipeline1", older_than_days=60)

        call_kwargs = mock_quarantine_port.purge.call_args[1]
        assert call_kwargs["older_than_days"] == 60

    def test_purge_uses_sanctioned_timing_anchor(
        self, quarantine_service, mock_quarantine_port
    ) -> None:
        """Purge passes the captured timing anchor into the quarantine port."""
        started_at = datetime(2026, 4, 13, 10, 0, tzinfo=UTC)
        completed_at = datetime(2026, 4, 13, 10, 0, 5, tzinfo=UTC)
        quarantine_service._capture_operator_timing_anchor = MagicMock(
            return_value=(started_at, 20.0)
        )
        quarantine_service._derive_operator_completion = MagicMock(
            return_value=(completed_at, 5.0)
        )
        mock_quarantine_port.purge.return_value = 0

        quarantine_service.purge("pipeline1", older_than_days=30)

        assert mock_quarantine_port.purge.call_args.kwargs["now"] == started_at
        quarantine_service.logger.info.assert_any_call(
            "Purged quarantine records",
            pipeline="pipeline1",
            records_purged=0,
            completed_at=completed_at.isoformat(),
            duration_seconds=5.0,
        )

    def test_purge_records_failed_operator_metric_on_port_error(
        self, quarantine_service, mock_quarantine_port
    ) -> None:
        mock_quarantine_port.purge.side_effect = ValueError("invalid retention")
        quarantine_service._derive_operator_completion = MagicMock(
            return_value=(datetime(2026, 4, 13, tzinfo=UTC), 2.5)
        )

        with pytest.raises(ValueError, match="invalid retention"):
            quarantine_service.purge("pipeline1")

        quarantine_service.metrics.increment_counter.assert_any_call(
            "bioetl_quarantine_operator_operations_total",
            1,
            labels={"operation": "purge", "status": "failed"},
        )


@pytest.mark.unit
class TestQuarantineServiceUpdateStatus:
    """Test QuarantineService.update_status method."""

    def test_update_status_success(self, quarantine_service, mock_quarantine_port):
        """Test successful status update."""
        mock_quarantine_port.update_status.return_value = True

        result = quarantine_service.update_status(
            "hash123", QuarantineRecordStatus.IGNORED
        )

        assert result is True
        mock_quarantine_port.update_status.assert_called_once_with(
            "hash123", QuarantineRecordStatus.IGNORED
        )

    def test_update_status_not_found(self, quarantine_service, mock_quarantine_port):
        """Test status update when record not found."""
        mock_quarantine_port.update_status.return_value = False

        result = quarantine_service.update_status(
            "nonexistent", QuarantineRecordStatus.REPROCESSED
        )

        assert result is False
        quarantine_service.metrics.increment_counter.assert_called_with(
            "bioetl_quarantine_operator_operations_total",
            1,
            labels={"operation": "update_status", "status": "not_found"},
        )

    def test_update_status_logs_derived_completion_timestamp(
        self, quarantine_service, mock_quarantine_port
    ) -> None:
        """Status updates should log completion via the sanctioned timing anchor."""
        started_at = datetime(2026, 4, 13, 11, 0, tzinfo=UTC)
        completed_at = datetime(2026, 4, 13, 11, 0, 1, tzinfo=UTC)
        quarantine_service._capture_operator_timing_anchor = MagicMock(
            return_value=(started_at, 30.0)
        )
        quarantine_service._derive_operator_completion = MagicMock(
            return_value=(completed_at, 1.0)
        )
        mock_quarantine_port.update_status.return_value = True

        quarantine_service.update_status("hash123", QuarantineRecordStatus.IGNORED)

        quarantine_service.logger.info.assert_any_call(
            "Updated quarantine status",
            payload_hash="hash123",
            new_status=QuarantineRecordStatus.IGNORED.value,
            completed_at=completed_at.isoformat(),
            duration_seconds=1.0,
        )


@pytest.mark.unit
class TestQuarantineServiceAclose:
    """Test QuarantineService.aclose method."""

    @pytest.mark.asyncio
    async def test_service_aclose__aclose__1d857769(
        self, quarantine_service, mock_quarantine_port
    ):
        """Test closing the service."""
        await quarantine_service.aclose()

        mock_quarantine_port.aclose.assert_called_once()
