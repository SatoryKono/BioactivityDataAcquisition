# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Regression tests for the ADR enforcement matrix scanner."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.engineering.qa._tracked_glob import git_discovery_environment

from scripts.engineering.qa import report_adr_enforcement_matrix as matrix

pytestmark = pytest.mark.unit


def test_git_grep_uses_posix_ere_digit_class(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The git-grep ERE must not use the unsupported ``\\d`` shorthand."""
    captured_command: list[str] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        captured_command.extend(command)
        return subprocess.CompletedProcess(command, 1, stdout="", stderr="")

    monkeypatch.setattr(matrix.subprocess, "run", fake_run)

    assert matrix._git_grep_reference_lines(tmp_path) == []
    assert matrix._GIT_ADR_REFERENCE_PATTERN in captured_command
    assert "--no-color" in captured_command
    assert r"ADR-\d{3}" not in captured_command


@pytest.mark.parametrize("backend", ["git", "rg", "python"])
def test_reference_index_excludes_untracked_for_every_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, backend: str
) -> None:
    subprocess.run(
        ["git", "init", str(tmp_path)],
        check=True,
        capture_output=True,
        env=git_discovery_environment(),
    )
    tests = tmp_path / "tests"
    tests.mkdir()
    tracked = tests / "tracked.py"
    tracked.write_text("# ADR-004\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(tmp_path), "add", "."],
        check=True,
        env=git_discovery_environment(),
    )
    (tests / "untracked.py").write_text("# ADR-004\n", encoding="utf-8")
    if backend != "git":
        monkeypatch.setattr(matrix, "_git_grep_reference_lines", lambda _root: None)
    if backend == "python":
        monkeypatch.setattr(matrix, "_ripgrep_reference_lines", lambda _root: None)
    paths, _exceptions = matrix._reference_index(tmp_path)
    assert paths["ADR-004"] == {"tests/tracked.py"}
    subprocess.run(
        ["git", "-C", str(tmp_path), "rm", "--cached", "tests/tracked.py"],
        check=True,
        env=git_discovery_environment(),
    )
    assert matrix._reference_index(tmp_path)[0] == {}
