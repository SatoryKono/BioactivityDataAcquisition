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
