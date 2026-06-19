"""Unit tests for debt-governance gate helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from scripts.engineering.qa import report_debt_governance_gates as gates

pytestmark = pytest.mark.unit


def test_release_review_freshness_gate_passes_for_recent_live_review() -> None:
    gate = gates._release_review_freshness_gate(
        {"generated_at": "2026-06-04T15:01:29Z"},
        now=datetime(2026, 6, 17, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "pass"
    assert gate.name == "observability_release_review_freshness"
    assert gate.current == 13
    assert gate.limit == gates.RELEASE_REVIEW_MAX_AGE_DAYS


def test_release_review_freshness_gate_fails_for_stale_live_review() -> None:
    gate = gates._release_review_freshness_gate(
        {"generated_at": "2026-06-04T15:01:29Z"},
        now=datetime(2026, 7, 6, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 32


def test_release_review_freshness_gate_fails_for_invalid_generated_at() -> None:
    gate = gates._release_review_freshness_gate(
        {"generated_at": "not-a-timestamp"},
        now=datetime(2026, 6, 17, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == "missing_or_invalid"


def test_release_review_freshness_gate_fails_for_future_generated_at() -> None:
    gate = gates._release_review_freshness_gate(
        {"generated_at": "2026-06-18T00:00:00Z"},
        now=datetime(2026, 6, 17, 0, 0, 0, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == -1


def test_release_gate_status_prioritizes_failures_over_warnings() -> None:
    assert gates._release_gate_status({"pass": 25, "warn": 0, "fail": 1}) == "failing"
    assert gates._release_gate_status({"pass": 25, "warn": 1, "fail": 0}) == "warning"
    assert gates._release_gate_status({"pass": 26, "warn": 0, "fail": 0}) == "passing"


def test_module_coverage_source_tree_hash_gate_fails_for_stale_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "compute_source_tree_sha256",
        lambda *, repo_root: "live-source-hash",
    )

    gate = gates._module_coverage_source_tree_hash_gate(
        {"source_tree_sha256": "committed-source-hash"},
        repo_root=gates.PROJECT_ROOT,
    )

    assert gate.name == "module_coverage_source_tree_hash_current"
    assert gate.status == "fail"
    assert gate.current == "live-source-hash"
    assert gate.limit == "committed-source-hash"


def test_module_coverage_source_tree_hash_gate_passes_for_current_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "compute_source_tree_sha256",
        lambda *, repo_root: "live-source-hash",
    )

    gate = gates._module_coverage_source_tree_hash_gate(
        {"source_tree_sha256": "live-source-hash"},
        repo_root=gates.PROJECT_ROOT,
    )

    assert gate.status == "pass"


def test_render_markdown_separates_weighted_score_from_release_gate_status() -> None:
    payload = {
        "summary": {
            "gate_count": 1,
            "pass_count": 0,
            "warn_count": 0,
            "fail_count": 1,
            "release_gate_status": "failing",
            "architecture_quality_scorecard_integral_score": 7.98,
            "architecture_quality_scorecard_interpretation": (
                "satisfactory_system_refactoring_required"
            ),
        },
        "gates": [
            {
                "name": "generated_artifact_drift",
                "status": "fail",
                "metric": "stale_artifact_count",
                "current": 1,
                "limit": 0,
                "source_artifact": "reports/quality/*.json",
            }
        ],
    }

    markdown = gates.render_markdown(payload)

    assert "release_gate_status: `failing`" in markdown
    assert "architecture_quality_scorecard_integral_score: `7.98`" in markdown


def test_observability_touched_metric_review_gate_passes_without_metric_changes() -> (
    None
):
    gate = gates._observability_touched_metric_review_gate(
        {"generated_at": "2026-06-04T15:01:29Z", "status": "passed"},
        changed_paths={"src/bioetl/interfaces/cli/main.py"},
        trigger_paths={"src/bioetl/infrastructure/observability/server.py"},
        now=datetime(2026, 6, 17, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "pass"
    assert gate.current == 0


def test_observability_touched_metric_review_gate_fails_for_stale_review() -> None:
    gate = gates._observability_touched_metric_review_gate(
        {"generated_at": "2026-06-04T15:01:29Z", "status": "passed"},
        changed_paths={"src/bioetl/infrastructure/observability/server.py"},
        trigger_paths={"src/bioetl/infrastructure/observability/server.py"},
        now=datetime(2026, 7, 6, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 1


def test_observability_touched_metric_review_gate_fails_for_degraded_review() -> None:
    gate = gates._observability_touched_metric_review_gate(
        {"generated_at": "2026-06-04T15:01:29Z", "status": "degraded"},
        changed_paths={"configs/quality/observability_metric_declarations.yaml"},
        trigger_paths={"configs/quality/observability_metric_declarations.yaml"},
        now=datetime(2026, 6, 17, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 1
