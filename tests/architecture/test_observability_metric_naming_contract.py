# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guards for canonical observability metric naming."""

from __future__ import annotations

from pathlib import Path

import pytest

_SRC_ROOT = Path("src/bioetl")
_LEGACY_METRIC_NAMES = (
    "adapter_batch_size",
    "adapter_dropped_duplicates_total",
    "adapter_fallback_attempts_total",
    "adapter_fallback_hit_rate",
    "adapter_fallback_hits_total",
    "adapter_request_duration_seconds",
    "adapter_request_p95_seconds",
    "adapter_requests_total",
    "batch_size_records",
    "bronze_bytes_freed_total",
    "bronze_files_removed_total",
    "checkpoint_compatibility_events_total",
    "checkpoint_load_events_total",
    "circuit_breaker_failure_total",
    "circuit_breaker_state",
    "circuit_breaker_success_total",
    "circuit_breaker_trips_total",
    "composite_source_selection_total",
    "control_plane_ledger_appends_total",
    "control_plane_manifest_writes_total",
    "control_plane_read_duration_seconds",
    "control_plane_reads_total",
    "data_freshness_seconds",
    "data_source_retries_total",
    "data_source_retry_exhausted_total",
    "dq_anomaly_detected",
    "dq_baseline_updated",
    "dq_check_duration_ms",
    "dq_context_build_failures_total",
    "dq_monitor_disabled_total",
    "dq_monitor_enabled",
    "dq_records_quarantined_total",
    "dq_report_generated_total",
    "dq_report_skipped_total",
    "dq_soft_threshold_exceeded",
    "dq_validation_failures_total",
    "dq_validation_record_count",
    "dq_validation_score",
    "errors_total",
    "filter_combinations_loaded_total",
    "filter_ids_duplicates_total",
    "filter_ids_loaded_total",
    "health_check_degraded_total",
    "health_check_duration_seconds",
    "health_check_failures_total",
    "health_check_latency_seconds",
    "health_check_mode_latency_seconds",
    "health_check_mode_status",
    "health_check_status",
    "health_check_success_total",
    "http_retry_budget_exhausted_total",
    "http_request_duration_seconds",
    "http_request_errors_total",
    "http_retries_total",
    "infrastructure_validated",
    "lineage_fragments_emitted_total",
    "lineage_refs_missing_total",
    "observability_events_total",
    "pipeline_duration_seconds",
    "pipeline_health_check_passed",
    "preflight_config_errors_total",
    "preflight_medallion_policy_valid",
    "probe_mode_fallback_total",
    "provider_health_status",
    "quarantine_operator_duration_seconds",
    "quarantine_operator_operations_total",
    "quarantine_records_total",
    "records_processed_total",
    "silver_filter_rejections_total",
    "storage_optimization_total",
    "traced_runs_total",
    "transform_duration_seconds",
    "transform_errors_total",
    "vacuum_duration_seconds",
    "vacuum_files_removed_total",
)


def _iter_metric_dispatch_lines() -> list[tuple[Path, int, str]]:
    """Yield source lines that dispatch metrics from runtime modules."""
    metric_dispatch_tokens = (
        "increment_counter(",
        "observe_histogram(",
        "set_gauge(",
    )
    matches: list[tuple[Path, int, str]] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        if not path.is_file():
            continue
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if any(token in line for token in metric_dispatch_tokens):
                matches.append((path, lineno, line))
    return matches


def _collect_legacy_metric_violations() -> list[str]:
    """Collect runtime callsites still using legacy non-bioetl metric names."""
    violations: list[str] = []
    for path, lineno, line in _iter_metric_dispatch_lines():
        for metric_name in _LEGACY_METRIC_NAMES:
            if f'"{metric_name}"' in line or f"'{metric_name}'" in line:
                violations.append(f"{path}:{lineno}: {metric_name}")
    return violations


@pytest.mark.architecture
def test_runtime_metric_callsites_use_canonical_bioetl_prefix() -> None:
    """Runtime modules must emit observability metrics through canonical names."""
    violations = _collect_legacy_metric_violations()
    assert not violations, (
        "Runtime observability callsites must use canonical bioetl_* metric names.\n"
        + "\n".join(f"  - {violation}" for violation in violations[:80])
    )
