"""Revision evidence distinguishes clean, dirty and unavailable Git state."""

from __future__ import annotations
import subprocess
import pytest
from bioetl.infrastructure.provenance import code_revision as revision
from bioetl.infrastructure.system.subprocess_boundary import _copy_env


pytestmark = pytest.mark.unit


def test_copy_env_preserves_empty_environment() -> None:
    assert _copy_env(None) is None
    assert _copy_env({}) == {}


@pytest.mark.parametrize(
    "returncode,expected", [(0, "clean"), (1, "dirty"), (128, "dirty_state_unknown")]
)
def test_revision_state_preserves_git_failure_provenance(
    monkeypatch, returncode, expected
):
    revision.get_code_revision_provenance.cache_clear()
    monkeypatch.setattr(revision, "get_git_commit", lambda: "a" * 40)
    monkeypatch.setattr(revision, "get_dependency_lock_hash", lambda: "sha256:lock")
    monkeypatch.setattr(
        revision,
        "_run_git_command",
        lambda *args, **kwargs: subprocess.CompletedProcess(args, returncode, "", ""),
    )
    try:
        result = revision.get_code_revision_provenance()
        assert result.source_revision_state == expected
        assert result.git_commit == "a" * 40
        assert result.dependency_lock_hash == "sha256:lock"
    finally:
        revision.get_code_revision_provenance.cache_clear()


def test_config_hash_is_order_independent_but_preserves_sequence_order():
    assert revision.compute_config_hash(
        {"b": 2, "a": 1}
    ) == revision.compute_config_hash({"a": 1, "b": 2})
    assert revision.compute_config_hash(
        {"values": [1, 2]}
    ) != revision.compute_config_hash({"values": [2, 1]})


@pytest.mark.parametrize(
    "result", [None, subprocess.CompletedProcess([], 128, "", "not a repository")]
)
def test_git_file_inventory_marks_failed_git_as_unavailable(
    monkeypatch, tmp_path, result
):
    monkeypatch.setattr(revision, "_run_git_command", lambda *a, **k: result)
    assert revision.list_git_worktree_files(tmp_path, "src") is None


@pytest.mark.parametrize("failure", ["timeout", "spawn"])
def test_windows_process_tree_cleanup_stays_bounded_when_taskkill_fails(
    monkeypatch, failure
):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from bioetl.infrastructure.system import subprocess_boundary as subject

    real_subprocess = subprocess
    proc = Mock(pid=123)
    killer = Mock()
    killer.wait.side_effect = real_subprocess.TimeoutExpired("taskkill", 0.5)
    popen = Mock(return_value=killer)
    if failure == "spawn":
        popen.side_effect = OSError("taskkill unavailable")
    monkeypatch.setattr(subject, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        subject, "shutil", SimpleNamespace(which=lambda _: "taskkill.exe")
    )
    monkeypatch.setattr(
        subject,
        "subprocess",
        SimpleNamespace(
            Popen=popen, DEVNULL=-3, TimeoutExpired=real_subprocess.TimeoutExpired
        ),
    )
    assert subject._terminate_process_tree(proc) is False
    proc.kill.assert_called_once_with()
    assert popen.call_args.args[0] == ["taskkill.exe", "/PID", "123", "/T", "/F"]
    if failure == "timeout":
        killer.kill.assert_called_once_with()
