"""Selected-run IO stays bounded, deterministic, and uncached."""

from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Lock
from unittest.mock import Mock

import pytest

from bioetl.domain.control_plane import ControlPlaneArtifactSurface
from bioetl.infrastructure.control_plane import _file_artifact_lifecycle_refs as refs
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import (
    _ProtectedRefs,
)

pytestmark = pytest.mark.unit


def test_selected_reads_overlap_preserve_results_and_refresh_files(
    tmp_path, monkeypatch
):
    paths = [tmp_path / f"{i}.json" for i in reversed(range(4))]
    for path in paths:
        path.write_text('{"created_at":"2026-09-15T00:00:00+00:00"}')
    candidates = [(ControlPlaneArtifactSurface.LINEAGE, path) for path in paths]
    monkeypatch.setattr(refs, "_manifest_candidate_paths", lambda *_: candidates)
    protected = _ProtectedRefs(
        **{field.name: frozenset() for field in fields(_ProtectedRefs)}
    )
    cutoff = datetime(2026, 9, 1, tzinfo=UTC)
    original = refs.build_artifact_ref
    expected = tuple(
        sorted(
            (
                original(surface=s, path=p, cutoff=cutoff, protected_refs=protected)
                for s, p in candidates
            ),
            key=lambda ref: (ref.surface.value, ref.path),
        )
    )
    barrier, lock = Barrier(4), Lock()
    active = 0
    peak = 0

    def overlapping_read(**kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        try:
            barrier.wait(timeout=5)
            return original(**kwargs)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(refs, "build_artifact_ref", overlapping_read)
    args = {
        "base_path": tmp_path,
        "cutoff": cutoff,
        "protected_refs": protected,
        "manifest": Mock(),
    }
    first, issues = refs.plan_manifest_artifact_refs(**args)
    assert first == expected
    assert issues == ()
    assert peak == 4
    assert active == 0
    paths[0].write_text('{"created_at":"2020-01-01T00:00:00+00:00"}')
    second, _ = refs.plan_manifest_artifact_refs(**args)
    assert next(ref for ref in second if ref.path == str(paths[0])).delete_selected
    assert not next(ref for ref in first if ref.path == str(paths[0])).delete_selected


def test_selected_read_error_is_not_silently_omitted(tmp_path: Path, monkeypatch):
    path = tmp_path / "artifact.json"
    path.write_text("{}")
    monkeypatch.setattr(
        refs,
        "_manifest_candidate_paths",
        lambda *_: [(ControlPlaneArtifactSurface.LINEAGE, path)],
    )
    monkeypatch.setattr(
        refs, "build_artifact_ref", Mock(side_effect=OSError("read failed"))
    )
    with pytest.raises(OSError, match="read failed"):
        refs.plan_manifest_artifact_refs(
            base_path=tmp_path,
            cutoff=datetime.now(UTC),
            protected_refs=Mock(),
            manifest=Mock(),
        )
