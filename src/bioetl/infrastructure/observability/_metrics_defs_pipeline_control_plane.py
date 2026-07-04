"""Control-plane persistence Prometheus metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

__all__ = [
    "CONTROL_PLANE_LEDGER_APPENDS_TOTAL",
    "CONTROL_PLANE_LEDGER_APPEND_DURATION_SECONDS",
    "CONTROL_PLANE_LIFECYCLE_APPLY_TOTAL",
    "CONTROL_PLANE_LIFECYCLE_DELETED_TOTAL",
    "CONTROL_PLANE_LIFECYCLE_DELETE_CANDIDATES",
    "CONTROL_PLANE_MANIFEST_WRITES_TOTAL",
    "CONTROL_PLANE_MANIFEST_WRITE_DURATION_SECONDS",
    "CONTROL_PLANE_READS_TOTAL",
    "CONTROL_PLANE_READ_DURATION_SECONDS",
    "CONTROL_PLANE_TERMINAL_EVENTS_TOTAL",
]

CONTROL_PLANE_MANIFEST_WRITES_TOTAL = Counter(
    "bioetl_control_plane_manifest_writes_total",
    "Total immutable run-manifest persistence attempts",
    ["pipeline", "run_type", "status"],
)

CONTROL_PLANE_MANIFEST_WRITE_DURATION_SECONDS = Histogram(
    "bioetl_control_plane_manifest_write_duration_seconds",
    "Latency of immutable run-manifest persistence in seconds",
    ["pipeline", "run_type", "status"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

CONTROL_PLANE_LEDGER_APPENDS_TOTAL = Counter(
    "bioetl_control_plane_ledger_appends_total",
    "Total append attempts for run-ledger entries",
    ["pipeline", "event_type", "status"],
)

CONTROL_PLANE_LEDGER_APPEND_DURATION_SECONDS = Histogram(
    "bioetl_control_plane_ledger_append_duration_seconds",
    "Latency of run-ledger append operations in seconds",
    ["pipeline", "event_type", "status"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

CONTROL_PLANE_TERMINAL_EVENTS_TOTAL = Counter(
    "bioetl_control_plane_terminal_events_total",
    "Total terminal run outcomes mirrored from persisted run-ledger entries",
    ["pipeline", "terminal_status"],
)

CONTROL_PLANE_READS_TOTAL = Counter(
    "bioetl_control_plane_reads_total",
    "Total control-plane read and lookup operations by store, operation, and outcome",
    ["store", "operation", "status"],
)

CONTROL_PLANE_READ_DURATION_SECONDS = Histogram(
    "bioetl_control_plane_read_duration_seconds",
    "Latency of control-plane read and lookup operations in seconds",
    ["store", "operation", "status"],
    buckets=[0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

CONTROL_PLANE_LIFECYCLE_DELETED_TOTAL = Counter(
    "bioetl_control_plane_lifecycle_deleted_total",
    "Total control-plane lifecycle artifacts deleted by retention application",
    ["surface", "replay_impact"],
)

CONTROL_PLANE_LIFECYCLE_DELETE_CANDIDATES = Gauge(
    "bioetl_control_plane_lifecycle_delete_candidates",
    "Current number of control-plane lifecycle delete candidates in the latest plan",
)

CONTROL_PLANE_LIFECYCLE_APPLY_TOTAL = Counter(
    "bioetl_control_plane_lifecycle_apply_total",
    "Total control-plane lifecycle plan apply attempts by dry-run policy",
    ["dry_run"],
)
