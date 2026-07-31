"""Regression tests for bounded module-coverage Git authority checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.architecture import _module_coverage_inventory_support as support


@pytest.mark.parametrize(
    ("returncodes", "expected"),
    [
        ([0, 0], False),
        ([1], True),
        ([0, 1], True),
    ],
)
def test_git_path_is_dirty_checks_unstaged_and_staged_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    returncodes: list[int],
    expected: bool,
) -> None:
    calls: list[list[str]] = []
    pending = iter(returncodes)

    def _fake_run(command: list[str], *, root: Path) -> tuple[int, str]:
        assert root == tmp_path
        calls.append(command)
        return next(pending), ""

    monkeypatch.setattr(support, "_run_git_command", _fake_run)

    assert (
        support._git_path_is_dirty("reports/inventory.json", root=tmp_path) is expected
    )
    assert calls[0][:4] == ["git", "--no-optional-locks", "diff", "--quiet"]
    if len(calls) == 2:
        assert "--cached" in calls[1]


def test_git_path_is_dirty_rejects_git_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        support,
        "_run_git_command",
        lambda command, *, root: (128, ""),
    )

    with pytest.raises(OSError, match="exit code 128"):
        support._git_path_is_dirty("reports/inventory.json", root=tmp_path)
