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

SUMMARY_ZERO_FALLBACK_EXPECTATIONS = {
    "bioetl-runtime.json": {
        "Track Records by Stage / Interval": "or vector(0)",
        "Monitor Pipeline Alert Conditions": "or vector(0)",
        "Inspect DQ Alert Conditions": "or vector(0)",
        "Inspect Control Plane Alert Conditions": "or vector(0)",
        "Inspect Provider Alert Conditions": "or vector(0)",
        "Inspect Global Provider Alert Conditions": "or vector(0)",
        "Track Global Shutdown Starts": "or vector(0)",
        "Track Global Shutdown Completions": "or vector(0)",
        "Track Failed Workflow Runs": "or vector(0)",
        "Track Failed Workflow Steps": "or vector(0)",
    },
    "bioetl-provider-health-v2.json": {
        "Monitor Healthy Checks": "or vector(0)",
        "Monitor Degraded Checks": "or vector(0)",
        "Track Failure Rate": "or vector(0)",
        "Monitor Health Checks": "or vector(0)",
        "Track Rate-Limit Errors": "or vector(0)",
        "Track Network & Timeout Errors": "or vector(0)",
    },
    "bioetl-dq-v2.json": {
        "Monitor Quarantined Records": "or vector(0)",
        "Monitor Silver Filter Rejects": "or vector(0)",
        "Monitor Silver Validation Failures": "or vector(0)",
        "Monitor Gold Validation Failures": "or vector(0)",
    },
    "bioetl-control-plane-v1.json": {
        "Track Manifest Write Failures": "or vector(0)",
        "Track Ledger Append Failures": "or vector(0)",
        "Track Checkpoint Incompatibilities": "or vector(0)",
        "Track Global Read Failures": "or vector(0)",
        "Monitor Global Read Failures (30m)": "or vector(0)",
        "Track Checkpoint Load Failures": "or vector(0)",
        "Track Checkpoint Save Failures": "or vector(0)",
        "Track Global Checkpoint Admin Failures": "or vector(0)",
        "Track Unreconstructable Replays": "or vector(0)",
        "Track Replay Drift": "or vector(0)",
        "Track Replay Blockers": "or vector(0)",
        "Compare Global Audit Write Outcomes": "or vector(0)",
        "Compare Global Audit Query Outcomes": "or vector(0)",
        "Track Lineage Persistence Failures": "or vector(0)",
        "Track Missing Lineage References": "or vector(0)",
    },
    # retired
    "bioetl-workflow-overview.json_RETIRED": {
        "Failed Workflow Runs / Range": "or vector(0)",
        "Failed Pipeline Steps / Range": "or vector(0)",
        "Failed Transform Steps / Range": "or vector(0)",
        "Skipped Step Events / Range": "or vector(0)",
    },
}
