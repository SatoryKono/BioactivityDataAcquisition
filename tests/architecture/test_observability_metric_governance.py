"""Architecture tests for observability metric governance policy."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path

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
    }

    runtime_cardinality_review = payload["runtime_cardinality_review"]
    assert runtime_cardinality_review["heuristic"] == "multi_emitter_static_proxy"
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

        assert metric
        assert owner.startswith("@")
        assert reason.strip()
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
    }
    for key in (
        "declared_metrics",
        "emitted_metrics",
        "runtime_cardinality_review_required",
        "declared_risky_label_review_required",
        "runtime_label_contract_violations",
        "runtime_label_contract_unresolved",
    ):
        assert isinstance(actual[key], list), f"{key} must be a list"
        assert actual[key] == sorted(actual[key]), f"{key} must be deterministic"

    runtime_emitters = actual["runtime_emitters"]
    helper_backed_emitters = actual["helper_backed_emitters"]
    assert isinstance(runtime_emitters, dict)
    assert isinstance(helper_backed_emitters, dict)

    allowlist_payload = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    allowlisted_runtime_cardinality = sorted(
        entry["metric"]
        for entry in allowlist_payload["allowed"]["runtime_cardinality_review_required"]
    )
    assert actual["runtime_cardinality_review_required"] == (
        allowlisted_runtime_cardinality
    ), (
        "Runtime cardinality evidence must stay aligned with the governed "
        "allowlist metadata. Regenerate it with:\n"
        f"{REGENERATION_COMMAND}"
    )

    expected = inventory.collect_metric_inventory(ROOT)
    mismatched_keys = sorted(
        key for key in sorted(set(actual) | set(expected)) if actual.get(key) != expected.get(key)
    )
    assert actual == expected, (
        "Runtime cardinality evidence artifact is stale or inconsistent with the "
        "current static inventory report. Mismatched keys: "
        f"{', '.join(mismatched_keys) if mismatched_keys else '<unknown>'}. "
        "Regenerate it with:\n"
        f"{REGENERATION_COMMAND}"
    )
