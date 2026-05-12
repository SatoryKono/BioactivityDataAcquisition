"""Contract tests for grouped Prometheus metric registries."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.observability.metrics_definitions import __all__ as defs_all
from bioetl.infrastructure.observability.metrics_export_names import (
    METRICS_DEFINITION_EXPORT_NAMES,
)
from bioetl.infrastructure.observability.prometheus_metric_label_policies import (
    APPROVED_ENDPOINT_LABEL_METRICS,
    APPROVED_SOURCE_FILE_LABEL_METRICS,
    APPROVED_TABLE_LABEL_METRICS,
    FORBIDDEN_PROMETHEUS_LABEL_NAMES,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
    METRIC_REGISTRY_FAMILIES,
    METRIC_REGISTRY_INVENTORY,
    REGISTERED_PROMETHEUS_METRIC_NAMES,
)

_FORBIDDEN_LABELS = FORBIDDEN_PROMETHEUS_LABEL_NAMES


def _iter_registered_metric_labels() -> list[tuple[str, set[str]]]:
    return [
        (name, set(metric._labelnames))
        for registry in (COUNTERS, GAUGES, HISTOGRAMS)
        for name, metric in registry.items()
    ]


@pytest.mark.unit
def test_metric_registry_family_inventory_has_expected_families() -> None:
    assert tuple(METRIC_REGISTRY_INVENTORY) == (
        "pipeline_runtime",
        "storage_medallion",
        "http_adapters",
        "dq_validation",
        "system_process",
    )


@pytest.mark.unit
def test_metric_registry_family_keys_are_disjoint() -> None:
    seen: set[str] = set()
    duplicates: set[str] = set()

    for family in METRIC_REGISTRY_FAMILIES:
        family_names = (
            set(family.counters) | set(family.gauges) | set(family.histograms)
        )
        duplicates.update(seen & family_names)
        seen.update(family_names)

    assert not duplicates, (
        "Metric registry families must not overlap; duplicates found: "
        + ", ".join(sorted(duplicates))
    )


@pytest.mark.unit
def test_metric_registry_inventory_matches_public_registries() -> None:
    inventory_names = {
        name
        for family_inventory in METRIC_REGISTRY_INVENTORY.values()
        for registry_names in family_inventory.values()
        for name in registry_names
    }

    assert inventory_names == REGISTERED_PROMETHEUS_METRIC_NAMES
    assert inventory_names == set(COUNTERS) | set(GAUGES) | set(HISTOGRAMS)


@pytest.mark.unit
def test_high_cardinality_label_denylist_covers_forensic_identifiers() -> None:
    """Prometheus label policy must explicitly deny forensic/raw identifiers."""
    required_forbidden = {
        "run_id",
        "manifest_id",
        "lineage_fragment_id",
        "record_id",
        "content_hash",
        "payload_hash",
        "request_id",
        "message",
        "path",
        "file_path",
        "url",
        "raw_url",
        "query",
        "source_batch_id",
    }

    assert required_forbidden.issubset(FORBIDDEN_PROMETHEUS_LABEL_NAMES)


@pytest.mark.unit
def test_no_registered_metric_declares_forbidden_high_cardinality_labels() -> None:
    """Registry declarations must not introduce high-cardinality TSDB labels."""
    offenders = {
        name: sorted(labels & _FORBIDDEN_LABELS)
        for name, labels in _iter_registered_metric_labels()
        if labels & _FORBIDDEN_LABELS
    }

    assert offenders == {}


@pytest.mark.unit
def test_rawish_label_names_are_confined_to_normalized_metric_families() -> None:
    """Endpoint labels are allowed only behind central normalizers."""
    endpoint_metrics = {
        name
        for name, labels in _iter_registered_metric_labels()
        if "endpoint" in labels
    }
    source_file_metrics = {
        name
        for name, labels in _iter_registered_metric_labels()
        if "source_file" in labels
    }
    table_metrics = {
        name for name, labels in _iter_registered_metric_labels() if "table" in labels
    }

    assert endpoint_metrics == APPROVED_ENDPOINT_LABEL_METRICS
    assert source_file_metrics == APPROVED_SOURCE_FILE_LABEL_METRICS
    assert table_metrics == APPROVED_TABLE_LABEL_METRICS


@pytest.mark.unit
def test_metric_definition_exports_remain_stable() -> None:
    assert set(defs_all) == set(METRICS_DEFINITION_EXPORT_NAMES)


@pytest.mark.unit
def test_grouped_registry_inventory_preserves_expected_size() -> None:
    # This ratchet intentionally changes only when we add/remove public metrics.
    assert len(REGISTERED_PROMETHEUS_METRIC_NAMES) == 150


@pytest.mark.unit
def test_removed_dead_metric_families_are_no_longer_registered() -> None:
    assert "bioetl_archive_duration_seconds" not in REGISTERED_PROMETHEUS_METRIC_NAMES
    assert "bioetl_archive_files_total" not in REGISTERED_PROMETHEUS_METRIC_NAMES
    assert "bioetl_preflight_medallion_policy_valid" not in (
        REGISTERED_PROMETHEUS_METRIC_NAMES
    )
    assert "bioetl_preflight_config_errors_total" not in (
        REGISTERED_PROMETHEUS_METRIC_NAMES
    )
    assert "bioetl_vacuum_duration_seconds" not in REGISTERED_PROMETHEUS_METRIC_NAMES


@pytest.mark.unit
def test_bronze_runtime_write_metrics_are_registered() -> None:
    assert "bioetl_bronze_write_attempts_total" in COUNTERS
    assert "bioetl_bronze_write_total_duration_seconds" in HISTOGRAMS
    assert "bioetl_bronze_files_removed_total" in COUNTERS
    assert "bioetl_bronze_bytes_freed_total" in COUNTERS
    assert "bioetl_audit_write_events_total" in COUNTERS
    assert "bioetl_audit_query_events_total" in COUNTERS
    assert "bioetl_audit_write_duration_seconds" in HISTOGRAMS
    assert "bioetl_audit_query_duration_seconds" in HISTOGRAMS


@pytest.mark.unit
def test_gold_lifecycle_write_metrics_are_registered_with_bounded_labels() -> None:
    expected_counters = {
        "bioetl_gold_write_attempts_total": {"pipeline", "table", "mode"},
        "bioetl_gold_write_outcomes_total": {
            "pipeline",
            "table",
            "mode",
            "status",
        },
        "bioetl_gold_validation_failures_total": {
            "pipeline",
            "table",
            "mode",
            "error_type",
        },
        "bioetl_gold_lifecycle_state_total": {"pipeline", "table", "state"},
    }
    for metric_name, labels in expected_counters.items():
        actual_labels = set(COUNTERS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)

    duration_labels = set(HISTOGRAMS["bioetl_gold_write_duration_seconds"]._labelnames)
    assert duration_labels == {"pipeline", "table", "mode", "status"}
    assert _FORBIDDEN_LABELS.isdisjoint(duration_labels)


@pytest.mark.unit
def test_control_plane_and_lineage_metrics_are_registered() -> None:
    assert "bioetl_health_check_degraded_total" in COUNTERS
    assert "bioetl_control_plane_manifest_writes_total" in COUNTERS
    assert "bioetl_control_plane_ledger_appends_total" in COUNTERS
    assert "bioetl_control_plane_terminal_events_total" in COUNTERS
    assert "bioetl_control_plane_reads_total" in COUNTERS
    assert "bioetl_traced_runs_total" in COUNTERS
    assert "bioetl_checkpoint_compatibility_events_total" in COUNTERS
    assert "bioetl_checkpoint_load_events_total" in COUNTERS
    assert "bioetl_checkpoint_operator_operations_total" in COUNTERS
    assert "bioetl_structural_policy_events_total" in COUNTERS
    assert "bioetl_structural_policy_shadow_comparisons_total" in COUNTERS
    assert "bioetl_control_plane_read_duration_seconds" in HISTOGRAMS
    assert "bioetl_control_plane_manifest_write_duration_seconds" in HISTOGRAMS
    assert "bioetl_control_plane_ledger_append_duration_seconds" in HISTOGRAMS
    assert "bioetl_checkpoint_operator_duration_seconds" in HISTOGRAMS
    assert "bioetl_lineage_fragments_emitted_total" in COUNTERS
    assert "bioetl_lineage_refs_missing_total" in COUNTERS
    assert "bioetl_composite_source_selection_total" in COUNTERS
    assert "bioetl_http_retry_budget_exhausted_total" in COUNTERS


@pytest.mark.unit
def test_memory_runtime_metrics_are_registered_with_bounded_labels() -> None:
    expected_counter_labels = {
        "bioetl_memory_pressure_events_total": {
            "pipeline",
            "stage",
            "reason",
            "monitor_mode",
            "status",
        },
        "bioetl_memory_batch_resize_events_total": {
            "pipeline",
            "stage",
            "reason",
            "monitor_mode",
            "status",
        },
        "bioetl_memory_monitor_fallback_events_total": {
            "pipeline",
            "stage",
            "reason",
            "monitor_mode",
            "status",
        },
    }

    for metric_name, labels in expected_counter_labels.items():
        actual_labels = set(COUNTERS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)

    gauge_labels = set(GAUGES["bioetl_memory_pressure_state"]._labelnames)
    assert gauge_labels == {
        "pipeline",
        "stage",
        "reason",
        "monitor_mode",
        "status",
    }
    assert _FORBIDDEN_LABELS.isdisjoint(gauge_labels)


@pytest.mark.unit
def test_dq_and_circuit_breaker_diagnostic_metrics_use_bounded_labels() -> None:
    expected_counter_labels = {
        "bioetl_dq_check_failures_total": {
            "pipeline",
            "stage",
            "check_type",
            "severity",
        },
        "bioetl_dq_dispositions_total": {
            "pipeline",
            "stage",
            "disposition",
            "terminal_status",
        },
        "bioetl_circuit_breaker_open_total": {"adapter"},
    }

    for metric_name, labels in expected_counter_labels.items():
        actual_labels = set(COUNTERS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)


@pytest.mark.unit
def test_new_batch_artifact_and_composite_metrics_use_bounded_labels() -> None:
    expected_counter_labels = {
        "bioetl_batch_lifecycle_events_total": {
            "pipeline",
            "run_type",
            "event",
            "stage",
            "status",
        },
        "bioetl_batch_lifecycle_records_total": {
            "pipeline",
            "run_type",
            "event",
            "stage",
            "status",
        },
        "bioetl_output_artifact_publication_events_total": {
            "pipeline",
            "stage",
            "status",
        },
        "bioetl_composite_phase_records_total": {"pipeline", "phase", "outcome"},
        "bioetl_composite_phase_errors_total": {"pipeline", "phase", "error_kind"},
        "bioetl_composite_phase_loss_total": {"pipeline", "phase", "loss_kind"},
        "bioetl_composite_phase_retries_total": {"pipeline", "phase", "retry_kind"},
    }

    for metric_name, labels in expected_counter_labels.items():
        actual_labels = set(COUNTERS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)


@pytest.mark.unit
def test_control_plane_and_lineage_metrics_avoid_high_cardinality_labels() -> None:
    expected_labels = {
        "bioetl_control_plane_manifest_writes_total": {
            "pipeline",
            "run_type",
            "status",
        },
        "bioetl_control_plane_ledger_appends_total": {
            "pipeline",
            "event_type",
            "status",
        },
        "bioetl_control_plane_terminal_events_total": {
            "pipeline",
            "terminal_status",
        },
        "bioetl_checkpoint_compatibility_events_total": {
            "pipeline",
            "disposition",
        },
        "bioetl_checkpoint_load_events_total": {"pipeline", "status"},
        "bioetl_checkpoint_operator_operations_total": {"operation", "status"},
        "bioetl_lineage_fragments_emitted_total": {"pipeline", "layer", "status"},
        "bioetl_lineage_refs_missing_total": {"pipeline", "layer", "ref_type"},
        "bioetl_composite_source_selection_total": {
            "pipeline",
            "decision_type",
            "selected_source",
        },
    }

    for metric_name, labels in expected_labels.items():
        metric = COUNTERS[metric_name]
        actual_labels = set(metric._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels), (
            f"{metric_name} must not use forbidden high-cardinality labels: "
            f"{sorted(_FORBIDDEN_LABELS.intersection(actual_labels))}"
        )

    checkpoint_operator_histogram_labels = set(
        HISTOGRAMS["bioetl_checkpoint_operator_duration_seconds"]._labelnames
    )
    assert checkpoint_operator_histogram_labels == {"operation", "status"}
    assert _FORBIDDEN_LABELS.isdisjoint(checkpoint_operator_histogram_labels)
    manifest_write_histogram_labels = set(
        HISTOGRAMS["bioetl_control_plane_manifest_write_duration_seconds"]._labelnames
    )
    assert manifest_write_histogram_labels == {"pipeline", "run_type", "status"}
    assert _FORBIDDEN_LABELS.isdisjoint(manifest_write_histogram_labels)
    ledger_append_histogram_labels = set(
        HISTOGRAMS["bioetl_control_plane_ledger_append_duration_seconds"]._labelnames
    )
    assert ledger_append_histogram_labels == {"pipeline", "event_type", "status"}
    assert _FORBIDDEN_LABELS.isdisjoint(ledger_append_histogram_labels)


@pytest.mark.unit
def test_adapter_metrics_use_bounded_label_names_only() -> None:
    expected_counter_labels = {
        "bioetl_adapter_requests_total": {"provider", "endpoint", "status"},
        "bioetl_adapter_error_taxonomy_total": {
            "provider",
            "operation",
            "error_category",
            "error_type",
        },
        "bioetl_adapter_fallback_attempts_total": {"provider", "operation"},
        "bioetl_adapter_fallback_hits_total": {"provider", "operation"},
        "bioetl_filter_ids_loaded_total": {"pipeline", "source_kind"},
        "bioetl_filter_ids_duplicates_total": {"pipeline", "source_kind"},
        "bioetl_filter_combinations_loaded_total": {"pipeline", "source_kind"},
        "bioetl_record_flow_records_total": {"pipeline", "run_type", "flow_stage"},
        "bioetl_record_flow_invariants_total": {
            "pipeline",
            "run_type",
            "invariant",
            "status",
        },
        "bioetl_stage_records_total": {"pipeline", "run_type", "stage", "outcome"},
        "bioetl_metrics_publication_events_total": {
            "pipeline",
            "run_type",
            "target",
            "status",
        },
        "bioetl_replay_drift_events_total": {
            "pipeline",
            "run_type",
            "replay_capability",
            "drift_type",
            "status",
        },
    }
    expected_histogram_labels = {
        "bioetl_adapter_request_duration_seconds": {"provider", "endpoint"},
        "bioetl_adapter_batch_size": {"provider", "endpoint"},
        "bioetl_phase_duration_seconds": {"pipeline", "phase", "status"},
        "bioetl_postrun_phase_duration_seconds": {"pipeline", "phase", "status"},
    }
    expected_gauge_labels = {
        "bioetl_observability_runtime_status": {"pipeline", "component", "mode"},
        "bioetl_stage_backlog_records": {"pipeline", "run_type", "stage"},
        "bioetl_stage_lag_seconds": {"pipeline", "run_type", "stage"},
        "bioetl_replay_lag_seconds": {
            "pipeline",
            "run_type",
            "replay_capability",
            "status",
        },
    }
    expected_adapter_gauge_labels = {
        "bioetl_adapter_fallback_hit_rate": {"provider", "operation"},
    }

    for metric_name, labels in expected_counter_labels.items():
        actual_labels = set(COUNTERS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)

    for metric_name, labels in expected_histogram_labels.items():
        actual_labels = set(HISTOGRAMS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)

    for metric_name, labels in expected_gauge_labels.items():
        actual_labels = set(GAUGES[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)

    for metric_name, labels in expected_adapter_gauge_labels.items():
        actual_labels = set(GAUGES[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)


@pytest.mark.unit
def test_audit_metrics_use_bounded_labels() -> None:
    expected_counter_labels = {
        "bioetl_audit_write_events_total": {"layer", "operation", "status"},
        "bioetl_audit_query_events_total": {"layer_filter", "status"},
    }
    expected_histogram_labels = {
        "bioetl_audit_write_duration_seconds": {"layer", "operation", "status"},
        "bioetl_audit_query_duration_seconds": {"layer_filter", "status"},
    }

    for metric_name, labels in expected_counter_labels.items():
        actual_labels = set(COUNTERS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)

    for metric_name, labels in expected_histogram_labels.items():
        actual_labels = set(HISTOGRAMS[metric_name]._labelnames)
        assert actual_labels == labels
        assert _FORBIDDEN_LABELS.isdisjoint(actual_labels)
