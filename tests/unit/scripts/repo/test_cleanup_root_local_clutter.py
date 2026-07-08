"""Unit tests for reviewed root-local clutter cleanup command."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.engineering.repo import cleanup_root_local_clutter as module


pytestmark = pytest.mark.unit


def _write_governance(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / ".github").mkdir()
    (tmp_path / ".github" / "root-allowlist.txt").write_text(
        "README.md\npyproject.toml\n",
        encoding="utf-8",
    )
    config_dir = tmp_path / "configs" / "quality"
    config_dir.mkdir(parents=True)
    (config_dir / "repo_structure_catalog.yaml").write_text(
        yaml.safe_dump(
            {
                "docs_drafts": {"allowed_files": []},
                "plans": {
                    "readme": "docs/plans/README.md",
                    "max_active_backlog": 1,
                    "allowed_files": [],
                },
                "src_sidecars": {"approved_roots": [{"path": "src/bioetl"}]},
                "blocked_cleanup_zones": [
                    {"path": "data"},
                    {"path": "reports"},
                    {"path": "docs/99-archive"},
                    {"path": "tests/fixtures"},
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (config_dir / "root_hygiene_review_registry.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0.0",
                "status": "active",
                "review_lanes": [
                    {
                        "lane_id": "local_runtime_root_dirs",
                        "classification": "review_required",
                        "verification": ["git check-ignore -v .pytest_cache"],
                        "candidates": [
                            {
                                "path": ".pytest_cache",
                                "current_live_state": "present_local_only_root_surface",
                                "canonical_path": None,
                                "action_if_reintroduced": "safe local pytest cache",
                            },
                            {
                                "path": ".mypy_cache",
                                "current_live_state": "present_local_only_root_surface",
                                "canonical_path": None,
                                "action_if_reintroduced": "safe local mypy cache",
                            },
                            {
                                "path": ".venv",
                                "current_live_state": "present_local_only_root_surface",
                                "canonical_path": "pyproject.toml",
                                "action_if_reintroduced": "local virtualenv",
                            },
                            {
                                "path": "node_modules",
                                "current_live_state": "present_local_only_root_surface",
                                "canonical_path": "package-lock.json",
                                "action_if_reintroduced": "local dependency tree",
                            },
                        ],
                    },
                    {
                        "lane_id": "root_env_security",
                        "classification": "security_review_required",
                        "verification": ["git ls-files .env"],
                        "candidates": [
                            {
                                "path": ".env",
                                "current_live_state": "present_local_only_root_surface",
                                "canonical_path": ".env.example",
                            }
                        ],
                    },
                    {
                        "lane_id": "retention_sensitive_boundaries",
                        "classification": "blocked_cleanup_zone",
                        "verification": ["data"],
                        "candidates": [
                            {
                                "path": "data",
                                "current_live_state": "present_blocked_cleanup_zone",
                                "canonical_path": None,
                            }
                        ],
                    },
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    (tmp_path / "README.md").write_text("readme\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "package-lock.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("TOKEN=\n", encoding="utf-8")


def test_collect_root_local_cleanup_candidates_excludes_env_and_opt_in_families(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_governance(tmp_path)
    for path in (".mypy_cache", ".pytest_cache", ".venv", "node_modules", ".env"):
        (tmp_path / path).mkdir()
    monkeypatch.setattr(module, "_tracked_paths", lambda _repo_root: frozenset())

    candidates = module.collect_root_local_cleanup_candidates(tmp_path)

    assert [candidate.rel_path for candidate in candidates] == [
        ".mypy_cache",
        ".pytest_cache",
    ]


def test_collect_root_local_cleanup_candidates_includes_opt_in_families(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_governance(tmp_path)
    for path in (".mypy_cache", ".pytest_cache", ".venv", "node_modules"):
        (tmp_path / path).mkdir()
    monkeypatch.setattr(module, "_tracked_paths", lambda _repo_root: frozenset())

    candidates = module.collect_root_local_cleanup_candidates(
        tmp_path,
        include_venv=True,
        include_dependency_trees=True,
    )

    assert [candidate.rel_path for candidate in candidates] == [
        ".mypy_cache",
        ".pytest_cache",
        ".venv",
        "node_modules",
    ]


def test_main_apply_deletes_only_exact_reviewed_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_governance(tmp_path)
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".env").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "_tracked_paths", lambda _repo_root: frozenset())

    assert module.main(["--apply", "--path", ".pytest_cache"]) == 0

    assert not (tmp_path / ".pytest_cache").exists()
    assert (tmp_path / ".env").exists()


def test_main_apply_continues_after_delete_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo_root = tmp_path
    monkeypatch.chdir(repo_root)
    candidates = [
        module.RootLocalCleanupCandidate(
            path=Path(".hypothesis"),
            lane_id="local_runtime_root_dirs",
            category="local_cache",
            reason="local property test cache",
        ),
        module.RootLocalCleanupCandidate(
            path=Path(".pytest_cache"),
            lane_id="local_runtime_root_dirs",
            category="local_cache",
            reason="local pytest cache",
        ),
    ]
    deleted: list[str] = []

    monkeypatch.setattr(module, "_project_root", lambda: repo_root)
    monkeypatch.setattr(
        module,
        "collect_root_local_cleanup_candidates",
        lambda *_args, **_kwargs: candidates,
    )

    def fake_delete(
        _repo_root: Path,
        candidate: module.RootLocalCleanupCandidate,
    ) -> None:
        if candidate.rel_path == ".hypothesis":
            raise OSError("invalid argument")
        deleted.append(candidate.rel_path)

    monkeypatch.setattr(module, "_delete_candidate", fake_delete)

    assert module.main(["--apply", "--json"]) == 1

    output = capsys.readouterr().out
    assert '"path": ".hypothesis"' in output
    assert '"deleted": [' in output
    assert deleted == [".pytest_cache"]
