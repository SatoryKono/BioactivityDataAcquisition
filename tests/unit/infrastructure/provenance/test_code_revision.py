"""Revision evidence distinguishes clean, dirty and unavailable Git state."""

from __future__ import annotations
import subprocess
import pytest
from bioetl.infrastructure.provenance import code_revision as revision


pytestmark = pytest.mark.unit


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
