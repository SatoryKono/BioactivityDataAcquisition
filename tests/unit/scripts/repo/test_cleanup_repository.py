"""Unit tests for deterministic repository cleanup candidate discovery."""

from __future__ import annotations

import pytest

import json
import os
import sys
from pathlib import Path

import yaml

from scripts.ops.support.repo import cleanup_repository as module


pytestmark = pytest.mark.unit


def _set_age_days(path: Path, *, days: int) -> None:
    age_seconds = days * 24 * 60 * 60
    now = path.stat().st_mtime
    target = now - age_seconds
    os.utime(path, (target, target))


def _write_governance_files(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    allowlist_path = tmp_path / ".github" / "root-allowlist.txt"
    allowlist_path.parent.mkdir(parents=True)
    allowlist_path.write_text("README.md\npyproject.toml\n", encoding="utf-8")
    catalog_path = tmp_path / "configs" / "quality" / "repo_structure_catalog.yaml"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(
        yaml.safe_dump(
            {
                "docs_drafts": {"allowed_files": []},
                "plans": {
                    "readme": "docs/plans/README.md",
                    "max_active_backlog": 1,
                    "allowed_files": [
                        {
                            "path": "docs/plans/consolidated-open-tasks-plan-2026-03-21.md",
                            "lifecycle": "active_backlog",
                        }
                    ],
                },
                "src_sidecars": {
                    "approved_roots": [
                        {"path": "src/bioetl"},
                        {"path": "src/tools"},
                        {"path": "src/memory"},
                    ]
                },
                "root_tooling_roots": {
                    "approved_roots": [{"path": "tools"}],
                },
                "blocked_cleanup_zones": [
                    {"path": "reports"},
                    {"path": "data"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    routing_path = tmp_path / "configs" / "quality" / "generated_artifact_routing.yaml"
    routing_path.write_text(
        yaml.safe_dump(
            {
                "routes": [
                    {
                        "id": "file-merger-working-reports",
                        "generator": "src/tools/file_merger.py",
                        "commit_policy": "working_output",
                        "outputs": [
                            "reports/documentation_merged.md",
                            "reports/project_structure.md",
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    replay_inventory_path = (
        tmp_path / "configs" / "quality" / "replay_safe_cleanup_inventory.yaml"
    )
    replay_inventory_path.write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "entries": [
                    {
                        "id": "reports_quality_tmp_diagnostics",
                        "path": "reports/quality/_tmp_*",
                        "owner": "Engineering / Quality",
                        "ttl_days": 7,
                    },
                    {
                        "id": "reports_quality_pretest_guardrails_history",
                        "path": "reports/quality/pretest_guardrails_*.json",
                        "owner": "Engineering / Quality",
                        "ttl_days": 30,
                    },
                    {
                        "id": "reports_quality_architecture_debt_execution_plans",
                        "path": "reports/quality/architecture_debt_execution_plan_*.json",
                        "owner": "Engineering / Architecture",
                        "ttl_days": 30,
                    },
                    {
                        "id": "reports_quality_architecture_metric_exemption_tasks",
                        "path": "reports/quality/tasks_architecture_metric_exemptions_*.json",
                        "owner": "Engineering / Architecture",
                        "ttl_days": 30,
                    },
                    {
                        "id": "reports_quality_duplication_baseline_working_snapshots",
                        "path": "reports/quality/duplication-baseline.*",
                        "owner": "Engineering / Architecture",
                        "ttl_days": 30,
                    },
                    {
                        "id": "reports_quality_contract_registry_dq_diagnostics",
                        "path": "reports/quality/contract-registry-dq-diagnostics.json",
                        "owner": "Engineering / Quality",
                        "ttl_days": 30,
                    },
                    {
                        "id": "reports_quality_test_runs",
                        "path": "reports/quality/test-runs",
                        "owner": "Engineering / Quality",
                        "ttl_days": 30,
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_review_registry(tmp_path: Path, lanes: list[dict[str, object]]) -> None:
    registry_path = (
        tmp_path / "configs" / "quality" / "root_hygiene_review_registry.yaml"
    )
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        yaml.safe_dump(
            {
                "version": "1.0.0",
                "status": "active",
                "current_live_root_baseline": {
                    "tracked_root_audit_status": "pass",
                    "strict_untracked_root_audit_status": "pass",
                    "verification_command": "python audit_root_cleanliness.py --strict-untracked",
                },
                "review_lanes": lanes,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_collect_cleanup_candidates_excludes_blocked_cleanup_zones(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    allowed = tmp_path / ".pytest_cache"
    blocked = tmp_path / "reports" / ".pytest_cache"
    allowed.mkdir()
    blocked.mkdir(parents=True)

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: [])

    candidates = module.collect_cleanup_candidates(tmp_path)
    rel_paths = {candidate.rel_path for candidate in candidates}

    assert ".pytest_cache" in rel_paths
    assert "reports/.pytest_cache" not in rel_paths


def test_collect_cleanup_candidates_reports_tracked_policy_candidates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    monkeypatch.setattr(
        module,
        "_tracked_paths",
        lambda repo_root: [".python-user/site.py", "README.md"],
    )

    candidates = module.collect_cleanup_candidates(tmp_path)

    assert any(
        candidate.tracked
        and not candidate.apply_allowed
        and candidate.rel_path == ".python-user/site.py"
        for candidate in candidates
    )


def test_collect_cleanup_candidates_includes_safe_local_log_temp_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    for relative_path in (
        "worker.log",
        "session.tmp",
        "full_log.txt",
        "final_report_debug.txt",
        "project_rules_failures.txt",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("artifact\n", encoding="utf-8")

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: [])

    candidates = module.collect_cleanup_candidates(tmp_path)
    rel_paths = {candidate.rel_path for candidate in candidates}

    assert "worker.log" in rel_paths
    assert "session.tmp" in rel_paths
    assert "full_log.txt" in rel_paths
    assert "final_report_debug.txt" in rel_paths
    assert "project_rules_failures.txt" in rel_paths


def test_collect_cleanup_candidates_excludes_blocked_zone_log_temp_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    for relative_path in (
        "reports/worker.log",
        "reports/session.tmp",
        "data/full_log.txt",
        "data/final_report_debug.txt",
        "reports/project_rules_failures.txt",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("artifact\n", encoding="utf-8")

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: [])

    candidates = module.collect_cleanup_candidates(tmp_path)
    rel_paths = {candidate.rel_path for candidate in candidates}

    assert "reports/worker.log" not in rel_paths
    assert "reports/session.tmp" not in rel_paths
    assert "data/full_log.txt" not in rel_paths
    assert "data/final_report_debug.txt" not in rel_paths
    assert "reports/project_rules_failures.txt" not in rel_paths


def test_collect_cleanup_candidates_includes_egg_info_and_notebook_checkpoints(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    (tmp_path / "dist-info.egg-info").mkdir()
    (tmp_path / ".ipynb_checkpoints").mkdir()

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: [])

    candidates = module.collect_cleanup_candidates(tmp_path)
    rel_paths = {candidate.rel_path for candidate in candidates}

    assert "dist-info.egg-info" in rel_paths
    assert ".ipynb_checkpoints" in rel_paths


def test_collect_root_review_evidence_marks_absent_baseline_ok(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    _write_review_registry(
        tmp_path,
        [
            {
                "lane_id": "lane",
                "classification": "review_required",
                "verification": ["git ls-files foo"],
                "candidates": [
                    {
                        "path": "root-helper.ps1",
                        "current_live_state": "absent_from_root_baseline",
                        "canonical_path": "scripts/canonical/root-helper.ps1",
                        "action_if_reintroduced": "review",
                    }
                ],
            }
        ],
    )
    canonical = tmp_path / "scripts" / "canonical" / "root-helper.ps1"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text("echo hi\n", encoding="utf-8")

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: [])
    monkeypatch.setattr(module, "_git_path_has_history", lambda repo_root, path: False)
    monkeypatch.setattr(module, "_count_reference_hits", lambda repo_root, path: 0)

    evidence = module.collect_root_review_evidence(tmp_path)

    assert len(evidence) == 1
    assert evidence[0].rel_path == "root-helper.ps1"
    assert evidence[0].review_status == "absent_baseline_ok"
    assert evidence[0].canonical_exists is True


def test_collect_root_review_evidence_marks_present_cmp_match(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    _write_review_registry(
        tmp_path,
        [
            {
                "lane_id": "lane",
                "classification": "review_required",
                "verification": ["git ls-files foo"],
                "candidates": [
                    {
                        "path": "root-helper.ps1",
                        "current_live_state": "present_approved_root_surface",
                        "canonical_path": "scripts/canonical/root-helper.ps1",
                        "action_if_reintroduced": "review",
                    }
                ],
            }
        ],
    )
    root_copy = tmp_path / "root-helper.ps1"
    root_copy.write_text("echo hi\n", encoding="utf-8")
    canonical = tmp_path / "scripts" / "canonical" / "root-helper.ps1"
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text("echo hi\n", encoding="utf-8")

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: ["root-helper.ps1"])
    monkeypatch.setattr(module, "_git_path_has_history", lambda repo_root, path: True)
    monkeypatch.setattr(module, "_count_reference_hits", lambda repo_root, path: 3)

    evidence = module.collect_root_review_evidence(tmp_path)

    assert len(evidence) == 1
    assert evidence[0].review_status == "present_cmp_match"
    assert evidence[0].cmp_status == "match"
    assert evidence[0].tracked is True


def test_collect_root_review_evidence_marks_blocked_cleanup_retained(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    _write_review_registry(
        tmp_path,
        [
            {
                "lane_id": "retention_sensitive_boundaries",
                "classification": "blocked_cleanup_zone",
                "verification": ["git ls-files reports"],
                "candidates": [
                    {
                        "path": "reports",
                        "current_live_state": "present_blocked_cleanup_zone",
                        "canonical_path": None,
                        "action_if_reintroduced": "cleanup_only_via_retention_driven_procedure",
                    }
                ],
            }
        ],
    )
    (tmp_path / "reports").mkdir()

    monkeypatch.setattr(
        module, "_tracked_paths", lambda repo_root: ["reports/dummy.txt"]
    )
    monkeypatch.setattr(module, "_git_path_has_history", lambda repo_root, path: True)
    monkeypatch.setattr(module, "_count_reference_hits", lambda repo_root, path: 1)

    evidence = module.collect_root_review_evidence(tmp_path)

    assert len(evidence) == 1
    assert evidence[0].review_status == "blocked_cleanup_retained"
    assert evidence[0].exists is True
    assert evidence[0].tracked is True


def test_collect_root_review_evidence_marks_directory_with_tracked_descendant(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    _write_review_registry(
        tmp_path,
        [
            {
                "lane_id": "root_tooling_transitions",
                "classification": "owner_decision_required",
                "verification": ["git ls-files .vibe"],
                "candidates": [
                    {
                        "path": ".vibe",
                        "current_live_state": "present_approved_root_surface",
                        "canonical_path": ".vibe",
                        "action_if_reintroduced": "keep_with_owner_decision",
                    }
                ],
            }
        ],
    )
    (tmp_path / ".vibe").mkdir()

    monkeypatch.setattr(
        module, "_tracked_paths", lambda repo_root: [".vibe/config.toml"]
    )
    monkeypatch.setattr(module, "_git_path_has_history", lambda repo_root, path: True)
    monkeypatch.setattr(module, "_count_reference_hits", lambda repo_root, path: 1)

    evidence = module.collect_root_review_evidence(tmp_path)

    assert len(evidence) == 1
    assert evidence[0].tracked is True
    assert evidence[0].review_status == "present_owner_decision_required"


def test_collect_root_review_evidence_marks_resolved_owner_decision(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    _write_review_registry(
        tmp_path,
        [
            {
                "lane_id": "root_launcher_shims",
                "classification": "owner_decision_resolved",
                "verification": ["git ls-files codex.ps1"],
                "candidates": [
                    {
                        "path": "codex.ps1",
                        "current_live_state": "present_approved_root_surface",
                        "canonical_path": "scripts/ai/codex/run-codex.ps1",
                        "action_if_reintroduced": "retain_thin_root_launcher",
                    }
                ],
            }
        ],
    )
    (tmp_path / "codex.ps1").write_text("pwsh", encoding="utf-8")
    canonical = tmp_path / "scripts" / "ai" / "codex" / "run-codex.ps1"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("pwsh", encoding="utf-8")

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: ["codex.ps1"])
    monkeypatch.setattr(module, "_git_path_has_history", lambda repo_root, path: True)
    monkeypatch.setattr(module, "_count_reference_hits", lambda repo_root, path: 1)

    evidence = module.collect_root_review_evidence(tmp_path)

    assert len(evidence) == 1
    assert evidence[0].tracked is True
    assert evidence[0].review_status == "present_owner_decision_resolved"


def test_collect_root_review_evidence_skips_expensive_probes_for_local_only_surface(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    _write_review_registry(
        tmp_path,
        [
            {
                "lane_id": "local_runtime_root_dirs",
                "classification": "review_required",
                "verification": ["git ls-files .cache"],
                "candidates": [
                    {
                        "path": ".cache",
                        "current_live_state": "present_local_only_root_surface",
                        "canonical_path": None,
                        "action_if_reintroduced": "keep_untracked",
                    }
                ],
            }
        ],
    )
    (tmp_path / ".cache").mkdir()

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: [])
    monkeypatch.setattr(
        module,
        "_git_path_has_history",
        lambda repo_root, path: (_ for _ in ()).throw(AssertionError("history probe")),
    )
    monkeypatch.setattr(
        module,
        "_count_reference_hits",
        lambda repo_root, path: (_ for _ in ()).throw(
            AssertionError("reference probe")
        ),
    )

    evidence = module.collect_root_review_evidence(tmp_path)

    assert len(evidence) == 1
    assert evidence[0].review_status == "present_untracked_surface"
    assert evidence[0].has_history is False
    assert evidence[0].reference_hits == 0


def test_build_cleanup_classification_report_distinguishes_policy_classes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    _write_review_registry(
        tmp_path,
        [
            {
                "lane_id": "retention_sensitive_boundaries",
                "classification": "blocked_cleanup_zone",
                "verification": ["git ls-files reports"],
                "candidates": [
                    {
                        "path": "reports",
                        "current_live_state": "present_blocked_cleanup_zone",
                        "canonical_path": None,
                        "action_if_reintroduced": "cleanup_only_via_retention_driven_procedure",
                    }
                ],
            }
        ],
    )
    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(
        module, "_tracked_paths", lambda repo_root: ["reports/dummy.txt"]
    )
    monkeypatch.setattr(module, "_git_path_has_history", lambda repo_root, path: True)
    monkeypatch.setattr(module, "_count_reference_hits", lambda repo_root, path: 1)

    candidates = [
        module.CleanupCandidate(
            path=Path(".pytest_cache"),
            category="local_cache_dir",
            tracked=False,
            apply_allowed=True,
            reason="safe",
        ),
        module.CleanupCandidate(
            path=Path(".python-user/site.py"),
            category="tracked_policy_review",
            tracked=True,
            apply_allowed=False,
            reason="review",
        ),
    ]
    evidence = module.collect_root_review_evidence(tmp_path)
    report = module.build_cleanup_classification_report(
        tmp_path,
        candidates=candidates,
        review_evidence=evidence,
    )
    report_path = module.write_cleanup_classification_report(
        tmp_path,
        Path("reports/quality/cleanup.json"),
        report,
    )

    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["summary"] == {
        "BLOCKED": 1,
        "REVIEW_REQUIRED": 1,
        "SAFE": 1,
        "SECURITY_REVIEW_REQUIRED": 0,
    }
    assert loaded["cleanup_candidates"][0]["classification"] == "SAFE"
    assert loaded["root_review_evidence"][0]["classification"] == "BLOCKED"


def test_build_cleanup_classification_report_records_dry_run_safety_contract(
    tmp_path: Path,
) -> None:
    report = module.build_cleanup_classification_report(
        tmp_path,
        mode="dry-run",
        candidates=[
            module.CleanupCandidate(
                path=Path(".pytest_cache"),
                category="local_cache_dir",
                tracked=False,
                apply_allowed=True,
                reason="exact local artifact family outside blocked cleanup zones",
            )
        ],
        review_evidence=[],
    )

    assert report["mode"] == "dry-run"
    assert report["safety_contract"] == {
        "non_destructive_dry_run": True,
        "exact_candidates_only": True,
        "blocked_cleanup_zones_respected": True,
        "secret_env_files_excluded": True,
    }
    assert report["summary"]["SAFE"] == 1
    assert report["cleanup_candidates"][0]["classification"] == "SAFE"


def test_main_dry_run_report_writes_non_destructive_classification_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_governance_files(tmp_path)
    _write_review_registry(tmp_path, [])
    (tmp_path / ".pytest_cache").mkdir()
    report_path = tmp_path / "reports" / "quality" / "root-clutter.json"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "_tracked_paths", lambda _repo_root: [])
    monkeypatch.setattr(
        module, "_git_path_has_history", lambda _repo_root, _path: False
    )
    monkeypatch.setattr(module, "_count_reference_hits", lambda _repo_root, _path: 0)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "cleanup_repository.py",
            "--dry-run",
            "--no-root",
            "--detail-limit",
            "0",
            "--report-json",
            str(report_path),
        ],
    )

    assert module.main() == 0

    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["mode"] == "dry-run"
    assert loaded["safety_contract"]["non_destructive_dry_run"] is True
    assert loaded["safety_contract"]["secret_env_files_excluded"] is True
    assert loaded["cleanup_candidates"][0]["path"] == ".pytest_cache"
    assert loaded["cleanup_candidates"][0]["classification"] == "SAFE"
    assert (tmp_path / ".pytest_cache").exists()


def test_collect_root_policy_mismatches_includes_live_root_violation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    monkeypatch.setattr(
        module,
        "_tracked_paths",
        lambda repo_root: ["README.md", "pyproject.toml", "conftest.py"],
    )
    monkeypatch.setattr(
        module.root_cleanliness,
        "_load_allowed_root_files",
        lambda repo_root: frozenset({"README.md", "pyproject.toml"}),
    )
    monkeypatch.setattr(
        module.root_cleanliness,
        "_load_structure_catalog",
        lambda repo_root: {},
    )
    monkeypatch.setattr(
        module.root_cleanliness,
        "_approved_root_directories",
        lambda catalog: frozenset({"configs"}),
    )
    monkeypatch.setattr(
        module.root_cleanliness,
        "_collect_tracked_root_entries",
        lambda tracked_paths: ({"README.md", "pyproject.toml", "conftest.py"}, set()),
    )

    mismatches = module.collect_root_policy_mismatches(tmp_path)

    assert len(mismatches) == 1
    assert mismatches[0].rel_path == "conftest.py"
    assert mismatches[0].mismatch_type == "unexpected_tracked_root_file"
    assert mismatches[0].tracked is True


def test_collect_reports_workspace_evidence_marks_local_only_candidates_for_prune(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    (tmp_path / "reports" / "docs-audit").mkdir(parents=True)
    (tmp_path / "reports" / "Codex").mkdir(parents=True)
    (tmp_path / "reports" / "tmp").mkdir(parents=True)
    (tmp_path / "reports" / "test-swarm").mkdir(parents=True)
    (tmp_path / "reports" / "README.md").write_text("guide\n", encoding="utf-8")
    (tmp_path / "reports" / "documentation_merged.md").write_text(
        "merged\n",
        encoding="utf-8",
    )
    (tmp_path / "reports" / "tmp_module_dependency_map.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    quality_dir = tmp_path / "reports" / "quality"
    quality_dir.mkdir(parents=True)
    (quality_dir / "_tmp_field_level_diagnostics.csv").write_text(
        "field,value\n",
        encoding="utf-8",
    )
    _set_age_days(quality_dir / "_tmp_field_level_diagnostics.csv", days=8)
    (quality_dir / "architecture_debt_execution_plan_2026-06-01-00-00.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    _set_age_days(
        quality_dir / "architecture_debt_execution_plan_2026-06-01-00-00.json",
        days=31,
    )
    (
        quality_dir / "tasks_architecture_metric_exemptions_2026-06-01-00-00.json"
    ).write_text(
        "{}\n",
        encoding="utf-8",
    )
    _set_age_days(
        quality_dir / "tasks_architecture_metric_exemptions_2026-06-01-00-00.json",
        days=31,
    )
    (quality_dir / "duplication-baseline.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    _set_age_days(quality_dir / "duplication-baseline.json", days=31)
    (quality_dir / "contract-registry-dq-diagnostics.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    _set_age_days(quality_dir / "contract-registry-dq-diagnostics.json", days=31)
    (quality_dir / "pretest_guardrails_20260419_174602.json").write_text(
        "{}\n",
        encoding="utf-8",
    )
    _set_age_days(quality_dir / "pretest_guardrails_20260419_174602.json", days=31)
    (quality_dir / "test-runs").mkdir()
    _set_age_days(quality_dir / "test-runs", days=31)
    monkeypatch.setattr(
        module,
        "_tracked_paths",
        lambda repo_root: ["reports/README.md", "reports/test-swarm/README.md"],
    )
    monkeypatch.setattr(module, "_git_path_has_history", lambda repo_root, path: False)
    monkeypatch.setattr(module, "_count_reference_hits", lambda repo_root, path: 0)

    evidence = module.collect_reports_workspace_evidence(tmp_path)
    by_path = {row.rel_path: row for row in evidence}

    assert by_path["reports/README.md"].classification == "RETAIN"
    assert by_path["reports/test-swarm"].classification == "RETAIN"
    assert by_path["reports/Codex"].classification == "PRUNE_CANDIDATE"
    assert by_path["reports/tmp"].classification == "PRUNE_CANDIDATE"
    assert by_path["reports/docs-audit"].classification == "PRUNE_CANDIDATE"
    assert (
        by_path["reports/documentation_merged.md"].classification == "PRUNE_CANDIDATE"
    )
    assert (
        by_path["reports/tmp_module_dependency_map.json"].classification
        == "PRUNE_CANDIDATE"
    )
    assert (
        by_path["reports/quality/_tmp_field_level_diagnostics.csv"].classification
        == "PRUNE_CANDIDATE"
    )
    assert (
        by_path["reports/quality/_tmp_field_level_diagnostics.csv"].ttl_expired is True
    )
    assert (
        by_path["reports/quality/_tmp_field_level_diagnostics.csv"].retention_entry_id
        == "reports_quality_tmp_diagnostics"
    )
    assert (
        by_path["reports/quality/_tmp_field_level_diagnostics.csv"].retention_ttl_days
        == 7
    )
    assert (
        by_path[
            "reports/quality/pretest_guardrails_20260419_174602.json"
        ].classification
        == "PRUNE_CANDIDATE"
    )
    assert (
        by_path["reports/quality/pretest_guardrails_20260419_174602.json"].ttl_expired
        is True
    )
    assert (
        by_path[
            "reports/quality/pretest_guardrails_20260419_174602.json"
        ].retention_entry_id
        == "reports_quality_pretest_guardrails_history"
    )
    assert (
        by_path[
            "reports/quality/pretest_guardrails_20260419_174602.json"
        ].retention_ttl_days
        == 30
    )
    assert (
        by_path[
            "reports/quality/architecture_debt_execution_plan_2026-06-01-00-00.json"
        ].classification
        == "PRUNE_CANDIDATE"
    )
    assert (
        by_path[
            "reports/quality/tasks_architecture_metric_exemptions_2026-06-01-00-00.json"
        ].classification
        == "PRUNE_CANDIDATE"
    )
    assert by_path["reports/quality/duplication-baseline.json"].classification == (
        "PRUNE_CANDIDATE"
    )
    assert (
        by_path["reports/quality/contract-registry-dq-diagnostics.json"].classification
        == "PRUNE_CANDIDATE"
    )
    assert by_path["reports/quality/test-runs"].classification == "PRUNE_CANDIDATE"


def test_collect_reports_workspace_evidence_retains_fresh_ttl_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    quality_dir = tmp_path / "reports" / "quality"
    quality_dir.mkdir(parents=True)
    fresh_tmp = quality_dir / "_tmp_recent_diagnostics.csv"
    fresh_tmp.write_text("field,value\n", encoding="utf-8")
    fresh_guardrails = quality_dir / "pretest_guardrails_20990101_000000.json"
    fresh_guardrails.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: [])
    monkeypatch.setattr(module, "_git_path_has_history", lambda repo_root, path: False)
    monkeypatch.setattr(module, "_count_reference_hits", lambda repo_root, path: 0)

    evidence = module.collect_reports_workspace_evidence(tmp_path)
    by_path = {row.rel_path: row for row in evidence}

    assert (
        by_path["reports/quality/_tmp_recent_diagnostics.csv"].classification
        == "RETAIN"
    )
    assert by_path["reports/quality/_tmp_recent_diagnostics.csv"].ttl_expired is False
    assert (
        by_path[
            "reports/quality/pretest_guardrails_20990101_000000.json"
        ].classification
        == "RETAIN"
    )
    assert (
        by_path["reports/quality/pretest_guardrails_20990101_000000.json"].ttl_expired
        is False
    )


def test_collect_reports_workspace_evidence_skips_expensive_probes_for_local_prune_candidates(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _write_governance_files(tmp_path)
    (tmp_path / "reports" / "docs-audit").mkdir(parents=True)

    monkeypatch.setattr(module, "_tracked_paths", lambda repo_root: [])
    monkeypatch.setattr(
        module,
        "_git_path_has_history",
        lambda repo_root, path: (_ for _ in ()).throw(AssertionError("history probe")),
    )
    monkeypatch.setattr(
        module,
        "_count_reference_hits",
        lambda repo_root, path: (_ for _ in ()).throw(
            AssertionError("reference probe")
        ),
    )

    evidence = module.collect_reports_workspace_evidence(tmp_path)
    by_path = {row.rel_path: row for row in evidence}

    assert by_path["reports/docs-audit"].classification == "PRUNE_CANDIDATE"
    assert by_path["reports/docs-audit"].has_history is False
    assert by_path["reports/docs-audit"].reference_hits == 0


def test_build_root_review_and_reports_workspace_reports_include_new_sections(
    tmp_path: Path,
) -> None:
    _write_governance_files(tmp_path)
    root_review_report = module.build_root_review_evidence_report(
        tmp_path,
        mismatches=[
            module.RootPolicyMismatch(
                path=Path("conftest.py"),
                mismatch_type="unexpected_tracked_root_file",
                tracked=True,
            )
        ],
        review_evidence=[],
    )
    reports_report = module.build_reports_workspace_review_report(
        tmp_path,
        reports_evidence=[
            module.ReportsWorkspaceEvidence(
                path=Path("reports/Codex"),
                classification="PRUNE_CANDIDATE",
                tracked=False,
                exists=True,
                has_history=False,
                reference_hits=0,
                generator=None,
                commit_policy=None,
                reason="local-only",
            )
        ],
    )

    assert root_review_report["summary"]["ROOT_POLICY_MISMATCH"] == 1
    assert root_review_report["root_policy_mismatches"][0]["path"] == "conftest.py"
    assert reports_report["summary"]["PRUNE_CANDIDATE"] == 1
    assert reports_report["reports_workspace_evidence"][0]["path"] == "reports/Codex"
    assert reports_report["reports_workspace_evidence"][0]["retention_entry_id"] is None
