"""Architecture tests for observability metric governance policy."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import subprocess
import sys

import pytest
from scripts.engineering.qa import report_observability_metric_inventory as inventory
import yaml


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_PATH = ROOT / "configs" / "quality" / "observability_metric_governance.yaml"
POLICY_REVIEW_DATE = date(2026, 5, 15)
ALLOWLIST_PATH = (
    ROOT / "configs" / "quality" / "observability_metric_inventory_allowlist.yaml"
)
EVIDENCE_PATH = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
REGENERATION_COMMAND = (
    "python -m scripts.engineering.qa.report_observability_metric_inventory "
    "--repo-root . "
    "--write-evidence reports/observability/runtime_cardinality_inventory.json"
)


def _collect_fresh_metric_inventory() -> dict[str, object]:
    """Collect inventory in a fresh process to avoid test-order metric pollution."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa.report_observability_metric_inventory",
            "--repo-root",
            str(ROOT),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    loaded = json.loads(result.stdout)
    assert isinstance(loaded, dict)
    return loaded


@pytest.mark.architecture
def test_observability_metric_governance_declares_required_views_and_evidence_path() -> (
    None
):
    payload = yaml.safe_load(GOVERNANCE_PATH.read_text(encoding="utf-8"))

    assert payload["policy_scope"] == "observability_metric_governance"
    assert payload["owner"] == "@bioetl-observability"
    assert (
        payload["report_script"]
        == "scripts/engineering/qa/report_observability_metric_inventory.py"
    )
    assert (
        payload["inventory_allowlist"]
        == "configs/quality/observability_metric_inventory_allowlist.yaml"
    )
    assert (
        payload["derived_metric_declarations"]
        == "configs/quality/observability_metric_declarations.yaml"
    )

    governance_views = payload["governance_views"]
    assert governance_views == {
        "declared_metrics_field": "declared_metrics",
        "emitted_metrics_field": "emitted_metrics",
        "dashboarded_metrics_field": "dashboarded_metrics",
        "alerted_metrics_field": "alerted_metrics",
        "unused_declared_metrics_field": "unused_declared_metrics",
        "emitted_without_declaration_field": "emitted_without_declaration",
        "dashboarded_without_declaration_field": "dashboarded_without_declaration",
        "alerted_without_declaration_field": "alerted_without_declaration",
        "dashboarded_without_emission_field": "dashboarded_without_emission",
        "alerted_without_emission_field": "alerted_without_emission",
        "runtime_cardinality_review_required_field": (
            "runtime_cardinality_review_required"
        ),
        "runtime_cardinality_threshold_violations_field": (
            "runtime_cardinality_threshold_violations"
        ),
    }

    runtime_cardinality_review = payload["runtime_cardinality_review"]
    assert (
        runtime_cardinality_review["heuristic"]
        == "runtime_evidence_with_static_hotspot_seed"
    )
    assert runtime_cardinality_review["min_distinct_emitters"] >= 3
    assert (
        runtime_cardinality_review["exception_allowlist_field"]
        == "runtime_cardinality_review_required"
    )
    assert set(runtime_cardinality_review["exception_metadata_fields"]) >= {
        "metric",
        "owner",
        "reason",
        "review_date",
    }

    evidence_collection = runtime_cardinality_review["evidence_collection"]
    assert evidence_collection["mode"] == "replayable_inventory_evidence_workflow"
    assert (
        evidence_collection["artifact"]
        == "reports/observability/runtime_cardinality_inventory.json"
    )
    command = evidence_collection["command"]
    assert "report_observability_metric_inventory" in command
    assert "--write-evidence" in command

    live_evidence = runtime_cardinality_review["live_evidence"]
    assert (
        live_evidence["workflow"] == ".github/workflows/tests.yml::quality-metrics-gate"
    )
    assert (
        live_evidence["artifact"]
        == "reports/observability/runtime_cardinality_review.json"
    )
    assert live_evidence["summary_output"] == "$GITHUB_STEP_SUMMARY"
    assert live_evidence["status_when_unavailable"] == "degraded"
    assert live_evidence["fail_on_threshold_violation"] is True
    assert live_evidence["fail_on_degraded_release_review"] is True
    assert (
        live_evidence["prometheus_url_env_var"] == "BIOETL_OBSERVABILITY_PROMETHEUS_URL"
    )
    assert (
        live_evidence["prometheus_token_env_var"]
        == "BIOETL_OBSERVABILITY_PROMETHEUS_TOKEN"
    )
    assert "--review-json-out" in live_evidence["command"]
    assert "--summary-out" in live_evidence["command"]
    assert "--fail-on-degraded-live-review" in live_evidence["command"]

    local_fallback_evidence = runtime_cardinality_review["local_fallback_evidence"]
    assert (
        local_fallback_evidence["workflow"]
        == ".github/workflows/tests.yml::governance-preflight"
    )
    assert (
        local_fallback_evidence["artifact"]
        == "reports/observability/runtime_cardinality_review_pr.json"
    )
    assert local_fallback_evidence["release_gate_allowed"] is False
    assert "--allow-local-cardinality-fallback" in local_fallback_evidence["command"]


@pytest.mark.architecture
def test_tests_workflow_keeps_local_cardinality_fallback_out_of_release_gate() -> None:
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )

    assert "--allow-local-cardinality-fallback" in workflow
    assert workflow.index("--allow-local-cardinality-fallback") < workflow.index(
        "Review observability runtime cardinality evidence"
    )
    release_gate = workflow.split(
        "-   name: Review observability runtime cardinality evidence",
        1,
    )[1]
    assert "--fail-on-degraded-live-review" in release_gate
    assert "--allow-local-cardinality-fallback" not in release_gate


@pytest.mark.architecture
def test_runtime_cardinality_allowlist_entries_require_metadata() -> None:
    payload = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    runtime_allowlist = payload["allowed"]["runtime_cardinality_review_required"]

    assert isinstance(runtime_allowlist, list)
    seen_metrics: set[str] = set()
    for entry in runtime_allowlist:
        assert isinstance(entry, dict), (
            "runtime_cardinality_review_required entries must be structured "
            "mappings with metric ownership metadata"
        )
        metric = str(entry["metric"])
        owner = str(entry["owner"])
        reason = str(entry["reason"])
        review_date = str(entry["review_date"])
        approved_max_series = entry.get("approved_max_series")

        assert metric
        assert owner.startswith("@")
        assert reason.strip()
        assert isinstance(approved_max_series, int) and approved_max_series > 0
        assert date.fromisoformat(review_date) >= POLICY_REVIEW_DATE, (
            "runtime_cardinality_review_required lifecycle exception has expired "
            f"review_date: metric={metric} review_date={review_date}"
        )
        assert metric not in seen_metrics, (
            "runtime_cardinality_review_required must not duplicate metric entries: "
            f"{metric}"
        )
        seen_metrics.add(metric)


@pytest.mark.architecture
def test_runtime_cardinality_evidence_artifact_is_committed_and_governed() -> None:
    """Replayable cardinality evidence artifact must stay materialized."""
    assert EVIDENCE_PATH.exists(), (
        "Missing runtime cardinality evidence artifact: "
        "reports/observability/runtime_cardinality_inventory.json"
    )

    actual = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    assert set(actual) >= {
        "declared_metrics",
        "emitted_metrics",
        "runtime_emitters",
        "helper_backed_emitters",
        "runtime_cardinality_review_required",
        "declared_risky_label_review_required",
        "runtime_label_contract_violations",
        "runtime_label_contract_unresolved",
        "runtime_cardinality_evidence",
        "runtime_cardinality_observed_series",
        "runtime_cardinality_threshold_violations",
    }
    for key in (
        "declared_metrics",
        "emitted_metrics",
        "runtime_cardinality_review_required",
        "declared_risky_label_review_required",
        "runtime_label_contract_violations",
        "runtime_label_contract_unresolved",
        "runtime_cardinality_threshold_violations",
    ):
        assert isinstance(actual[key], list), f"{key} must be a list"
        assert actual[key] == sorted(actual[key]), f"{key} must be deterministic"

    runtime_emitters = actual["runtime_emitters"]
    helper_backed_emitters = actual["helper_backed_emitters"]
    alias_emitters = actual.get("alias_emitters", {})
    runtime_cardinality_evidence = actual.get("runtime_cardinality_evidence", {})
    runtime_cardinality_observed_series = actual.get(
        "runtime_cardinality_observed_series",
        {},
    )
    assert isinstance(runtime_emitters, dict)
    assert isinstance(helper_backed_emitters, dict)
    assert isinstance(alias_emitters, dict)
    assert isinstance(runtime_cardinality_evidence, dict)
    assert isinstance(runtime_cardinality_observed_series, dict)
    for metric_name in alias_emitters:
        assert inventory._is_metric_like_alias_name(metric_name), (
            "Alias emitter evidence must contain only Prometheus-style metric names: "
            f"{metric_name!r}"
        )

    allowlist_payload = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    allowlisted_runtime_cardinality = sorted(
        entry["metric"]
        for entry in allowlist_payload["allowed"]["runtime_cardinality_review_required"]
    )
    assert actual["runtime_cardinality_reviewed"] == (
        allowlisted_runtime_cardinality
    ), (
        "Runtime cardinality evidence must stay aligned with the governed "
        "allowlist metadata. Regenerate it with:\n"
        f"{REGENERATION_COMMAND}"
    )
    assert actual["runtime_cardinality_review_required"] == [], (
        "Runtime cardinality review required must contain only unreviewed "
        "multi-emitter candidates. Allowlisted metrics belong in "
        "runtime_cardinality_reviewed. Regenerate it with:\n"
        f"{REGENERATION_COMMAND}"
    )

    expected = _collect_fresh_metric_inventory()
    mismatched_keys = sorted(
        key
        for key in sorted(set(actual) | set(expected))
        if actual.get(key) != expected.get(key)
    )
    assert actual == expected, (
        "Runtime cardinality evidence artifact is stale or inconsistent with the "
        "current static inventory report. Mismatched keys: "
        f"{', '.join(mismatched_keys) if mismatched_keys else '<unknown>'}. "
        "Regenerate it with:\n"
        f"{REGENERATION_COMMAND}"
    )
