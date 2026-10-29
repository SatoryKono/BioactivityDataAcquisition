"""Revision evidence distinguishes clean, dirty and unavailable Git state."""

from __future__ import annotations
import subprocess
import sys
import shutil
import pytest
from bioetl.infrastructure.provenance import code_revision as revision


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "returncode,expected", [(0, "clean"), (1, "dirty"), (128, "dirty_state_unknown")]
)
def test_revision_state_preserves_git_failure_provenance(
    monkeypatch, returncode, expected
):
    run_git = revision._run_git_command
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
    # A Git filename/diagnostic may contain non-UTF-8 bytes on POSIX. Exercise
    # the real subprocess decoder without creating platform-specific filenames.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(shutil, "which", lambda _name: sys.executable)
        decoded = run_git(
            "-I",
            "-c",
            "import sys; sys.stdout.buffer.write(b'file_\\xff.md\\x00')",
            environment={},
        )
    assert decoded is not None and decoded.returncode == 0
    assert (
        decoded.stdout.encode("utf-8", errors="surrogateescape") == b"file_\xff.md\x00"
    )


def test_config_hash_is_order_independent_but_preserves_sequence_order():
    assert revision.compute_config_hash(
        {"b": 2, "a": 1}
    ) == revision.compute_config_hash({"a": 1, "b": 2})
    assert revision.compute_config_hash(
        {"values": [1, 2]}
    ) != revision.compute_config_hash({"values": [2, 1]})
