"""Unit tests for PrometheusMetrics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.observability.prometheus_metric_label_policies import (
    normalize_adapter_operation_label,
    normalize_dq_disposition,
    normalize_filter_source_kind_label,
    normalize_flow_stage,
    normalize_observability_mode,
    normalize_postrun_phase,
    normalize_publication_status,
    normalize_runtime_phase,
    normalize_runtime_stage,
    normalize_silver_filter_field,
    normalize_stage_model_outcome,
    normalize_stage_model_stage,
    normalize_terminal_status,
    normalize_publication_vocab_field,
    normalize_publication_vocab_handling,
    normalize_publication_vocab_provider,
)
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_source_file_label,
)
from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
    PrometheusMetrics,
)


@pytest.fixture
def prometheus_metrics():
    """Create a PrometheusMetrics instance."""
    return PrometheusMetrics()


@pytest.mark.unit
class TestPrometheusMetrics:
    """Tests for PrometheusMetrics."""

    def test_observe_histogram_valid_metric(self, prometheus_metrics):
        """Test observe_histogram with a valid metric name."""
        with patch.dict(
            HISTOGRAMS,
            {"bioetl_pipeline_duration_seconds": MagicMock()},
        ):
            prometheus_metrics.observe_histogram(
                name="bioetl_pipeline_duration_seconds",
                value=123.45,
                labels={
                    "pipeline": "test",
                    "stage": "pipeline",
                    "status": "success",
                    "run_type": "full",
                },
            )

            HISTOGRAMS[
                "bioetl_pipeline_duration_seconds"
            ].labels.assert_called_once_with(
                pipeline="test",
                stage="pipeline",
                status="success",
                run_type="full",
            )
            HISTOGRAMS[
                "bioetl_pipeline_duration_seconds"
            ].labels().observe.assert_called_once_with(123.45)

    def test_observe_histogram_unknown_metric(self, prometheus_metrics):
        """Unknown histogram names must fail loudly."""
        with pytest.raises(ValueError, match="Unknown Prometheus histogram metric"):
            prometheus_metrics.observe_histogram(
                name="unknown_metric",
                value=100.0,
                labels={"label": "value"},
            )

    def test_increment_counter_valid_metric(self, prometheus_metrics):
        """Test increment_counter with a valid metric name."""
        with patch.dict(
            COUNTERS,
            {"bioetl_records_processed_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_records_processed_total",
                value=100,
                labels={
                    "pipeline": "test",
                    "stage": "bronze",
                    "run_type": "incremental",
                },
            )

            COUNTERS["bioetl_records_processed_total"].labels.assert_called_once_with(
                pipeline="test",
                stage="bronze",
                run_type="incremental",
            )
            COUNTERS[
                "bioetl_records_processed_total"
            ].labels().inc.assert_called_once_with(100)

    def test_increment_counter_unknown_metric(self, prometheus_metrics):
        """Unknown counter names must fail loudly."""
        with pytest.raises(ValueError, match="Unknown Prometheus counter metric"):
            prometheus_metrics.increment_counter(
                name="unknown_counter",
                value=50,
                labels={"label": "value"},
            )

    def test_filter_source_metrics_normalize_source_kind_label(
        self, prometheus_metrics
    ):
        """Filter-source metrics must emit bounded source-kind labels."""
        with patch.dict(
            COUNTERS,
            {"bioetl_filter_ids_loaded_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_filter_ids_loaded_total",
                value=7,
                labels={
                    "pipeline": "chembl_activity",
                    "source_kind": "csv-single-column",
                },
            )

            COUNTERS["bioetl_filter_ids_loaded_total"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                source_kind="csv_single_column",
            )
            COUNTERS[
                "bioetl_filter_ids_loaded_total"
            ].labels().inc.assert_called_once_with(7)

    def test_filter_source_metrics_reject_source_file_label(self, prometheus_metrics):
        """Raw filter source paths must not be accepted as metric labels."""
        with patch.dict(
            COUNTERS,
            {"bioetl_filter_ids_loaded_total": MagicMock()},
        ):
            with pytest.raises(ValueError, match="source_file"):
                prometheus_metrics.increment_counter(
                    name="bioetl_filter_ids_loaded_total",
                    value=7,
                    labels={
                        "pipeline": "chembl_activity",
                        "source_file": r"filters\Activity IDs.csv",
                    },
                )

    def test_silver_maintenance_metrics_normalize_table_labels(
        self, prometheus_metrics
    ):
        """Table-scoped maintenance metrics must collapse table labels to canonical form."""
        with patch.dict(
            COUNTERS,
            {"bioetl_silver_csv_export_start_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_silver_csv_export_start_total",
                value=1,
                labels={
                    "table": "chembl.activity__v2_0_0",
                    "pipeline": "chembl_activity",
                },
            )

            COUNTERS[
                "bioetl_silver_csv_export_start_total"
            ].labels.assert_called_once_with(
                table="chembl_activity",
                pipeline="chembl_activity",
            )
            COUNTERS[
                "bioetl_silver_csv_export_start_total"
            ].labels().inc.assert_called_once_with(1)

    def test_table_label_rejected_for_unapproved_metric_families(
        self, prometheus_metrics
    ):
        """Raw table labels must be rejected outside reviewed table-scoped metrics."""
        with patch.dict(COUNTERS, {"bioetl_records_processed_total": MagicMock()}):
            with pytest.raises(ValueError, match="table"):
                prometheus_metrics.increment_counter(
                    name="bioetl_records_processed_total",
                    value=1,
                    labels={
                        "pipeline": "chembl_activity",
                        "stage": "bronze",
                        "run_type": "incremental",
                        "table": "chembl.activity",
                    },
                )

            COUNTERS["bioetl_records_processed_total"].labels.assert_not_called()

    def test_adapter_endpoint_metrics_normalize_dynamic_endpoint_labels(
        self, prometheus_metrics
    ):
        """Adapter endpoint families must re-normalize endpoint labels centrally."""
        with patch.dict(
            HISTOGRAMS,
            {"bioetl_adapter_request_duration_seconds": MagicMock()},
        ):
            prometheus_metrics.observe_histogram(
                name="bioetl_adapter_request_duration_seconds",
                value=0.25,
                labels={
                    "provider": "crossref",
                    "endpoint": "/works/123456789",
                },
            )

            HISTOGRAMS[
                "bioetl_adapter_request_duration_seconds"
            ].labels.assert_called_once_with(
                provider="crossref",
                endpoint="/works/{id}",
            )
            HISTOGRAMS[
                "bioetl_adapter_request_duration_seconds"
            ].labels().observe.assert_called_once_with(0.25)

    def test_forbidden_high_cardinality_labels_fail_before_dispatch(
        self, prometheus_metrics
    ):
        """Prometheus adapter must reject forensic labels before TSDB dispatch."""
        with patch.dict(COUNTERS, {"bioetl_records_processed_total": MagicMock()}):
            with pytest.raises(ValueError, match="run_id"):
                prometheus_metrics.increment_counter(
                    name="bioetl_records_processed_total",
                    value=1,
                    labels={
                        "pipeline": "chembl_activity",
                        "stage": "bronze",
                        "run_type": "incremental",
                        "run_id": "run-123",
                    },
                )

            COUNTERS["bioetl_records_processed_total"].labels.assert_not_called()

    def test_raw_endpoint_label_is_restricted_to_adapter_endpoint_metrics(
        self, prometheus_metrics
    ):
        """Endpoint labels are only valid on centrally-normalized adapter metrics."""
        with patch.dict(COUNTERS, {"bioetl_records_processed_total": MagicMock()}):
            with pytest.raises(ValueError, match="endpoint"):
                prometheus_metrics.increment_counter(
                    name="bioetl_records_processed_total",
                    value=1,
                    labels={
                        "pipeline": "chembl_activity",
                        "stage": "bronze",
                        "run_type": "incremental",
                        "endpoint": "/works/123",
                    },
                )

            COUNTERS["bioetl_records_processed_total"].labels.assert_not_called()

    def test_adapter_operation_metrics_normalize_unreviewed_operations(
        self, prometheus_metrics
    ):
        """Adapter operation labels must collapse unknown free-text to other."""
        with patch.dict(
            COUNTERS,
            {"bioetl_adapter_error_taxonomy_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_adapter_error_taxonomy_total",
                value=1,
                labels={
                    "provider": "chembl",
                    "operation": "custom_operation",
                    "error_category": "provider",
                    "error_type": "timeout",
                },
            )

            COUNTERS[
                "bioetl_adapter_error_taxonomy_total"
            ].labels.assert_called_once_with(
                provider="chembl",
                operation="other",
                error_category="provider",
                error_type="timeout",
            )
            COUNTERS[
                "bioetl_adapter_error_taxonomy_total"
            ].labels().inc.assert_called_once_with(1)

    def test_runtime_stage_metrics_normalize_unknown_stage_values(
        self, prometheus_metrics
    ):
        """Runtime stage labels must stay within the canonical bounded vocabulary."""
        with patch.dict(
            COUNTERS,
            {"bioetl_records_processed_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_records_processed_total",
                value=5,
                labels={
                    "pipeline": "chembl_activity",
                    "stage": "experimental_stage",
                    "run_type": "incremental",
                },
            )

            COUNTERS["bioetl_records_processed_total"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                stage="other",
                run_type="incremental",
            )
            COUNTERS[
                "bioetl_records_processed_total"
            ].labels().inc.assert_called_once_with(5)

    def test_runtime_phase_metrics_normalize_unknown_phase_values(
        self, prometheus_metrics
    ):
        """Phase metrics must reject arbitrary free-text phase labels."""
        with patch.dict(
            HISTOGRAMS,
            {"bioetl_phase_duration_seconds": MagicMock()},
        ):
            prometheus_metrics.observe_histogram(
                name="bioetl_phase_duration_seconds",
                value=1.5,
                labels={
                    "pipeline": "composite_target",
                    "phase": "totally_new_phase",
                    "status": "success",
                },
            )

            HISTOGRAMS["bioetl_phase_duration_seconds"].labels.assert_called_once_with(
                pipeline="composite_target",
                phase="other",
                status="success",
            )
            HISTOGRAMS[
                "bioetl_phase_duration_seconds"
            ].labels().observe.assert_called_once_with(1.5)

    def test_batch_lifecycle_metrics_normalize_unreviewed_labels(
        self, prometheus_metrics
    ):
        """Batch lifecycle labels must stay within bounded event/stage/status vocabularies."""
        with patch.dict(
            COUNTERS,
            {"bioetl_batch_lifecycle_events_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_batch_lifecycle_events_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "event": "custom_created_variant",
                    "stage": "experimental_stage",
                    "status": "unexpected_status",
                },
            )

            COUNTERS[
                "bioetl_batch_lifecycle_events_total"
            ].labels.assert_called_once_with(
                pipeline="chembl_activity",
                run_type="incremental",
                event="other",
                stage="other",
                status="other",
            )

    def test_composite_phase_metrics_normalize_unknown_labels(self, prometheus_metrics):
        """Composite phase counters must collapse unknown phase and outcome labels."""
        with patch.dict(
            COUNTERS,
            {"bioetl_composite_phase_records_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_composite_phase_records_total",
                value=4,
                labels={
                    "pipeline": "composite:target",
                    "phase": "wild_phase",
                    "outcome": "wild_outcome",
                },
            )

            COUNTERS[
                "bioetl_composite_phase_records_total"
            ].labels.assert_called_once_with(
                pipeline="composite:target",
                phase="other",
                outcome="other",
            )

    def test_postrun_phase_metrics_normalize_unknown_subphases(
        self, prometheus_metrics
    ):
        """Postrun phase metrics must use the dedicated bounded subphase vocabulary."""
        with patch.dict(
            COUNTERS,
            {"bioetl_postrun_phase_events_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_postrun_phase_events_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "phase": "custom_postrun",
                    "status": "success",
                },
            )

            COUNTERS[
                "bioetl_postrun_phase_events_total"
            ].labels.assert_called_once_with(
                pipeline="chembl_activity",
                phase="other",
                status="success",
            )
            COUNTERS[
                "bioetl_postrun_phase_events_total"
            ].labels().inc.assert_called_once_with(1)

    def test_record_flow_metrics_normalize_unknown_flow_stage_values(
        self, prometheus_metrics
    ):
        """Record-flow metrics must stay within the canonical bounded vocabulary."""
        with patch.dict(
            COUNTERS,
            {"bioetl_record_flow_records_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_record_flow_records_total",
                value=8,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "flow_stage": "experimental_projection",
                },
            )

            COUNTERS["bioetl_record_flow_records_total"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                run_type="incremental",
                flow_stage="other",
            )
            COUNTERS[
                "bioetl_record_flow_records_total"
            ].labels().inc.assert_called_once_with(8)

    def test_stage_model_metrics_normalize_unknown_labels(self, prometheus_metrics):
        """Stage-model families must enforce bounded stage/outcome vocabularies."""
        with patch.dict(
            COUNTERS,
            {"bioetl_stage_records_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_stage_records_total",
                value=6,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "stage": "wild_stage",
                    "outcome": "wild_outcome",
                },
            )

            COUNTERS["bioetl_stage_records_total"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                run_type="incremental",
                stage="other",
                outcome="other",
            )
            COUNTERS["bioetl_stage_records_total"].labels().inc.assert_called_once_with(
                6
            )

    def test_record_flow_invariant_metrics_normalize_unknown_labels(
        self, prometheus_metrics
    ):
        """Invariant metrics must stay within the canonical bounded vocabulary."""
        with patch.dict(
            COUNTERS,
            {"bioetl_record_flow_invariants_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_record_flow_invariants_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "invariant": "custom_invariant",
                    "status": "custom_status",
                },
            )

            COUNTERS[
                "bioetl_record_flow_invariants_total"
            ].labels.assert_called_once_with(
                pipeline="chembl_activity",
                run_type="incremental",
                invariant="other",
                status="other",
            )
            COUNTERS[
                "bioetl_record_flow_invariants_total"
            ].labels().inc.assert_called_once_with(1)

    def test_stage_backlog_gauge_normalizes_unknown_stage_labels(
        self, prometheus_metrics
    ):
        """Stage backlog gauge must stay within the canonical stage vocabulary."""
        with patch.dict(
            GAUGES,
            {"bioetl_stage_backlog_records": MagicMock()},
        ):
            prometheus_metrics.set_gauge(
                name="bioetl_stage_backlog_records",
                value=4.0,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "stage": "wild_stage",
                },
            )

            GAUGES["bioetl_stage_backlog_records"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                run_type="incremental",
                stage="other",
            )
            GAUGES["bioetl_stage_backlog_records"].labels().set.assert_called_once_with(
                4.0
            )

    def test_stage_lag_gauge_normalizes_unknown_stage_labels(self, prometheus_metrics):
        """Stage lag gauge must stay within the canonical stage vocabulary."""
        with patch.dict(
            GAUGES,
            {"bioetl_stage_lag_seconds": MagicMock()},
        ):
            prometheus_metrics.set_gauge(
                name="bioetl_stage_lag_seconds",
                value=12.5,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "stage": "wild_stage",
                },
            )

            GAUGES["bioetl_stage_lag_seconds"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                run_type="incremental",
                stage="other",
            )
            GAUGES["bioetl_stage_lag_seconds"].labels().set.assert_called_once_with(
                12.5
            )

    def test_dq_disposition_metrics_normalize_unknown_labels(self, prometheus_metrics):
        """DQ disposition labels must stay within the bounded canonical set."""
        with patch.dict(
            COUNTERS,
            {"bioetl_dq_dispositions_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_dq_dispositions_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "stage": "custom_stage",
                    "disposition": "custom_disposition",
                    "terminal_status": "custom_terminal",
                },
            )

            COUNTERS["bioetl_dq_dispositions_total"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                stage="other",
                disposition="other",
                terminal_status="other",
            )
            COUNTERS[
                "bioetl_dq_dispositions_total"
            ].labels().inc.assert_called_once_with(1)

    def test_metrics_publication_events_normalize_unknown_labels(
        self, prometheus_metrics
    ):
        """Publication self-monitoring counters must keep bounded target/status."""
        with patch.dict(
            COUNTERS,
            {"bioetl_metrics_publication_events_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_metrics_publication_events_total",
                value=1,
                labels={
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "target": "custom_sink",
                    "status": "custom_state",
                },
            )

            COUNTERS[
                "bioetl_metrics_publication_events_total"
            ].labels.assert_called_once_with(
                pipeline="chembl_activity",
                run_type="incremental",
                target="other",
                status="other",
            )
            COUNTERS[
                "bioetl_metrics_publication_events_total"
            ].labels().inc.assert_called_once_with(1)

    def test_publication_vocab_unknown_metrics_normalize_unknown_labels(
        self, prometheus_metrics
    ) -> None:
        """Publication vocabulary drift counters must keep bounded labels."""
        with patch.dict(
            COUNTERS,
            {"bioetl_publication_raw_vocab_unknown_total": MagicMock()},
        ):
            prometheus_metrics.increment_counter(
                name="bioetl_publication_raw_vocab_unknown_total",
                value=1,
                labels={
                    "pipeline": "pubmed_publication",
                    "provider": "custom_provider",
                    "field": "custom_field",
                    "handling": "custom_handling",
                },
            )

            COUNTERS[
                "bioetl_publication_raw_vocab_unknown_total"
            ].labels.assert_called_once_with(
                pipeline="pubmed_publication",
                provider="other",
                field="other",
                handling="other",
            )
            COUNTERS[
                "bioetl_publication_raw_vocab_unknown_total"
            ].labels().inc.assert_called_once_with(1)

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("filters/activity_ids.csv", "csv_file"),
            (r"filters\Activity IDs.csv", "csv_file"),
            ("configs/contracts/chembl/activity.yaml", "yaml_file"),
            ("filters/activity_ids", "extensionless_file"),
            ("filters/activity_ids.unknown", "other_file"),
            ("", "unknown"),
            ("////", "unknown"),
        ],
    )
    def test_normalize_source_file_label(self, raw_value: str, expected: str):
        """Source file labels should collapse to bounded source classes."""
        assert normalize_source_file_label(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("csv-single-column", "csv_single_column"),
            ("csv_multi_column", "csv_multi_column"),
            ("unknown/path.csv", "other"),
        ],
    )
    def test_normalize_filter_source_kind_label(
        self, raw_value: str, expected: str
    ) -> None:
        """Filter source kinds should stay within the bounded vocabulary."""
        assert normalize_filter_source_kind_label(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("fetch_filtered_with_fallback", "fetch_filtered_with_fallback"),
            ("custom_operation", "other"),
        ],
    )
    def test_normalize_adapter_operation_label(
        self, raw_value: str, expected: str
    ) -> None:
        """Adapter operation labels should stay within the reviewed vocabulary."""
        assert normalize_adapter_operation_label(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("bronze", "bronze"),
            ("experimental_stage", "other"),
        ],
    )
    def test_normalize_runtime_stage(self, raw_value: str, expected: str) -> None:
        """Runtime stage labels should collapse unknown values to other."""
        assert normalize_runtime_stage(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("bronze", "bronze"),
            ("custom_projection", "other"),
        ],
    )
    def test_normalize_flow_stage(self, raw_value: str, expected: str) -> None:
        """Record-flow stage labels should stay within the canonical set."""
        assert normalize_flow_stage(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("crossref", "crossref"),
            ("future-provider", "other"),
        ],
    )
    def test_normalize_publication_vocab_provider(
        self, raw_value: str, expected: str
    ) -> None:
        assert normalize_publication_vocab_provider(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("publication_types", "publication_types"),
            ("future_field", "other"),
        ],
    )
    def test_normalize_publication_vocab_field(
        self, raw_value: str, expected: str
    ) -> None:
        assert normalize_publication_vocab_field(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("preserved_unknown", "preserved_unknown"),
            ("future_handling", "other"),
        ],
    )
    def test_normalize_publication_vocab_handling(
        self, raw_value: str, expected: str
    ) -> None:
        assert normalize_publication_vocab_handling(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("validation", "validation"),
            ("custom_stage", "other"),
        ],
    )
    def test_normalize_stage_model_stage(self, raw_value: str, expected: str) -> None:
        assert normalize_stage_model_stage(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("silver_written", "silver_written"),
            ("custom_outcome", "other"),
        ],
    )
    def test_normalize_stage_model_outcome(self, raw_value: str, expected: str) -> None:
        assert normalize_stage_model_outcome(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("warn", "warn"),
            ("custom", "other"),
        ],
    )
    def test_normalize_dq_disposition(self, raw_value: str, expected: str) -> None:
        assert normalize_dq_disposition(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("success", "success"),
            ("custom", "other"),
        ],
    )
    def test_normalize_terminal_status(self, raw_value: str, expected: str) -> None:
        assert normalize_terminal_status(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("failed", "failed"),
            ("custom", "other"),
        ],
    )
    def test_normalize_publication_status(self, raw_value: str, expected: str) -> None:
        assert normalize_publication_status(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("active", "active"),
            ("custom", "other"),
        ],
    )
    def test_normalize_observability_mode(self, raw_value: str, expected: str) -> None:
        assert normalize_observability_mode(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("seed", "seed"),
            ("unexpected_phase", "other"),
        ],
    )
    def test_normalize_runtime_phase(self, raw_value: str, expected: str) -> None:
        """Composite/lifecycle phase labels should stay bounded."""
        assert normalize_runtime_phase(raw_value) == expected

    @pytest.mark.parametrize(
        ("raw_value", "expected"),
        [
            ("dq_evaluation", "dq_evaluation"),
            ("postrun_extra", "other"),
        ],
    )
    def test_normalize_postrun_phase(self, raw_value: str, expected: str) -> None:
        """Postrun subphase labels should use the dedicated bounded vocabulary."""
        assert normalize_postrun_phase(raw_value) == expected


@pytest.mark.unit
class TestPrometheusMetricsRegistries:
    """Tests for metric registries."""

    def test_histograms_registry_has_pipeline_duration(self):
        """Test HISTOGRAMS registry contains bioetl_pipeline_duration_seconds."""
        assert "bioetl_pipeline_duration_seconds" in HISTOGRAMS

    def test_counters_registry_has_records_processed(self):
        """Test COUNTERS registry contains bioetl_records_processed_total."""
        assert "bioetl_records_processed_total" in COUNTERS


@pytest.mark.unit
class TestPrometheusMetricsGauge:
    """Tests for gauge metrics."""

    def test_set_gauge_valid_metric(self, prometheus_metrics):
        """Test set_gauge with a valid metric name."""
        with patch.dict(
            GAUGES,
            {"bioetl_circuit_breaker_state": MagicMock()},
        ):
            prometheus_metrics.set_gauge(
                name="bioetl_circuit_breaker_state",
                value=1.0,
                labels={"adapter": "chembl"},
            )

            GAUGES["bioetl_circuit_breaker_state"].labels.assert_called_once_with(
                adapter="chembl"
            )
            GAUGES["bioetl_circuit_breaker_state"].labels().set.assert_called_once_with(
                1.0
            )

    def test_set_gauge_unknown_metric(self, prometheus_metrics):
        """Unknown gauge names must fail loudly."""
        with pytest.raises(ValueError, match="Unknown Prometheus gauge metric"):
            prometheus_metrics.set_gauge(
                name="unknown_gauge",
                value=42.0,
                labels={"label": "value"},
            )


@pytest.mark.unit
class TestRequiredMetricsSmoke:
    """Smoke tests for required metrics per observability contract.

    REQ-OBS-CONTRACT-001: All metrics defined in docs/contracts/observability.md
    MUST be registered and exportable.
    """

    def test_required_pipeline_metrics_registered(self):
        """Verify all MUST pipeline metrics are in registries."""
        # MUST metrics from docs/contracts/observability.md
        required_histograms = [
            "bioetl_pipeline_duration_seconds",
            "bioetl_batch_size_records",
        ]
        required_counters = [
            "bioetl_records_processed_total",
            "bioetl_errors_total",
            "bioetl_dq_records_quarantined_total",
        ]

        for metric in required_histograms:
            assert metric in HISTOGRAMS, (
                f"Required histogram '{metric}' not found in HISTOGRAMS registry"
            )

        for metric in required_counters:
            assert metric in COUNTERS, (
                f"Required counter '{metric}' not found in COUNTERS registry"
            )

    def test_required_circuit_breaker_metrics_registered(self):
        """Verify Circuit Breaker metrics are registered (per ADR-007)."""
        # MUST metrics per ADR-007
        cb_counters = [
            "bioetl_circuit_breaker_trips_total",
            "bioetl_circuit_breaker_success_total",
            "bioetl_circuit_breaker_failure_total",
            "bioetl_circuit_breaker_open_total",
        ]
        cb_gauges = [
            "bioetl_circuit_breaker_state",
        ]

        for metric in cb_counters:
            assert metric in COUNTERS, (
                f"Required CB counter '{metric}' not found in COUNTERS registry"
            )

        for metric in cb_gauges:
            assert metric in GAUGES, (
                f"Required CB gauge '{metric}' not found in GAUGES registry"
            )

    def test_required_adapter_operational_metrics_registered(self):
        """Verify canonical adapter fallback/error taxonomy metrics are registered."""
        required_counters = [
            "bioetl_adapter_fallback_attempts_total",
            "bioetl_adapter_fallback_hits_total",
            "bioetl_adapter_error_taxonomy_total",
        ]
        required_gauges = [
            "bioetl_adapter_fallback_hit_rate",
        ]

        for metric in required_counters:
            assert metric in COUNTERS, (
                f"Required adapter counter '{metric}' not found in COUNTERS registry"
            )

        for metric in required_gauges:
            assert metric in GAUGES, (
                f"Required adapter gauge '{metric}' not found in GAUGES registry"
            )

    def test_metrics_have_correct_labels(self):
        """Verify metrics have expected label names."""
        from bioetl.infrastructure.observability.metrics import (
            CIRCUIT_BREAKER_STATE,
            OBSERVABILITY_EVENTS_TOTAL,
            PIPELINE_DURATION_SECONDS,
            POSTRUN_PHASE_DURATION_SECONDS,
            POSTRUN_PHASE_EVENTS_TOTAL,
        )

        # Pipeline duration should have these labels
        pipeline_labels = PIPELINE_DURATION_SECONDS._labelnames
        assert "pipeline" in pipeline_labels
        assert "stage" in pipeline_labels
        assert "status" in pipeline_labels
        assert "run_type" in pipeline_labels

        # Circuit breaker state should have adapter label
        cb_labels = CIRCUIT_BREAKER_STATE._labelnames
        assert "adapter" in cb_labels

        # Unified observer events should expose standardized labels
        event_labels = OBSERVABILITY_EVENTS_TOTAL._labelnames
        assert "event" in event_labels
        assert "provider" in event_labels
        assert "pipeline" in event_labels
        assert "severity" in event_labels
        assert "error_type" in event_labels

        postrun_counter_labels = POSTRUN_PHASE_EVENTS_TOTAL._labelnames
        assert postrun_counter_labels == ("pipeline", "phase", "status")

        postrun_histogram_labels = POSTRUN_PHASE_DURATION_SECONDS._labelnames
        assert postrun_histogram_labels == ("pipeline", "phase", "status")


@pytest.mark.unit
class TestPrometheusMetricsClose:
    """Tests for close() method."""

    def test_close_is_idempotent(self, prometheus_metrics):
        """Test that close() can be called multiple times safely."""
        prometheus_metrics.close()
        prometheus_metrics.close()  # Should not raise

        assert prometheus_metrics._closed is True


@pytest.mark.unit
class TestPrometheusCounterLabelNormalization:
    """Tests for bounded-label normalization via generic dispatch."""

    def test_quarantine_records_total_normalizes_reason(self, prometheus_metrics):
        with patch.dict(COUNTERS, {"bioetl_quarantine_records_total": MagicMock()}):
            prometheus_metrics.increment_counter(
                "bioetl_quarantine_records_total",
                2,
                {"pipeline": "chembl_activity", "reason": "Unbounded Random Reason"},
            )

            COUNTERS["bioetl_quarantine_records_total"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                reason="other",
            )
            COUNTERS[
                "bioetl_quarantine_records_total"
            ].labels().inc.assert_called_once_with(2)

    def test_dq_validation_failures_total_normalizes_labels(self, prometheus_metrics):
        with patch.dict(COUNTERS, {"bioetl_dq_validation_failures_total": MagicMock()}):
            prometheus_metrics.increment_counter(
                "bioetl_dq_validation_failures_total",
                1,
                {
                    "pipeline": "chembl_activity",
                    "stage": "Threshold",
                    "severity": "SOFT-FAIL",
                },
            )

            COUNTERS[
                "bioetl_dq_validation_failures_total"
            ].labels.assert_called_once_with(
                pipeline="chembl_activity",
                stage="threshold",
                severity="soft_fail",
            )
            COUNTERS[
                "bioetl_dq_validation_failures_total"
            ].labels().inc.assert_called_once_with(1)

    def test_dq_check_failures_total_normalizes_labels(self, prometheus_metrics):
        with patch.dict(COUNTERS, {"bioetl_dq_check_failures_total": MagicMock()}):
            prometheus_metrics.increment_counter(
                "bioetl_dq_check_failures_total",
                1,
                {
                    "pipeline": "chembl_activity",
                    "stage": "Bronze",
                    "check_type": "Encoding Validation",
                    "severity": "HARD-FAIL",
                },
            )

            COUNTERS["bioetl_dq_check_failures_total"].labels.assert_called_once_with(
                pipeline="chembl_activity",
                stage="bronze",
                check_type="encoding_validation",
                severity="hard_fail",
            )
            COUNTERS[
                "bioetl_dq_check_failures_total"
            ].labels().inc.assert_called_once_with(1)

    def test_silver_filter_rejections_total_normalizes_labels(self, prometheus_metrics):
        with patch.dict(
            COUNTERS, {"bioetl_silver_filter_rejections_total": MagicMock()}
        ):
            prometheus_metrics.increment_counter(
                "bioetl_silver_filter_rejections_total",
                3,
                {
                    "pipeline": "chembl_activity",
                    "run_type": "incremental",
                    "reason_code": "Unbounded Random Reason",
                    "rule_type": "structural-policy",
                    "field": "totally_unknown_field",
                },
            )

            COUNTERS[
                "bioetl_silver_filter_rejections_total"
            ].labels.assert_called_once_with(
                pipeline="chembl_activity",
                run_type="incremental",
                reason_code="other",
                rule_type="structural_policy",
                field="other",
            )
            COUNTERS[
                "bioetl_silver_filter_rejections_total"
            ].labels().inc.assert_called_once_with(3)

    @pytest.mark.parametrize(
        ("raw_field", "expected"),
        [
            ("publication_id", "publication_id"),
            ("totally_unknown_field", "other"),
            ("metadata.source.url", "other"),
            ("/tmp/provider/path.csv", "other"),
            ("sha256:deadbeef", "other"),
            ("", "other"),
            (None, "other"),
        ],
    )
    def test_silver_filter_field_normalizer_is_bounded(
        self, raw_field: str | None, expected: str
    ) -> None:
        """Silver reject field labels must collapse free text to the bounded set."""
        assert normalize_silver_filter_field(raw_field) == expected


@pytest.mark.unit
class TestObservabilityMetricContract:
    """Tests for observability_events_total label schema normalization."""

    def test_observability_counter_ignores_legacy_labels(self, prometheus_metrics):
        with patch.dict(COUNTERS, {"bioetl_observability_events_total": MagicMock()}):
            prometheus_metrics.increment_counter(
                name="bioetl_observability_events_total",
                value=1,
                labels={
                    "event_name": "pipeline_started",
                    "provider_name": "chembl",
                    "pipeline_name": "chembl_activity",
                    "log_level": "INFO",
                },
            )

            COUNTERS[
                "bioetl_observability_events_total"
            ].labels.assert_called_once_with(
                event="unknown_event",
                provider="unknown",
                pipeline="unknown",
                severity="info",
                error_type="none",
            )

    def test_observability_counter_normalizes_path_like_pipeline_labels(
        self, prometheus_metrics
    ) -> None:
        with patch.dict(COUNTERS, {"bioetl_observability_events_total": MagicMock()}):
            prometheus_metrics.increment_counter(
                name="bioetl_observability_events_total",
                value=1,
                labels={
                    "event": "silver_merge_retry",
                    "provider": "storage",
                    "pipeline": "test-output/bioetl/silver/chembl_activity__v1_2_3",
                    "severity": "warning",
                    "error_type": "commit_conflict",
                },
            )

            COUNTERS[
                "bioetl_observability_events_total"
            ].labels.assert_called_once_with(
                event="silver_merge_retry",
                provider="storage",
                pipeline="chembl_activity",
                severity="warning",
                error_type="commit_conflict",
            )


@pytest.mark.unit
class TestMetricLabelContract:
    """Metrics adapters accept only canonical labels payloads."""

    def test_observability_counter_always_has_required_labels(self, prometheus_metrics):
        with patch.dict(COUNTERS, {"bioetl_observability_events_total": MagicMock()}):
            prometheus_metrics.increment_counter(
                name="bioetl_observability_events_total",
                value=1,
                labels={},
            )

            COUNTERS[
                "bioetl_observability_events_total"
            ].labels.assert_called_once_with(
                event="unknown_event",
                provider="unknown",
                pipeline="unknown",
                severity="info",
                error_type="none",
            )

    def test_observe_histogram_rejects_legacy__labels(self, prometheus_metrics):
        with pytest.raises(TypeError):
            prometheus_metrics.observe_histogram(
                name="bioetl_pipeline_duration_seconds",
                value=1.0,
                _labels={"pipeline": "test", "stage": "x", "status": "ok"},
            )

    def test_set_gauge_rejects_legacy_tags(self, prometheus_metrics):
        with pytest.raises(TypeError):
            prometheus_metrics.set_gauge(
                name="bioetl_circuit_breaker_state",
                value=1.0,
                tags={"adapter": "chembl"},
            )


@pytest.mark.unit
class TestLegacyMetricNameRetirement:
    """Legacy metric identifiers must fail instead of being canonicalized silently."""

    def test_legacy_histogram_name_fails_loudly(self, prometheus_metrics):
        with pytest.raises(ValueError, match="Unknown Prometheus histogram metric"):
            prometheus_metrics.observe_histogram(
                name="pipeline_duration_seconds",
                value=1.0,
                labels={"pipeline": "x"},
            )

    def test_legacy_counter_name_fails_loudly(self, prometheus_metrics):
        with pytest.raises(ValueError, match="Unknown Prometheus counter metric"):
            prometheus_metrics.increment_counter(
                name="records_processed_total",
                value=1,
                labels={"pipeline": "x"},
            )

    def test_legacy_gauge_name_fails_loudly(self, prometheus_metrics):
        with pytest.raises(ValueError, match="Unknown Prometheus gauge metric"):
            prometheus_metrics.set_gauge(
                name="circuit_breaker_state",
                value=1.0,
                labels={"adapter": "chembl"},
            )


@pytest.mark.unit
class TestMetricCardinalityGuards:
    """Guards against accidental high-cardinality metric labels (Wave 4 / Track E)."""

    def test_observability_events_total_label_contract_is_stable(self) -> None:
        from bioetl.infrastructure.observability.metrics import (
            OBSERVABILITY_EVENTS_TOTAL,
        )

        assert OBSERVABILITY_EVENTS_TOTAL._labelnames == (
            "event",
            "provider",
            "pipeline",
            "severity",
            "error_type",
        )

    def test_registered_metrics_do_not_use_run_level_correlation_labels(self) -> None:
        from bioetl.infrastructure.observability.metrics import (
            __all__ as metric_symbols,
        )

        from bioetl.infrastructure.observability import metrics as metrics_module

        forbidden = frozenset(
            {
                "run_id",
                "manifest_id",
                "dataset_ref",
                "lineage_fragment_id",
                "composite_run_id",
                "effective_config_hash",
                "contract_ref",
                "contract_version",
            }
        )
        violations: list[str] = []
        for symbol in metric_symbols:
            metric_obj = getattr(metrics_module, symbol, None)
            label_names = getattr(metric_obj, "_labelnames", None)
            if not isinstance(label_names, tuple):
                continue
            overlaps = sorted(forbidden.intersection(label_names))
            if not overlaps:
                continue
            if overlaps:
                violations.append(
                    f"{symbol}: forbidden labels present -> {', '.join(overlaps)}"
                )

        assert not violations, (
            "Metrics must keep high-cardinality correlation anchors out of labels:\n"
            + "\n".join(f"  - {line}" for line in violations)
        )
