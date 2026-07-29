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


def test_hydrate_code_provenance_accepts_partial_payload() -> None:
    """Nominal path: optional provenance fields hydrate without requiring full lock."""
    h = _Hydrator()
    prov = h._hydrate_code_provenance(
        {
            "pipeline_version": "1.2.3",
            "git_commit": "abc123",
            "config_hash": "cfg",
        }
    )
    assert prov.pipeline_version == "1.2.3"
    assert prov.git_commit == "abc123"
    assert prov.config_hash == "cfg"
    assert prov.dependency_lock_hash is None


def test_hydrate_code_provenance_empty_payload_is_all_none() -> None:
    h = _Hydrator()
    prov = h._hydrate_code_provenance({})
    assert prov.pipeline_version is None
    assert prov.git_commit is None
    assert prov.config_hash is None


def test_hydrate_planned_artifacts_requires_artifact_keys() -> None:
    h = _Hydrator()
    with pytest.raises(ValueError, match="missing required key: layer"):
        h._hydrate_planned_artifacts([{"path": "only-path"}])


def test_hydrate_planned_artifacts_nominal() -> None:
    h = _Hydrator()
    arts = h._hydrate_planned_artifacts(
        [{"layer": "bronze", "path": "chembl/activity/out.jsonl"}]
    )
    assert len(arts) == 1
    assert arts[0].layer == "bronze"
    assert arts[0].path == "chembl/activity/out.jsonl"
