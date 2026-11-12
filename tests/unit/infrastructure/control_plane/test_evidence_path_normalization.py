"""Win32 extended-length syntax preserves its logical containment path."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import pytest
from bioetl.infrastructure.control_plane import evidence_location_path_safety as subject

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "raw,expected",
    [
        (r"\\?\UNC\server\share\folder", r"\\server\share\folder"),
        (r"\\?\C:\evidence", r"C:\evidence"),
        (r"C:\evidence", r"C:\evidence"),
    ],
)
def test_extended_path_normalization_does_not_change_the_containment_identity(
    monkeypatch, raw, expected
):
    monkeypatch.setattr(subject, "os", SimpleNamespace(name="nt"))
    assert subject._normalize_resolved_path(Path(raw)) == Path(expected)
