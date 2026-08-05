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
"""Shared data matrices for Grafana integration contract tests."""

from __future__ import annotations

CONTROL_PLANE_GLOBAL_SCOPE_EXPECTATIONS = {
    "bioetl-control-plane-v1.json": (
        "Track Global Read Failures",
        "Monitor Global Read Failures (30m)",
        "Track Global Read Latency",
        "Compare Global Reads by Store",
        "Track Global Checkpoint Admin Failures",
        "Track Global Checkpoint Admin Latency",
    ),
}

CONTROL_PLANE_GLOBAL_READ_PANEL_TITLES = {
    "bioetl-control-plane-v1.json": (
        "Track Global Read Failures",
        "Monitor Global Read Failures (30m)",
        "Track Global Read Latency",
        "Compare Global Reads by Store",
    ),
}

# Summary panels must preserve PromQL absence as No data (no masking `or vector(0)`).
# Display-level empty text (fieldConfig.noValue) may still render operator-facing zeros.
SUMMARY_NO_VECTOR_ZERO_FALLBACK_PANELS = {
    "bioetl-runtime.json": {
        "Track Records by Stage / Interval",
        "Track Global Shutdown Starts",
        "Track Global Shutdown Completions",
        "Track Failed Workflow Runs",
        "Track Failed Workflow Steps",
    },
    "bioetl-provider-health-v2.json": {
        "Monitor Healthy Checks",
        "Monitor Health Checks",
    },
    "bioetl-control-plane-v1.json": {
        "Compare Global Audit Write Outcomes",
        "Compare Global Audit Query Outcomes",
    },
}

# Deprecated name retained only as an empty map so stale importers fail closed
# instead of re-introducing masking `or vector(0)` expectations.
SUMMARY_ZERO_FALLBACK_EXPECTATIONS: dict[str, dict[str, str]] = {}

DIAGNOSTIC_NO_ZERO_FALLBACK_EXPECTATIONS = {
    "bioetl-runtime.json": {
        "Monitor Pipeline Alert Conditions",
        "Inspect DQ Alert Conditions",
        "Inspect Control Plane Alert Conditions",
        "Inspect Provider Alert Conditions",
        "Inspect Global Provider Alert Conditions",
    },
    "bioetl-provider-health-v2.json": {
        "Monitor Degraded Checks",
        "Track Failure Rate",
        "Track Rate-Limit Errors",
        "Track Network & Timeout Errors",
    },
    "bioetl-dq-v2.json": {
        "Monitor Quarantined Records",
        "Monitor Silver Filter Rejects",
        "Monitor Silver Validation Failures",
        "Monitor Gold Validation Failures",
    },
    "bioetl-control-plane-v1.json": {
        "Track Manifest Write Failures",
        "Track Ledger Append Failures",
        "Track Checkpoint Incompatibilities",
        "Track Global Read Failures",
        "Monitor Global Read Failures (30m)",
        "Track Checkpoint Load Failures",
        "Track Checkpoint Save Failures",
        "Track Global Checkpoint Admin Failures",
        "Track Unreconstructable Replays",
        "Track Replay Drift",
        "Track Replay Blockers",
        "Track Lineage Persistence Failures",
        "Track Missing Lineage References",
    },
}
