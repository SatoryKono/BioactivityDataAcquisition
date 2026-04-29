"""Unit tests for deterministic repository cleanup candidate discovery."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.ops.support.repo import cleanup_repository as module


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
    assert loaded["summary"] == {"BLOCKED": 1, "REVIEW_REQUIRED": 1, "SAFE": 1}
    assert loaded["cleanup_candidates"][0]["classification"] == "SAFE"
    assert loaded["root_review_evidence"][0]["classification"] == "BLOCKED"
