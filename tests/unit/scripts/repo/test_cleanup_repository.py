"""Unit tests for deterministic repository cleanup candidate discovery."""

from __future__ import annotations

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
                "test_support_roots": {
                    "approved_roots": [{"path": "testing_support"}],
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
