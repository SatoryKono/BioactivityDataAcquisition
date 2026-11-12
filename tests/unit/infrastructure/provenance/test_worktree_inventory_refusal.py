"""Failed Git discovery is unknown, never an authoritative empty inventory."""

from __future__ import annotations

from subprocess import CompletedProcess
import pytest
from bioetl.infrastructure.provenance import code_revision as subject

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "result", [None, CompletedProcess(["git"], 1, stdout="", stderr="fixture failure")]
)
def test_failed_git_file_discovery_does_not_report_an_empty_tree(
    monkeypatch, tmp_path, result
):
    monkeypatch.setattr(subject, "_run_git_command", lambda *args, **kwargs: result)
    assert subject.list_git_worktree_files(tmp_path, "src") is None
