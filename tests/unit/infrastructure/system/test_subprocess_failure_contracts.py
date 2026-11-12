"""Protected subprocesses preserve failures, copy env and report cleanup limits."""

from __future__ import annotations

import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock, sentinel
import pytest
from bioetl.infrastructure.system import subprocess_boundary as subject

pytestmark = pytest.mark.unit


def test_nonzero_child_retains_captured_streams_in_called_process_error():
    with pytest.raises(subprocess.CalledProcessError) as caught:
        subject.run_protected_command(
            [
                sys.executable,
                "-c",
                "import sys; print('fixture-out'); sys.stderr.write('fixture-error'); sys.exit(3)",
            ],
            env={},
            timeout=5,
            capture_output=True,
            check=True,
            text=True,
        )
    assert caught.value.returncode == 3
    assert caught.value.stdout.strip() == "fixture-out"
    assert caught.value.stderr == "fixture-error"


@pytest.mark.parametrize("output,expected", [(None, 0), (b"abc", 3), ("я", 2)])
def test_output_limit_counts_encoded_bytes_and_missing_streams(output, expected):
    assert subject._output_size(output, encoding="utf-8", errors=None) == expected


def test_popen_boundary_copies_explicit_environment_and_disables_shell(monkeypatch):
    popen = Mock(return_value=sentinel.child)
    monkeypatch.setattr(subject.subprocess, "Popen", popen)
    environment = {"SYNTHETIC_FIXTURE": "value"}
    assert (
        subject.run_protected_subprocess_popen(["fixture-python"], env=environment)
        is sentinel.child
    )
    assert popen.call_args.kwargs["env"] == environment
    assert popen.call_args.kwargs["env"] is not environment
    assert popen.call_args.kwargs["shell"] is False


def test_windows_without_taskkill_does_not_claim_descendant_cleanup(monkeypatch):
    process = Mock(pid=123)
    monkeypatch.setattr(subject, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(subject.shutil, "which", lambda command: None)
    assert subject._terminate_process_tree(process) is False
    process.kill.assert_called_once_with()


@pytest.mark.parametrize("available", [False, True])
def test_posix_tree_cleanup_reports_only_confirmed_group_kill(monkeypatch, available):
    process = Mock(pid=123)
    group_kill = Mock()
    platform = SimpleNamespace(name="posix")
    if available:
        platform.killpg = group_kill
    monkeypatch.setattr(subject, "os", platform)
    monkeypatch.setattr(subject, "signal", SimpleNamespace(SIGKILL=9))
    assert subject._terminate_process_tree(process) is available
    if available:
        group_kill.assert_called_once_with(123, 9)
        process.kill.assert_not_called()
    else:
        process.kill.assert_called_once_with()


@pytest.mark.parametrize("failure", [None, "nonzero", "timeout", "spawn"])
def test_windows_taskkill_failure_still_kills_direct_child(monkeypatch, failure):
    process = Mock(pid=123)
    killer = Mock()
    killer.wait.return_value = 1 if failure == "nonzero" else 0
    if failure == "timeout":
        killer.wait.side_effect = subprocess.TimeoutExpired("fixture-taskkill", 0.5)
    start = Mock(return_value=killer)
    if failure == "spawn":
        start.side_effect = OSError("fixture spawn failure")
    monkeypatch.setattr(subject, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(subject.shutil, "which", lambda command: "fixture-taskkill")
    monkeypatch.setattr(subject.subprocess, "Popen", start)
    assert subject._terminate_process_tree(process) is (failure is None)
    process.kill.assert_called_once_with()
    if failure == "timeout":
        killer.kill.assert_called_once_with()
    assert start.call_args.kwargs["shell"] is False


@pytest.mark.parametrize("tree_terminated", [False, True])
def test_cleanup_preserves_unconfirmed_descendant_streams_and_retries_wait(
    monkeypatch, tree_terminated
):
    process = Mock()
    process.wait.side_effect = subprocess.TimeoutExpired("fixture-child", 0.5)
    terminate = Mock(return_value=tree_terminated)
    monkeypatch.setattr(subject, "_terminate_process_tree", terminate)
    subject._cleanup_process(process)
    assert terminate.call_count == 2
    process.stdin.close.assert_called_once_with()
    assert process.stdout.close.called is tree_terminated
    assert process.stderr.close.called is tree_terminated
