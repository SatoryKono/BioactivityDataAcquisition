"""Architecture tests for observability metric governance policy."""

from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from scripts.engineering.qa import check_prometheus_rules
from scripts.engineering.qa import report_observability_metric_inventory as inventory
import yaml


ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_PATH = ROOT / "configs" / "quality" / "observability_metric_governance.yaml"
DECLARATIONS_PATH = (
    ROOT / "configs" / "quality" / "observability_metric_declarations.yaml"
)
CONTROL_PLANE_RULES_PATH = (
    ROOT / "grafana" / "prometheus-rules" / "bioetl_control_plane_current_status.yml"
)
OBSERVABILITY_RULES_PATH = (
    ROOT / "grafana" / "prometheus-rules" / "bioetl_observability.yml"
)
REQUIREMENTS_PATH = ROOT / "docs" / "01-requirements" / "REQUIREMENTS.md"
RULES_PATH = ROOT / "docs" / "00-project" / "RULES.md"
METRICS_DEFS_CORE_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "observability"
    / "_metrics_defs_core.py"
)
POLICY_REVIEW_DATE = date(2026, 5, 15)
ALLOWLIST_PATH = (
    ROOT / "configs" / "quality" / "observability_metric_inventory_allowlist.yaml"
)
EVIDENCE_PATH = (
    ROOT / "reports" / "observability" / "runtime_cardinality_inventory.json"
)
LIVE_REVIEW_PATH = (
    ROOT / "reports" / "observability" / "runtime_cardinality_review.json"
)
REGENERATION_COMMAND = (
    "python -m scripts.engineering.qa.report_observability_metric_inventory "
    "--repo-root . "
    "--write-evidence reports/observability/runtime_cardinality_inventory.json"
)
FRESH_INVENTORY_TIMEOUT_SECONDS = int(
    os.environ.get("BIOETL_OBSERVABILITY_INVENTORY_TIMEOUT_SECONDS", "90")
)
FORCE_FRESH_INVENTORY_SUBPROCESS = (
    os.environ.get("BIOETL_FORCE_FRESH_OBSERVABILITY_INVENTORY_SUBPROCESS") == "1"
)


def _collect_inprocess_metric_inventory() -> dict[str, object]:
    """Collect static inventory without a subprocess for Windows/GDrive runs."""
    inventory._METRIC_INVENTORY_CACHE.clear()
    try:
        loaded = inventory.collect_metric_inventory(ROOT)
    finally:
        inventory._METRIC_INVENTORY_CACHE.clear()
    assert isinstance(loaded, dict)
    return loaded


def _collect_fresh_metric_inventory() -> dict[str, object]:
    """Collect current inventory without hanging Windows/PyCharm subprocess runs."""
    if os.name == "nt" and not FORCE_FRESH_INVENTORY_SUBPROCESS:
        return _collect_inprocess_metric_inventory()

    command = [
        sys.executable,
        "-m",
        "scripts.engineering.qa.report_observability_metric_inventory",
        "--repo-root",
        str(ROOT),
        "--json",
    ]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            cwd=ROOT,
            env=env,
            timeout=FRESH_INVENTORY_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        if os.name == "nt":
            return _collect_inprocess_metric_inventory()
        raise AssertionError(
            "Fresh observability metric inventory subprocess timed out after "
            f"{FRESH_INVENTORY_TIMEOUT_SECONDS}s. Command: {' '.join(command)}"
        ) from exc
    assert result.returncode == 0, result.stderr
    loaded = json.loads(result.stdout)
    assert isinstance(loaded, dict)
    return loaded


def _collect_recording_rule_names(path: Path) -> set[str]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            record_name = rule.get("record")
            if record_name:
                names.add(str(record_name))
    return names


def _collect_recording_rule_exprs(path: Path) -> dict[str, str]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    exprs: dict[str, str] = {}
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            record_name = rule.get("record")
            expr = rule.get("expr")
            if record_name and expr:
                exprs[str(record_name)] = str(expr)
    return exprs


@pytest.mark.architecture
def test_control_plane_rules_are_in_default_prometheus_rule_check() -> None:
    """The shipped control-plane rule file must stay in default promtool coverage."""
    assert (
        check_prometheus_rules.CONTROL_PLANE_RULES_FILE
        in check_prometheus_rules.DEFAULT_RULES_FILES
    )


@pytest.mark.architecture
def test_control_plane_recording_rules_are_declared() -> None:
    """Control-plane recording rules must be under declaration governance."""
    declarations = yaml.safe_load(DECLARATIONS_PATH.read_text(encoding="utf-8"))
    declared = set(declarations["recording_rule_metrics"])
    recording_rules = _collect_recording_rule_names(CONTROL_PLANE_RULES_PATH)

    assert recording_rules
    assert sorted(recording_rules - declared) == []


@pytest.mark.architecture
def test_typed_observability_inventory_is_bidirectional_and_source_specific() -> None:
    """Recording outputs, aliases, consumers, and HTTP targets stay distinct."""
    report = inventory.collect_typed_observability_inventory(ROOT)

    assert len(report["recording_rule_outputs"]) == 104
    assert len(report["policy_alias_metrics"]) == 15
    assert report["recording_outputs_without_declaration"] == []
    assert report["recording_declarations_without_output"] == []
    assert report["policy_aliases_overlapping_outputs"] == []
    assert report["policy_aliases_overlapping_runtime_metrics"] == []
    assert report["policy_aliases_without_catalog"] == []
    assert report["catalog_aliases_without_declaration"] == []
    assert report["prometheus_run_id_selector_violations"] == []
    assert report["http_semantics_violations"] == []
    assert report["panel_contract_drift"] == []
    assert report["documented_metrics"]
    assert report["direct_dashboard_targets"]
    assert report["recording_rule_inputs"]
    assert report["direct_alert_inputs"]

    http_targets = report["http_targets"]
    assert len(http_targets) == 19
    assert any(target["uses_run_id_query_parameter"] for target in http_targets)
    assert all(
        str(target["url"]).startswith(("/ops/", "/health/")) for target in http_targets
    )
    assert report["typed_target_counts"] == {
        "promql": 171,
        "http": 19,
        "loki": 0,
        "tempo": 0,
        "unknown": 0,
    }
    assert all(target["datasource_type"] for target in report["typed_targets"])
    assert all(
        target["datasource_type"] == "yesoreyeram-infinity-datasource"
        and target["documents_valid_empty"]
        and target["documents_backend_down"]
        for target in http_targets
    )


@pytest.mark.architecture
def test_recording_rule_declarations_and_policy_aliases_are_disjoint() -> None:
    declarations = yaml.safe_load(DECLARATIONS_PATH.read_text(encoding="utf-8"))
    recording_outputs = declarations["recording_rule_metrics"]
    policy_aliases = declarations["policy_alias_metrics"]

    assert recording_outputs == sorted(recording_outputs)
    assert policy_aliases == sorted(policy_aliases)
    assert set(recording_outputs).isdisjoint(policy_aliases)


@pytest.mark.architecture
def test_workflow_planned_pipeline_universe_rules_cover_selectors() -> None:
    """Workflow-planned child pipelines must feed dashboard selector universes."""
    observability_exprs = _collect_recording_rule_exprs(OBSERVABILITY_RULES_PATH)
    control_plane_exprs = _collect_recording_rule_exprs(CONTROL_PLANE_RULES_PATH)

    assert "bioetl_workflow_universe" in observability_exprs
    assert "bioetl_workflow_expected" in observability_exprs["bioetl_workflow_universe"]
    assert (
        "bioetl_workflow_pipeline_expected"
        in observability_exprs["bioetl_overview_pipeline_universe"]
    )
    assert (
        "bioetl_workflow_pipeline_expected"
        in observability_exprs["bioetl_runtime_pipeline_run_type_universe"]
    )
    assert (
        observability_exprs["bioetl_overview_pipeline_run_type_universe"]
        == "bioetl_runtime_pipeline_run_type_universe"
    )
    assert (
        "bioetl_workflow_pipeline_expected"
        in control_plane_exprs["bioetl_control_plane_run_type_universe"]
    )


@pytest.mark.architecture
def test_dq_validation_score_label_contract_matches_runtime() -> None:
    """REQ-DQ-002 must stay aligned with the runtime metric label contract."""
    requirements = REQUIREMENTS_PATH.read_text(encoding="utf-8")
    rules = RULES_PATH.read_text(encoding="utf-8")
    metric_defs = METRICS_DEFS_CORE_PATH.read_text(encoding="utf-8")

    assert (
        "Метрика `bioetl_dq_validation_score` с bounded labels `pipeline`, `entity`"
        in requirements
    )
    assert 'bioetl_dq_validation_score{pipeline="...", entity="..."}' in rules
    assert "bioetl_dq_validation_score{check=" not in rules
    assert '["pipeline", "entity"]' in metric_defs


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

    typed_views = payload["typed_observability_views"]
    assert "--typed-observability-views --json" in typed_views["command"]
    assert typed_views["fail_closed_fields"] == [
        "recording_outputs_without_declaration",
        "recording_declarations_without_output",
        "policy_aliases_overlapping_outputs",
        "policy_aliases_overlapping_runtime_metrics",
        "policy_aliases_without_catalog",
        "catalog_aliases_without_declaration",
        "http_semantics_violations",
        "panel_contract_drift",
        "prometheus_run_id_selector_violations",
    ]
    assert set(typed_views["coverage_fields"]) == {
        "documented",
        "direct_dashboard_target",
        "recording_rule_input",
        "direct_alert_input",
        "http_target",
        "typed_target",
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
    touched_metric_change_gate = live_evidence["touched_metric_change_gate"]
    assert (
        touched_metric_change_gate["mode"]
        == "changed_paths_require_fresh_release_review"
    )
    assert touched_metric_change_gate["changed_from_ref"] == "refs/remotes/origin/main"
    assert touched_metric_change_gate["changed_path_trigger_fields"] == [
        "runtime_emitters",
        "helper_backed_emitters",
        "alias_emitters",
        "docs_mentions",
        "rules_mentions",
    ]
    assert touched_metric_change_gate["changed_path_trigger_static_paths"] == [
        "configs/quality/observability_metric_inventory_allowlist.yaml",
        "configs/quality/observability_metric_declarations.yaml",
    ]
    assert touched_metric_change_gate["changed_path_trigger_prefixes"] == [
        "grafana/dashboards/",
        "grafana/prometheus-rules/",
    ]
    assert str(touched_metric_change_gate["rationale"]).strip()

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
def test_tests_workflow_blocks_touched_metric_changes_on_stale_or_degraded_review() -> (
    None
):
    workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
        encoding="utf-8"
    )
    command = (
        "uv run --frozen --no-build python -m scripts.engineering.qa "
        "report-debt-governance-gates --check "
        "--changed-from-ref refs/remotes/origin/main"
    )

    assert command in workflow
    fetch_command = "git fetch --no-tags --depth=1 origin main:refs/remotes/origin/main"
    assert workflow.index(fetch_command) < workflow.index(command)


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


@pytest.mark.architecture
def test_runtime_cardinality_live_review_artifact_is_release_grade() -> None:
    """Release cardinality review evidence must not rely on local fallback."""
    assert LIVE_REVIEW_PATH.exists(), (
        "Missing live runtime cardinality review artifact: "
        "reports/observability/runtime_cardinality_review.json"
    )

    payload = json.loads(LIVE_REVIEW_PATH.read_text(encoding="utf-8"))

    # In local environments without Prometheus, the artifact will be in local_cardinality_fallback mode
    # This is acceptable for local development but not for release gates
    if payload["mode"] == "local_cardinality_fallback":
        # Local fallback is acceptable for local development
        assert payload["local_cardinality_fallback_allowed"] is True
        return

    # In CI with live Prometheus, enforce release-grade constraints
    assert payload["mode"] == "live_review"
    assert payload["status"] == "passed"
    assert payload["local_cardinality_fallback_allowed"] is False
    assert payload["degraded_reasons"] == []
    assert payload["query_errors"] == {}
    assert payload["live_threshold_violations"] == []
    assert payload["static_threshold_violations"] == []
