"""Cleanup eligibility rejects a candidate removed after planning."""

from __future__ import annotations

import pytest
from bioetl.infrastructure.storage.bronze import cleanup_support as subject

pytestmark = pytest.mark.unit


def test_fallback_eligibility_rejects_missing_planned_candidate(monkeypatch, tmp_path):
    path = tmp_path / "candidate"
    path.write_bytes(b"synthetic fixture")
    expected = path.lstat()
    path.unlink()
    monkeypatch.setattr(subject, "destructive_cleanup_supported", lambda root: False)
    assert (
        subject.candidate_is_safe(
            path, tmp_path.absolute(), tmp_path.resolve(), expected
        )
        is False
    )
