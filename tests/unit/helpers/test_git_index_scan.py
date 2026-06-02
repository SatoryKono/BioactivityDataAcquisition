"""Unit tests for Git-index scan helpers."""

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any

import pytest

from tests.helpers import git_index_scan


pytestmark = pytest.mark.unit


def test_git_grep_fixed_retries_batched_pathspecs_before_filesystem_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if len(calls) == 1:
            return subprocess.CompletedProcess(command, 4294967295, "", "")
        if ":(glob)src/**/*.py" in command:
            return subprocess.CompletedProcess(
                command,
                0,
                "src/example.py:7:legacy-wrapper-marker\n",
                "",
            )
        return subprocess.CompletedProcess(command, 1, "", "")

    def fail_filesystem_fallback(
        **_kwargs: Any,
    ) -> tuple[git_index_scan.GitGrepMatch, ...]:
        raise AssertionError(
            "filesystem fallback should not run after batched git grep"
        )

    monkeypatch.setattr(git_index_scan.subprocess, "run", fake_run)
    monkeypatch.setattr(
        git_index_scan,
        "_filesystem_grep_fixed",
        fail_filesystem_fallback,
    )

    matches = git_index_scan.git_grep_fixed(
        root=tmp_path,
        patterns=("legacy-wrapper-marker",),
        paths=("src", "tests"),
        suffixes=(".py", ".md"),
        timeout=1.0,
    )

    assert matches == (
        git_index_scan.GitGrepMatch(
            path="src/example.py",
            line_number="7",
            text="legacy-wrapper-marker",
        ),
    )
    assert len(calls) == 5
    assert calls[0].count("--") == 1
    assert calls[1].count("--") == 1


def test_git_grep_fixed_retries_batched_pathspecs_after_broad_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(
        command: list[str], **_kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(command, timeout=1.0)
        return subprocess.CompletedProcess(command, 1, "", "")

    def fail_filesystem_fallback(
        **_kwargs: Any,
    ) -> tuple[git_index_scan.GitGrepMatch, ...]:
        raise AssertionError("filesystem fallback should not run after clean batches")

    monkeypatch.setattr(git_index_scan.subprocess, "run", fake_run)
    monkeypatch.setattr(
        git_index_scan,
        "_filesystem_grep_fixed",
        fail_filesystem_fallback,
    )

    matches = git_index_scan.git_grep_fixed(
        root=tmp_path,
        patterns=("legacy-wrapper-marker",),
        paths=("src", "tests"),
        suffixes=(".py",),
        timeout=1.0,
    )

    assert matches == ()
    assert len(calls) == 3
