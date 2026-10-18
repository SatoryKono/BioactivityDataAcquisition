"""Tests for deterministic repository-wide tracked file discovery helper."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import ANY, patch

import pytest

from scripts.engineering.qa._tracked_glob import (
    git_discovery_environment,
    tracked_files,
)

pytestmark = pytest.mark.unit


def test_tracked_files_includes_tracked_and_excludes_untracked(tmp_path: Path):
    """Verify standard usage: returns only tracked files matching the pattern."""
    # Setup mock git ls-files output
    tracked_list = b"file1.py\0subdir/file2.py\0"

    # Create actual files in the tmp_path
    (tmp_path / "file1.py").write_text("tracked", encoding="utf-8")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file2.py").write_text("tracked", encoding="utf-8")
    (tmp_path / "untracked.py").write_text("untracked", encoding="utf-8")
    (tmp_path / "subdir" / "untracked2.py").write_text("untracked", encoding="utf-8")

    # We need to make the tmp_path look like a git repo to bypass the fallback
    (tmp_path / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = tracked_list
        mock_run.return_value.returncode = 0

        result = tracked_files(tmp_path, "**/*.py")

        # Verify subprocess was called correctly
        mock_run.assert_called_once_with(
            ["git", "ls-files", "-z"],
            cwd=tmp_path.resolve(),
            env=ANY,
            capture_output=True,
            check=True,
            text=False,
        )

        # Verify result contains only tracked files
        expected = (
            tmp_path / "file1.py",
            tmp_path / "subdir" / "file2.py",
        )
        assert result == expected


def test_tracked_files_with_include_untracked(tmp_path: Path):
    """Verify include_untracked=True opt-out behavior."""
    (tmp_path / "file1.py").write_text("tracked", encoding="utf-8")
    (tmp_path / "untracked.py").write_text("untracked", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    # Even if we mock subprocess.run, it shouldn't be called if include_untracked=True
    with patch("subprocess.run") as mock_run:
        result = tracked_files(tmp_path, "*.py", include_untracked=True)

        mock_run.assert_not_called()

        expected = (
            tmp_path / "file1.py",
            tmp_path / "untracked.py",
        )
        assert result == tuple(sorted(expected))


def test_tracked_files_fails_closed_on_git_error(tmp_path: Path):
    """Verify fail-closed behavior when git fails."""
    (tmp_path / "file1.py").write_text("tracked", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "ls-files"])

        with pytest.raises(SystemExit) as exc_info:
            tracked_files(tmp_path, "*.py")

        assert exc_info.value.code == 1


def test_tracked_files_resolves_patterns_correctly(tmp_path: Path):
    """Verify multiple patterns are handled and sorted deterministically."""
    tracked_list = b"file_a.py\0file_b.csv\0file_c.txt\0"

    (tmp_path / "file_a.py").write_text("1", encoding="utf-8")
    (tmp_path / "file_b.csv").write_text("2", encoding="utf-8")
    (tmp_path / "file_c.txt").write_text("3", encoding="utf-8")
    (tmp_path / ".git").mkdir()

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = tracked_list
        mock_run.return_value.returncode = 0

        # Test default pattern ("*")
        result_default = tracked_files(tmp_path)
        assert len(result_default) == 3

        # Test multiple specific patterns
        result_specific = tracked_files(tmp_path, "*.py", "*.csv")
        expected = (
            tmp_path / "file_a.py",
            tmp_path / "file_b.csv",
        )
        assert result_specific == expected


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        env=git_discovery_environment(),
    )


def test_tracked_files_observes_staged_add_remove_and_rename(tmp_path: Path):
    _git(tmp_path, "init")
    original = tmp_path / "original.py"
    original.write_text("tracked", encoding="utf-8")
    assert tracked_files(tmp_path, "*.py") == ()
    _git(tmp_path, "add", "original.py")
    assert tracked_files(tmp_path, "*.py") == (original,)
    _git(tmp_path, "mv", "original.py", "renamed.py")
    renamed = tmp_path / "renamed.py"
    assert tracked_files(tmp_path, "*.py") == (renamed,)
    _git(tmp_path, "rm", "--cached", "renamed.py")
    assert renamed.exists()
    assert tracked_files(tmp_path, "*.py") == ()


def test_tracked_files_uses_each_worktree_index(tmp_path: Path):
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init")
    (main / "common.py").write_text("common", encoding="utf-8")
    _git(main, "add", "common.py")
    _git(
        main,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "core.hooksPath=/dev/null",
        "commit",
        "-m",
        "fixture",
    )
    linked = tmp_path / "linked"
    _git(main, "worktree", "add", "--detach", str(linked))
    assert (linked / ".git").is_file()
    assert tracked_files(linked, "*.py") == (linked / "common.py",)
    extra = linked / "extra.py"
    extra.write_text("extra", encoding="utf-8")
    assert tracked_files(linked, "*.py") == (linked / "common.py",)
    _git(linked, "add", "extra.py")
    assert tracked_files(linked, "*.py") == (linked / "common.py", extra)
    assert tracked_files(main, "*.py") == (main / "common.py",)


@pytest.mark.parametrize(
    "pattern",
    [
        "*",
        "*.py",
        "**/*.py",
        "**",
        "sub/**",
        "./*.py",
        "sub/",
        "sub/**/*.py",
        "**/sub/**/a?.py",
        "[ab]*.py",
        "**/*",
    ],
)
def test_index_matcher_agrees_with_pathlib(tmp_path: Path, pattern: str):
    _git(tmp_path, "init")
    for name in ("a.py", "b.txt", ".hidden.py", "sub/a1.py", "sub/deep/a2.py"):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture")
    _git(tmp_path, "add", ".")
    expected = tuple(
        sorted(
            p for p in tmp_path.glob(pattern) if p.is_file() and ".git" not in p.parts
        )
    )
    assert tracked_files(tmp_path, pattern) == expected


def test_discovery_never_scans_ignored_tree(tmp_path: Path, monkeypatch):
    _git(tmp_path, "init")
    (tmp_path / "a.py").write_text("fixture")
    _git(tmp_path, "add", "a.py")

    def forbidden(*args, **kwargs):
        raise AssertionError("filesystem traversal is forbidden")

    monkeypatch.setattr(Path, "glob", forbidden)
    monkeypatch.setattr(Path, "rglob", forbidden)
    assert tracked_files(tmp_path, "**/*.py") == (tmp_path / "a.py",)


def test_discovery_ignores_foreign_git_location(tmp_path: Path, monkeypatch):
    own, foreign = tmp_path / "own", tmp_path / "foreign"
    foreign.mkdir()
    _git(foreign, "init")
    (foreign / "foreign.py").write_text("fixture")
    _git(foreign, "add", "foreign.py")
    foreign_index = (foreign / ".git/index").read_bytes()
    monkeypatch.setenv("GIT_DIR", str(foreign / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(foreign))
    monkeypatch.setenv("GIT_INDEX_FILE", str(foreign / ".git/index"))
    own.mkdir()
    _git(own, "init")
    (own / "own.py").write_text("fixture")
    _git(own, "add", "own.py")
    assert (foreign / ".git/index").read_bytes() == foreign_index
    assert tracked_files(own, "*.py") == (own / "own.py",)


def test_suppression_inventory_paths_are_portable(tmp_path: Path):
    from scripts.engineering.qa.report_basedpyright_suppression_inventory import collect

    _git(tmp_path, "init")
    product = tmp_path / "src/bioetl"
    product.mkdir(parents=True)
    (product / "a.py").write_text("# pyright: ignore[reportUnknownMemberType]\n")
    _git(tmp_path, "add", ".")
    result = collect(product)
    assert result["product_root"] == "src/bioetl"
    assert result["files_list"] == ["src/bioetl/a.py"]


def test_singleton_metric_document_obeys_index(tmp_path: Path, monkeypatch):
    from scripts.engineering.qa import observability_metric_inventory_report as report

    _git(tmp_path, "init")
    document = tmp_path / "grafana/README.md"
    document.parent.mkdir()
    document.write_text("bioetl_pipeline_duration_seconds")
    monkeypatch.setattr(report, "_DOC_SCAN_ROOTS", (Path("grafana/README.md"),))
    assert report._scan_documented_metrics_from_docs(tmp_path) == set()
    _git(tmp_path, "add", ".")
    assert (
        "bioetl_pipeline_duration_seconds"
        in report._scan_documented_metrics_from_docs(tmp_path)
    )
    _git(tmp_path, "rm", "--cached", "grafana/README.md")
    assert report._scan_documented_metrics_from_docs(tmp_path) == set()
