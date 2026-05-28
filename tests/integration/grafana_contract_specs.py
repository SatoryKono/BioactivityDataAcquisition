"""Shared data matrices for Grafana integration contract tests."""

from __future__ import annotations

CONTROL_PLANE_GLOBAL_SCOPE_EXPECTATIONS = {
    "bioetl-control-plane-v1.json": (
        "Monitor: GLOBAL Control-Plane Read Failures",
        "Monitor: GLOBAL Control-Plane Read Failure Ratio Severity",
        "Track: GLOBAL Control-Plane Read Latency p50/p95/p99",
        "Track: GLOBAL Control-Plane Reads by Store / Operation / Status",
        "Monitor: GLOBAL Checkpoint Operator Failures",
        "Track: GLOBAL Checkpoint Operator Latency p50/p95/p99",
    ),
}

CONTROL_PLANE_GLOBAL_READ_PANEL_TITLES = {
    "bioetl-control-plane-v1.json": (
        "Monitor: GLOBAL Control-Plane Read Failures",
        "Monitor: GLOBAL Control-Plane Read Failure Ratio Severity",
        "Track: GLOBAL Control-Plane Read Latency p50/p95/p99",
        "Track: GLOBAL Control-Plane Reads by Store / Operation / Status",
    ),
}

SUMMARY_ZERO_FALLBACK_EXPECTATIONS = {
    "bioetl-runtime.json": {
        "Track Records by Stage / Interval": "or vector(0)",
        "Monitor Pipeline Alert Conditions": "or vector(0)",
        "Inspect DQ Alert Conditions": "or vector(0)",
        "Inspect Control-plane Alert Conditions": "or vector(0)",
        "Inspect Provider Alert Conditions": "or vector(0)",
        "Inspect GLOBAL Provider Alert Conditions": "or vector(0)",
        "Track GLOBAL Shutdown Initiated by Reason / Interval": "or vector(0)",
        "Track GLOBAL Shutdown Completed by Reason / Interval": "or vector(0)",
    },
    "bioetl-provider-health-v2.json": {
        "Monitor Healthy Checks (Selected Range)": "or vector(0)",
        "Monitor Degraded Checks (Selected Range)": "or vector(0)",
        "Track Provider Failure Rate (Selected Range)": "or vector(0)",
        "Track Health Checks Total (Selected Range)": "or vector(0)",
        "Inspect HTTP Errors by Method/Error Type": "or vector(0)",
    },
    "bioetl-dq-v2.json": {
        "Track: Records Quarantined in Range": "or vector(0)",
        "Track: Silver Filter Rejects in Range": "or vector(0)",
        "Track: Silver Validation Failures in Range": "or vector(0)",
        "Monitor: Silver Validation Failures": "or vector(0)",
        "Monitor: Gold Strict Validation Failures": "or vector(0)",
    },
    "bioetl-control-plane-v1.json": {
        "Monitor: Manifest Write Failures": "or vector(0)",
        "Monitor: Ledger Append Failures": "or vector(0)",
        "Monitor: Checkpoint Incompatibilities": "or vector(0)",
        "Monitor: GLOBAL Control-Plane Read Failures": "or vector(0)",
        "Monitor: GLOBAL Control-Plane Read Failure Ratio Severity": "or vector(0)",
        "Monitor: Checkpoint Load Failures": "or vector(0)",
        "Monitor: Checkpoint Save Failures": "or vector(0)",
        "Monitor: GLOBAL Checkpoint Operator Failures": "or vector(0)",
        "Monitor: Replay Not Reconstructable": "or vector(0)",
        "Monitor: Replay Drift": "or vector(0)",
        "Track: Replay / Resume Blockers in Range": "or vector(0)",
        "Track: GLOBAL Audit Write Outcomes": "or vector(0)",
        "Track: GLOBAL Audit Query Outcomes": "or vector(0)",
        "Monitor: Lineage Fragment Persistence Failures": "or vector(0)",
        "Monitor: Lineage Refs Missing": "or vector(0)",
    },
    "bioetl-workflow-overview.json": {
        "Failed Workflow Runs / Range": "or vector(0)",
        "Failed Pipeline Steps / Range": "or vector(0)",
        "Failed Transform Steps / Range": "or vector(0)",
        "Skipped Step Events / Range": "or vector(0)",
    },
}
