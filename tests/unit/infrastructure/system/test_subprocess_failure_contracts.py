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
