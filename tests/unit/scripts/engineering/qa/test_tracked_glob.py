"""Tests for deterministic repository-wide tracked file discovery helper."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.engineering.qa._tracked_glob import _get_tracked_paths, tracked_files

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def clear_tracked_paths_cache():
    """Ensure the cache is cleared between tests."""
    _get_tracked_paths.cache_clear()


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
