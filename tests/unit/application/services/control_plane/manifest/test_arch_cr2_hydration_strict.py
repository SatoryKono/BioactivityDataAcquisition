"""ARCH-CR2-02: manifest hydration fails closed on malformed payloads."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.manifest._service_hydration import (
    RunManifestHydrationMixin,
)


class _Hydrator(RunManifestHydrationMixin):
    def __init__(self) -> None:
        self._manifest_id_factory = lambda: "mid"
        self.schema_version = "1"


def test_hydrate_source_refs_rejects_non_mapping() -> None:
    h = _Hydrator()
    with pytest.raises(ValueError, match="source_refs\\[0\\] must be a mapping"):
        h._hydrate_source_refs(["not-a-dict"])  # type: ignore[list-item]


def test_hydrate_source_refs_requires_keys() -> None:
    h = _Hydrator()
    with pytest.raises(ValueError, match="missing required key: provider"):
        h._hydrate_source_refs([{"entity": "activity", "pipeline_name": "p"}])


def test_hydrate_source_refs_nominal() -> None:
    h = _Hydrator()
    refs = h._hydrate_source_refs(
        [
            {
                "provider": "chembl",
                "entity": "activity",
                "pipeline_name": "chembl_activity",
                "query": None,
                "input_snapshots": [
                    {"snapshot_id": "s1", "content_hash": "h1"},
                ],
            }
        ]
    )
    assert len(refs) == 1
    assert refs[0].provider == "chembl"
    assert refs[0].input_snapshots[0].snapshot_id == "s1"


def test_hydrate_input_snapshots_requires_content_hash() -> None:
    h = _Hydrator()
    with pytest.raises(ValueError, match="missing required key: content_hash"):
        h._hydrate_input_snapshots([{"snapshot_id": "s1"}])


def test_hydrate_planned_artifacts_rejects_non_mapping() -> None:
    h = _Hydrator()
    with pytest.raises(ValueError, match="planned_artifacts\\[0\\]"):
        h._hydrate_planned_artifacts([123])  # type: ignore[list-item]
