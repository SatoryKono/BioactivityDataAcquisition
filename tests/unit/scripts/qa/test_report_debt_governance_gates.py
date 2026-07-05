"""Unit tests for debt-governance gate helpers."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import subprocess

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
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {"source_tree_sha256": "live-source-hash"},
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
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {"source_tree_sha256": "live-source-hash"},
    )

    gate = gates._module_coverage_source_tree_hash_gate(
        {"source_tree_sha256": "live-source-hash"},
        repo_root=gates.PROJECT_ROOT,
    )

    assert gate.status == "pass"


def test_module_coverage_scorecard_coherence_gate_passes_when_metrics_align() -> None:
    gate = gates._module_coverage_scorecard_coherence_gate(
        {
            "metrics": {
                "source_module_count": 10,
                "unmeasured_module_count": 0,
                "uncovered_module_count": 0,
            },
            "source_artifacts": {
                "module_coverage_inventory": {"source_tree_sha256": "same-hash"}
            },
        },
        {
            "summary": {
                "source_module_count": 10,
                "unmeasured_module_count": 0,
                "uncovered_module_count": 0,
            },
            "source_tree_sha256": "same-hash",
        },
    )

    assert gate.status == "pass"


def test_module_coverage_scorecard_coherence_gate_fails_for_metric_drift() -> None:
    gate = gates._module_coverage_scorecard_coherence_gate(
        {
            "metrics": {
                "source_module_count": 11,
                "unmeasured_module_count": 1,
                "uncovered_module_count": 0,
            },
            "source_artifacts": {
                "module_coverage_inventory": {"source_tree_sha256": "stale-hash"}
            },
        },
        {
            "summary": {
                "source_module_count": 10,
                "unmeasured_module_count": 0,
                "uncovered_module_count": 0,
            },
            "source_tree_sha256": "live-hash",
        },
    )

    assert gate.status == "fail"


def test_compatibility_scorecard_coherence_gate_passes_when_metrics_align() -> None:
    gate = gates._compatibility_scorecard_coherence_gate(
        {
            "metrics": {
                "retained_entrypoint_count": 12,
                "retained_public_export_facade_count": 4,
                "twin_pair_count": 0,
            }
        },
        {
            "summary": {
                "retained_entrypoint_count": 12,
                "retained_public_export_facade_count": 4,
                "twin_pair_count": 0,
            }
        },
    )

    assert gate.status == "pass"


def test_compatibility_scorecard_coherence_gate_fails_for_metric_drift() -> None:
    gate = gates._compatibility_scorecard_coherence_gate(
        {
            "metrics": {
                "retained_entrypoint_count": 13,
                "retained_public_export_facade_count": 4,
                "twin_pair_count": 1,
            }
        },
        {
            "summary": {
                "retained_entrypoint_count": 12,
                "retained_public_export_facade_count": 4,
                "twin_pair_count": 0,
            }
        },
    )

    assert gate.status == "fail"


def test_remote_baseline_allows_branch_introduced_missing_artifacts() -> None:
    remote_baseline = {
        "artifacts": [
            {
                "path": "reports/quality/compatibility-importer-census.json",
                "required": True,
                "required_on_remote": False,
                "introduced_after_remote_main": True,
                "summary": {"available": False},
            },
            {
                "path": "reports/quality/module-coverage-inventory.json",
                "required": True,
                "required_on_remote": True,
                "introduced_after_remote_main": False,
                "summary": {"available": True},
            },
        ]
    }

    assert gates._unavailable_required_remote_baseline_artifacts(remote_baseline) == []


def test_remote_baseline_fails_for_missing_artifact_required_on_remote() -> None:
    remote_baseline = {
        "artifacts": [
            {
                "path": "reports/quality/module-coverage-inventory.json",
                "required": True,
                "required_on_remote": True,
                "introduced_after_remote_main": False,
                "summary": {"available": False},
            }
        ]
    }

    assert gates._unavailable_required_remote_baseline_artifacts(remote_baseline) == [
        remote_baseline["artifacts"][0]
    ]


def test_module_coverage_aggregate_residual_limits_returns_none_without_ratchets() -> (
    None
):
    assert gates._module_coverage_aggregate_residual_limits({}) is None


def test_module_coverage_aggregate_residual_limits_reads_reviewed_limits() -> None:
    limits = gates._module_coverage_aggregate_residual_limits(
        {
            "aggregate_residual_ratchets": {
                "unmeasured_module_count": {"max_count": 2},
                "uncovered_module_count": {"max_count": 5},
            }
        }
    )

    assert limits == {
        "unmeasured_module_count": 2,
        "uncovered_module_count": 5,
    }


def test_budget_growth_increases_flags_raised_scorecard_limits() -> None:
    increases = gates._budget_growth_increases(
        baseline_payload={
            "family": {
                "metrics": {
                    "size": {"max_count": 3},
                    "warnings": {"current_count": 2},
                }
            }
        },
        current_payload={
            "family": {
                "metrics": {
                    "size": {"max_count": 4},
                    "warnings": {"current_count": 10},
                }
            }
        },
    )

    assert increases == {"family.metrics.size.max_count": {"from": 3, "to": 4}}


def test_budget_growth_increases_ignores_flat_or_lower_limits() -> None:
    assert (
        gates._budget_growth_increases(
            baseline_payload={"family": {"metrics": {"size": {"max_count": 3}}}},
            current_payload={"family": {"metrics": {"size": {"max_count": 2}}}},
        )
        == {}
    )


def test_debt_scorecard_budget_no_growth_gate_fails_on_budget_increase(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_load_yaml_from_git_ref",
        lambda repo_root, ref, rel_path: {"family": {"max_count": 3}},
    )
    monkeypatch.setattr(
        gates,
        "_load_yaml",
        lambda repo_root, rel_path: {"family": {"max_count": 4}},
    )

    gate = gates._debt_scorecard_budget_no_growth_gate(
        repo_root=gates.PROJECT_ROOT,
        changed_from_ref="origin/main",
    )

    assert gate.status == "fail"
    assert gate.current == {"family.max_count": {"from": 3, "to": 4}}


def test_flaky_untriaged_entries_require_triage_status() -> None:
    untriaged = gates._flaky_untriaged_entries(
        {
            "reviewed_flaky_tests": [
                {"nodeid": "tests/unit/test_a.py::test_ok", "triage_status": "fixed"},
                {"nodeid": "tests/unit/test_b.py::test_missing"},
                {
                    "nodeid": "tests/unit/test_c.py::test_unknown",
                    "triage_status": "unknown",
                },
            ]
        }
    )

    assert [entry["nodeid"] for entry in untriaged] == [
        "tests/unit/test_b.py::test_missing",
        "tests/unit/test_c.py::test_unknown",
    ]


def test_build_payload_fails_release_when_module_coverage_inventory_hash_is_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sys

    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(
        gates,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {"source_tree_sha256": "stale-source-hash"},
    )

    payload = gates.build_payload(repo_root=gates.PROJECT_ROOT)
    summary = payload["summary"]
    assert isinstance(summary, dict)

    failing_gates = summary["failing_gates"]
    assert isinstance(failing_gates, list)
    assert "module_coverage_source_tree_hash_current" in failing_gates
    assert "generated_artifact_drift" in failing_gates
    assert summary["release_gate_status"] == "failing"


def test_build_payload_tolerates_unavailable_remote_main_baseline_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_coverage = gates._load_json(
        gates.PROJECT_ROOT, "reports/quality/module-coverage-inventory.json"
    )
    assert isinstance(module_coverage, dict)
    monkeypatch.setattr(
        gates,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {
            "source_tree_sha256": module_coverage["source_tree_sha256"]
        },
    )
    monkeypatch.setattr(
        gates,
        "_artifact_matches_builder",
        lambda *, repo_root, rel_path, payload_builder: True,
    )
    monkeypatch.setattr(
        gates.report_architecture_debt_remote_main_baseline,
        "build_payload",
        lambda **kwargs: (_ for _ in ()).throw(
            subprocess.CalledProcessError(
                returncode=1,
                cmd=["git", "ls-remote", "origin", "refs/heads/main"],
            )
        ),
    )

    payload = gates.build_payload(repo_root=gates.PROJECT_ROOT)
    summary = payload["summary"]
    assert isinstance(summary, dict)

    failing_gates = summary["failing_gates"]
    assert isinstance(failing_gates, list)
    assert "generated_artifact_drift" not in failing_gates


def test_build_payload_marks_config_surface_backlog_drift_as_stale_artifact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gates,
        "_refresh_existing_inventory_source_tree",
        lambda payload, *, repo_root: {"source_tree_sha256": "live-source-hash"},
    )
    monkeypatch.setattr(
        gates,
        "build_backlog",
        lambda: {"schema_version": "drifted-live-backlog"},
    )

    payload = gates.build_payload(repo_root=gates.PROJECT_ROOT)
    summary = payload["summary"]
    assert isinstance(summary, dict)
    assert payload["stale_artifacts"]["config_surface_backlog"] is True
    assert "generated_artifact_drift" in summary["failing_gates"]


def test_remote_main_baseline_stale_check_ignores_revision_metadata_only(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    baseline_dir = tmp_path / "reports" / "quality"
    baseline_dir.mkdir(parents=True)
    committed = {
        "schema_version": 1,
        "generated_by": "scripts.engineering.qa.report_architecture_debt_remote_main_baseline",
        "evidence_source": "remote_main_git_tree",
        "remote": "origin",
        "branch": "main",
        "remote_main_ref": "refs/heads/main",
        "remote_main_sha": "old",
        "local_tracking_ref": "origin/main",
        "local_tracking_ref_sha": "old",
        "local_tracking_ref_matches_remote": True,
        "generator_commands": [
            "python -m scripts.engineering.qa report-module-coverage --check"
        ],
        "artifacts": [
            {
                "path": "reports/quality/module-coverage-inventory.json",
                "source_revision": "old",
                "blob_sha256": "same-blob",
                "required": True,
                "summary": {"available": True, "source_tree_sha256": "same-source"},
            }
        ],
    }
    live = {
        **committed,
        "remote_main_sha": "new",
        "local_tracking_ref_sha": "new",
        "artifacts": [
            {
                **committed["artifacts"][0],
                "source_revision": "new",
            }
        ],
    }
    (baseline_dir / "architecture-debt-remote-main-baseline.json").write_text(
        json.dumps(committed),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        gates.report_architecture_debt_remote_main_baseline,
        "build_payload",
        lambda **kwargs: live,
    )

    assert (
        gates._remote_main_baseline_artifact_matches_builder(repo_root=tmp_path) is True
    )


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


def test_check_artifacts_can_skip_artifact_comparison_for_changed_path_gate(
    tmp_path,
) -> None:
    payload = {
        "summary": {
            "gate_count": 1,
            "pass_count": 1,
            "warn_count": 0,
            "fail_count": 0,
            "release_gate_status": "passing",
            "architecture_quality_scorecard_integral_score": 7.98,
            "architecture_quality_scorecard_interpretation": (
                "satisfactory_system_refactoring_required"
            ),
        },
        "gates": [],
    }

    errors = gates._check_artifacts(
        payload,
        json_out=tmp_path / "missing.json",
        md_out=tmp_path / "missing.md",
        compare_artifacts=False,
    )

    assert errors == []


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


def test_collect_metric_change_trigger_paths_includes_dashboard_and_alert_surfaces() -> (
    None
):
    trigger_paths = gates._collect_metric_change_trigger_paths(
        {
            "runtime_emitters": {
                "bioetl_example_total": ["src/bioetl/observability/example.py"]
            },
            "docs_mentions": {
                "bioetl_example_total": ["grafana/dashboards/example.json"]
            },
            "rules_mentions": {
                "bioetl_example_total": ["grafana/prometheus-rules/example.yml"]
            },
        },
        {
            "runtime_cardinality_review": {
                "live_evidence": {
                    "touched_metric_change_gate": {
                        "changed_path_trigger_fields": [
                            "runtime_emitters",
                            "docs_mentions",
                            "rules_mentions",
                        ],
                        "changed_path_trigger_static_paths": [
                            "configs/quality/observability_metric_declarations.yaml"
                        ],
                        "changed_path_trigger_prefixes": [
                            "grafana/dashboards/",
                            "grafana/prometheus-rules/",
                        ],
                    }
                }
            }
        },
    )

    assert {
        "src/bioetl/observability/example.py",
        "grafana/dashboards/example.json",
        "grafana/prometheus-rules/example.yml",
        "configs/quality/observability_metric_declarations.yaml",
        "grafana/dashboards/",
        "grafana/prometheus-rules/",
    } <= trigger_paths


def test_observability_touched_metric_review_gate_matches_static_prefixes() -> None:
    gate = gates._observability_touched_metric_review_gate(
        {"generated_at": "2026-06-04T15:01:29Z", "status": "passed"},
        changed_paths={"grafana/dashboards/new-metric.json"},
        trigger_paths={"grafana/dashboards/"},
        now=datetime(2026, 7, 6, 15, 1, 29, tzinfo=UTC),
    )

    assert gate.status == "fail"
    assert gate.current == 1


def test_observability_touched_metric_inventory_gate_passes_without_metric_changes() -> (
    None
):
    gate = gates._observability_touched_metric_inventory_gate(
        {"declared_metrics": []},
        changed_paths={"docs/README.md"},
        trigger_paths={"grafana/dashboards/"},
        repo_root=gates.PROJECT_ROOT,
        current_inventory={"declared_metrics": []},
    )

    assert gate.status == "pass"
    assert gate.current == 0


def test_observability_touched_metric_inventory_gate_fails_for_stale_artifact() -> None:
    gate = gates._observability_touched_metric_inventory_gate(
        {"declared_metrics": ["bioetl_old_total"]},
        changed_paths={"grafana/prometheus-rules/new-rule.yml"},
        trigger_paths={"grafana/prometheus-rules/"},
        repo_root=gates.PROJECT_ROOT,
        current_inventory={"declared_metrics": ["bioetl_new_total"]},
    )

    assert gate.status == "fail"
    assert gate.current is False
    assert gate.limit is True


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
