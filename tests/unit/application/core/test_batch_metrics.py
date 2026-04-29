"""Unit tests for BatchMetricsRecorderService (BatchMetricsRecorder).

Tests all metrics recording methods: track_batch_size, track_processed_records,
track_error, track_dq_validation_failure, track_quarantined_records, and
no-op behavior when metrics=None.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.application.core.batch_metrics import (
    BatchMetricsRecorder,
    BatchMetricsRecorderService,
)
from bioetl.domain.types import ErrorType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock MetricsPort."""
    metrics = MagicMock()
    metrics.observe_histogram = MagicMock()
    metrics.increment_counter = MagicMock()
    metrics.set_gauge = MagicMock()
    return metrics


@pytest.fixture
def recorder(mock_metrics: MagicMock) -> BatchMetricsRecorderService:
    """Create BatchMetricsRecorderService with a mock metrics port."""
    return BatchMetricsRecorderService(
        metrics=mock_metrics,
        pipeline_label="test_pipeline",
        run_type_label="incremental",
    )


@pytest.fixture
def recorder_no_metrics() -> BatchMetricsRecorderService:
    """Create BatchMetricsRecorderService with metrics=None."""
    return BatchMetricsRecorderService(
        metrics=None,
        pipeline_label="test_pipeline",
        run_type_label="incremental",
    )


# ---------------------------------------------------------------------------
# Tests: Initialization
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchMetricsRecorderServiceInit:
    """Tests for BatchMetricsRecorderService initialization."""

    def test_alias_batch_metrics_recorder_is_same_class(self) -> None:
        """Test that BatchMetricsRecorder is an alias for BatchMetricsRecorderService."""
        assert BatchMetricsRecorder is BatchMetricsRecorderService

    def test_stores_pipeline_label(self, mock_metrics: MagicMock) -> None:
        """Test that pipeline_label is stored."""
        recorder = BatchMetricsRecorderService(
            metrics=mock_metrics,
            pipeline_label="chembl_activity",
            run_type_label="rebuild",
        )
        assert recorder._pipeline_label == "chembl_activity"

    def test_stores_run_type_label(self, mock_metrics: MagicMock) -> None:
        """Test that run_type_label is stored."""
        recorder = BatchMetricsRecorderService(
            metrics=mock_metrics,
            pipeline_label="chembl_activity",
            run_type_label="rebuild",
        )
        assert recorder._run_type_label == "rebuild"

    def test_stores_metrics_port(self, mock_metrics: MagicMock) -> None:
        """Test that metrics port is stored."""
        recorder = BatchMetricsRecorderService(
            metrics=mock_metrics,
            pipeline_label="test",
            run_type_label="incremental",
        )
        assert recorder._metrics is mock_metrics

    def test_accepts_none_metrics(self) -> None:
        """Test that None metrics is accepted without error."""
        recorder = BatchMetricsRecorderService(
            metrics=None,
            pipeline_label="test",
            run_type_label="incremental",
        )
        assert recorder._metrics is None


# ---------------------------------------------------------------------------
# Tests: track_batch_size
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrackBatchSize:
    """Tests for track_batch_size method."""

    def test_calls_observe_histogram(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that observe_histogram is called with correct metric name."""
        recorder.track_batch_size(stage="bronze", size=100)

        mock_metrics.observe_histogram.assert_called_once_with(
            "bioetl_batch_size_records",
            100,
            {"pipeline": "test_pipeline", "stage": "bronze"},
        )

    def test_includes_pipeline_and_stage_labels(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that labels include pipeline and stage."""
        recorder.track_batch_size(stage="silver", size=50)

        call_args = mock_metrics.observe_histogram.call_args
        labels = call_args[0][2]
        assert labels["pipeline"] == "test_pipeline"
        assert labels["stage"] == "silver"

    def test_no_op_when_metrics_none(
        self, recorder_no_metrics: BatchMetricsRecorderService
    ) -> None:
        """Test that track_batch_size is a no-op when metrics is None."""
        # Must not raise
        recorder_no_metrics.track_batch_size(stage="bronze", size=100)

    def test_handles_zero_size(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that size=0 is accepted."""
        recorder.track_batch_size(stage="gold", size=0)
        mock_metrics.observe_histogram.assert_called_once()

    def test_different_stages(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test batch size tracking for multiple stages."""
        for stage in ("bronze", "silver", "gold"):
            recorder.track_batch_size(stage=stage, size=10)

        assert mock_metrics.observe_histogram.call_count == 3


# ---------------------------------------------------------------------------
# Tests: track_processed_records
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrackProcessedRecords:
    """Tests for track_processed_records method."""

    def test_calls_increment_counter(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that increment_counter is called with correct metric name."""
        recorder.track_processed_records(stage="bronze", count=200)

        mock_metrics.increment_counter.assert_any_call(
            "bioetl_records_processed_total",
            200,
            {
                "pipeline": "test_pipeline",
                "stage": "bronze",
                "run_type": "incremental",
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            200,
            {
                "pipeline": "test_pipeline",
                "run_type": "incremental",
                "flow_stage": "bronze",
            },
        )

    def test_includes_run_type_label(self, mock_metrics: MagicMock) -> None:
        """Test that run_type label is included in counter call."""
        recorder = BatchMetricsRecorderService(
            metrics=mock_metrics,
            pipeline_label="pubchem",
            run_type_label="rebuild",
        )
        recorder.track_processed_records(stage="silver", count=5)

        call_labels = mock_metrics.increment_counter.call_args[0][2]
        assert call_labels["run_type"] == "rebuild"

    def test_no_op_when_metrics_none(
        self, recorder_no_metrics: BatchMetricsRecorderService
    ) -> None:
        """Test that track_processed_records is no-op when metrics is None."""
        recorder_no_metrics.track_processed_records(stage="gold", count=50)

    def test_handles_quarantined_stage(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test tracking quarantined stage."""
        recorder.track_processed_records(stage="quarantined", count=3)

        legacy_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call.args and call.args[0] == "bioetl_records_processed_total"
        ]
        assert legacy_calls
        call_labels = legacy_calls[0].args[2]
        assert call_labels["stage"] == "quarantined"
        assert not any(
            call.args and call.args[0] == "bioetl_record_flow_records_total"
            for call in mock_metrics.increment_counter.call_args_list
        )

    def test_filtered_out_stage_projects_into_stage_model(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Filtered-out counts should project into transform-stage accounting."""
        recorder.track_processed_records(stage="filtered_out", count=3)

        mock_metrics.increment_counter.assert_any_call(
            "bioetl_stage_records_total",
            3,
            {
                "pipeline": "test_pipeline",
                "run_type": "incremental",
                "stage": "transform",
                "outcome": "filtered_out",
            },
        )

    def test_track_records_fetched_uses_record_flow_counter(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Fetched counts should be emitted through the canonical flow family."""
        recorder.track_records_fetched(12)

        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            12,
            {
                "pipeline": "test_pipeline",
                "run_type": "incremental",
                "flow_stage": "fetched",
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_stage_records_total",
            12,
            {
                "pipeline": "test_pipeline",
                "run_type": "incremental",
                "stage": "input",
                "outcome": "fetched",
            },
        )

    def test_track_stage_records_uses_stage_model_counter(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Explicit stage-model outcomes should use the canonical counter."""
        recorder.track_stage_records(
            stage="storage",
            outcome="silver_written",
            count=7,
        )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_stage_records_total",
            7,
            {
                "pipeline": "test_pipeline",
                "run_type": "incremental",
                "stage": "storage",
                "outcome": "silver_written",
            },
        )


# ---------------------------------------------------------------------------
# Tests: track_error
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrackError:
    """Tests for track_error method."""

    def test_calls_increment_counter_with_error_code(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that error tracking uses error_type.value as error_code label."""
        recorder.track_error(stage="transform", error_type=ErrorType.SCHEMA_VIOLATION)

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_errors_total",
            1,
            {
                "pipeline": "test_pipeline",
                "stage": "transform",
                "error_code": ErrorType.SCHEMA_VIOLATION.value,
            },
        )


@pytest.mark.unit
class TestTrackSilverFilterRejection:
    """Tests for bounded Silver reject breakdown tracking."""

    def test_tracks_structured_silver_filter_labels(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Structured semantic filter details should be forwarded as labels."""
        recorder.track_silver_filter_rejection(
            {
                "reason_code": "required_field_missing",
                "rule_type": "required_fields",
                "field": "publication_year",
                "message": "display only",
            }
        )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_silver_filter_rejections_total",
            1,
            {
                "pipeline": "test_pipeline",
                "run_type": "incremental",
                "reason_code": "required_field_missing",
                "rule_type": "required_fields",
                "field": "publication_year",
            },
        )

    def test_structural_rejects_use_structural_policy_rule_type(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Structural rejects should map missing rule_type to structural_policy."""
        recorder.track_silver_filter_rejection(
            {
                "reason_code": "optional_nonnullable_field_type_mismatch",
                "field": "title",
                "policy_stage": "structural",
            }
        )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_silver_filter_rejections_total",
            1,
            {
                "pipeline": "test_pipeline",
                "run_type": "incremental",
                "reason_code": "optional_nonnullable_field_type_mismatch",
                "rule_type": "structural_policy",
                "field": "title",
            },
        )

    def test_no_op_when_metrics_none(
        self, recorder_no_metrics: BatchMetricsRecorderService
    ) -> None:
        """Tracking should remain a no-op when metrics are disabled."""
        recorder_no_metrics.track_silver_filter_rejection(
            {"reason_code": "required_field_missing"}
        )

    def test_increments_by_one(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that error counter always increments by exactly 1."""
        recorder.track_error(stage="write", error_type=ErrorType.NETWORK_ERROR)

        increment_amount = mock_metrics.increment_counter.call_args[0][1]
        assert increment_amount == 1

    def test_track_error_no_op_when_metrics_none(
        self, recorder_no_metrics: BatchMetricsRecorderService
    ) -> None:
        """Test that track_error is no-op when metrics is None."""
        recorder_no_metrics.track_error(
            stage="transform", error_type=ErrorType.INVALID_DATA
        )

    def test_different_error_types(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test tracking multiple different error types."""
        error_types = [
            ErrorType.AUTH_FAILURE,
            ErrorType.RATE_LIMIT,
            ErrorType.TIMEOUT,
            ErrorType.SCHEMA_MISMATCH_GOLD,
        ]
        for error_type in error_types:
            recorder.track_error(stage="api", error_type=error_type)

        assert mock_metrics.increment_counter.call_count == 4


# ---------------------------------------------------------------------------
# Tests: track_dq_validation_failure
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrackDQValidationFailure:
    """Tests for track_dq_validation_failure method."""

    def test_records_dq_validation_failures_via_generic_counter(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that DQ failures use the generic counter contract."""
        recorder.track_dq_validation_failure(
            stage="silver", severity="soft_fail", count=5
        )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_dq_validation_failures_total",
            5,
            {
                "pipeline": "test_pipeline",
                "stage": "silver",
                "severity": "soft_fail",
            },
        )

    def test_default_count_is_one(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that default count=1 is used when not specified."""
        recorder.track_dq_validation_failure(stage="gold", severity="hard_fail")

        call_args = mock_metrics.increment_counter.call_args
        assert call_args.args[1] == 1

    def test_no_op_when_metrics_none(
        self, recorder_no_metrics: BatchMetricsRecorderService
    ) -> None:
        """Test that track_dq_validation_failure is no-op when metrics is None."""
        recorder_no_metrics.track_dq_validation_failure(
            stage="silver", severity="soft_fail"
        )

    def test_includes_pipeline_label(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that pipeline label is passed to metrics."""
        recorder.track_dq_validation_failure(stage="bronze", severity="soft_fail")

        call_labels = mock_metrics.increment_counter.call_args.args[2]
        assert call_labels["pipeline"] == "test_pipeline"


# ---------------------------------------------------------------------------
# Tests: track_quarantined_records
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTrackQuarantinedRecords:
    """Tests for track_quarantined_records method."""

    def test_calls_increment_counter(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that dq_records_quarantined_total counter is incremented."""
        recorder.track_quarantined_records(
            error_type=ErrorType.SCHEMA_VIOLATION, count=10
        )

        mock_metrics.increment_counter.assert_any_call(
            "bioetl_dq_records_quarantined_total",
            10,
            {
                "pipeline": "test_pipeline",
                "error_type": ErrorType.SCHEMA_VIOLATION.value,
                "run_type": "incremental",
            },
        )

    def test_records_quarantine_records_via_generic_counter(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that quarantine counters use the generic metric API."""
        recorder.track_quarantined_records(error_type=ErrorType.INVALID_DATA, count=3)

        mock_metrics.increment_counter.assert_any_call(
            "bioetl_quarantine_records_total",
            3,
            {
                "pipeline": "test_pipeline",
                "reason": ErrorType.INVALID_DATA.value,
            },
        )
        mock_metrics.increment_counter.assert_any_call(
            "bioetl_record_flow_records_total",
            3,
            {
                "pipeline": "test_pipeline",
                "run_type": "incremental",
                "flow_stage": "quarantined",
            },
        )

    def test_no_op_when_metrics_none(
        self, recorder_no_metrics: BatchMetricsRecorderService
    ) -> None:
        """Test that track_quarantined_records is no-op when metrics is None."""
        recorder_no_metrics.track_quarantined_records(
            error_type=ErrorType.MISSING_REQUIRED_FIELD, count=2
        )

    def test_uses_error_type_value_as_reason(
        self, recorder: BatchMetricsRecorderService, mock_metrics: MagicMock
    ) -> None:
        """Test that the error_type.value is used as reason label."""
        recorder.track_quarantined_records(error_type=ErrorType.DATA_QUALITY, count=1)

        quarantine_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call.args and call.args[0] == "bioetl_quarantine_records_total"
        ]
        assert quarantine_calls
        assert quarantine_calls[0].args[2]["reason"] == ErrorType.DATA_QUALITY.value

    def test_includes_run_type_label_in_counter(
        self,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that run_type label is included in the quarantine counter."""
        recorder = BatchMetricsRecorderService(
            metrics=mock_metrics,
            pipeline_label="pubchem",
            run_type_label="backfill",
        )
        recorder.track_quarantined_records(
            error_type=ErrorType.SCHEMA_VIOLATION, count=5
        )

        legacy_calls = [
            call
            for call in mock_metrics.increment_counter.call_args_list
            if call.args and call.args[0] == "bioetl_dq_records_quarantined_total"
        ]
        assert legacy_calls
        counter_labels = legacy_calls[0].args[2]
        assert counter_labels["run_type"] == "backfill"


# ---------------------------------------------------------------------------
# Tests: All methods are no-ops with None metrics
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNoOpWithNoneMetrics:
    """Parameterized tests confirming all methods are safe with metrics=None."""

    def test_all_track_methods_safe_with_none_metrics(self) -> None:
        """Test all public track_* methods do not raise when metrics=None."""
        recorder = BatchMetricsRecorderService(
            metrics=None,
            pipeline_label="safe_test",
            run_type_label="incremental",
        )
        # None of these should raise
        recorder.track_batch_size(stage="bronze", size=10)
        recorder.track_processed_records(stage="silver", count=5)
        recorder.track_error(stage="transform", error_type=ErrorType.TIMEOUT)
        recorder.track_dq_validation_failure(stage="gold", severity="soft_fail")
        recorder.track_quarantined_records(error_type=ErrorType.INVALID_DATA, count=1)
