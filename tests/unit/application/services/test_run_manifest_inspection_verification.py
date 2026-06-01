"""Focused tests for pure run-manifest inspection verification helpers."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from bioetl.application.services.control_plane.manifest.inspection_verification import (
    build_effective_config_store_verification,
    json_equal,
    parse_run_id,
    resolve_cross_surface_replay_verdict,
    resolve_verify_verdict,
)
from bioetl.domain.types import RunID
from tests.unit.application.services.run_manifest_test_support import (
    FIXED_TIME,
    RunManifestOverrides,
    VALID_EFFECTIVE_CONFIG_HASH,
    build_default_source_refs,
    make_run_manifest,
)

TEST_ROOT = Path(__file__).resolve().parents[3] / "fixtures"
BRONZE_BATCH_URI = (TEST_ROOT / "bronze" / "batch_1.jsonl.zst").as_uri()


class _EffectiveConfigStore:
    def __init__(self) -> None:
        self._artifacts_by_run_id: dict[RunID, dict[str, object]] = {}
        self._occurrences_by_run_id: dict[RunID, dict[str, object]] = {}

    def save(
        self,
        *,
        artifact_id: str,
        run_id: RunID,
        payload: dict[str, object],
        occurrence: dict[str, object] | None = None,
    ) -> None:
        self._artifacts_by_run_id[run_id] = {"artifact_id": artifact_id, **payload}
        self._occurrences_by_run_id[run_id] = occurrence or {
            "artifact_id": artifact_id,
            "run_id": str(run_id),
        }

    def get_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        return self._artifacts_by_run_id.get(run_id)

    def get_occurrence_by_run_id(self, run_id: RunID) -> dict[str, object] | None:
        return self._occurrences_by_run_id.get(run_id)

    def diff_occurrences_by_run_id(
        self,
        left_run_id: RunID,
        right_run_id: RunID,
    ) -> dict[str, object]:
        left_artifact = self.get_by_run_id(left_run_id)
        right_artifact = self.get_by_run_id(right_run_id)
        left_occurrence = self.get_occurrence_by_run_id(left_run_id)
        right_occurrence = self.get_occurrence_by_run_id(right_run_id)
        differences: list[dict[str, object]] = []
        semantic_equivalent = left_artifact == right_artifact
        if left_occurrence != right_occurrence:
            differences.append(
                {
                    "field": "occurrence_envelope",
                    "left": left_occurrence,
                    "right": right_occurrence,
                }
            )
        return {
            "left_run_id": str(left_run_id),
            "right_run_id": str(right_run_id),
            "left_artifact_present": left_artifact is not None,
            "right_artifact_present": right_artifact is not None,
            "left_occurrence_present": left_occurrence is not None,
            "right_occurrence_present": right_occurrence is not None,
            "semantic_equivalent": semantic_equivalent,
            "occurrence_only": semantic_equivalent and bool(differences),
            "differences": differences,
        }


def _make_manifest(*, run_id: RunID, artifact_id: str) -> object:
    return make_run_manifest(
        manifest_id=f"manifest-{artifact_id}",
        run_id=run_id,
        created_at=FIXED_TIME,
        source_refs=build_default_source_refs(
            bronze_batch_uri=BRONZE_BATCH_URI,
        ),
        overrides=RunManifestOverrides(
            effective_config_artifact_id=artifact_id,
            effective_config_hash=VALID_EFFECTIVE_CONFIG_HASH,
        ),
    )


def test_parse_run_id_returns_none_for_invalid_identifier() -> None:
    assert parse_run_id("not-a-uuid") is None


def test_json_equal_normalizes_key_order() -> None:
    assert json_equal({"b": 1, "a": [2, 3]}, {"a": [2, 3], "b": 1}) is True


def test_resolve_replay_verdict_prioritizes_semantic_drift() -> None:
    assert (
        resolve_cross_surface_replay_verdict(
            semantic_equivalent=False,
            occurrence_only=False,
            checkpoint_compatible=True,
        )
        == "semantic_drift"
    )
    assert (
        resolve_verify_verdict(
            manifest_classification="semantic_drift",
            manifest_semantic_equivalent=False,
            effective_config_semantic_equivalent=True,
            missing_evidence=(),
            occurrence_only=False,
        )
        == "semantic_drift"
    )


def test_build_effective_config_store_verification_tracks_occurrence_only_diff() -> (
    None
):
    left_run_id = RunID(uuid4())
    right_run_id = RunID(uuid4())
    left_manifest = _make_manifest(run_id=left_run_id, artifact_id="artifact-1")
    right_manifest = replace(left_manifest, run_id=right_run_id)

    store = _EffectiveConfigStore()
    payload = {
        "semantic_artifact": {
            "artifact_id": "artifact-1",
            "effective_config_hash": VALID_EFFECTIVE_CONFIG_HASH,
        }
    }
    store.save(
        artifact_id="artifact-1",
        run_id=left_run_id,
        payload=payload,
        occurrence={"artifact_id": "artifact-1", "run_id": str(left_run_id)},
    )
    store.save(
        artifact_id="artifact-1",
        run_id=right_run_id,
        payload=payload,
        occurrence={"artifact_id": "artifact-1", "run_id": str(right_run_id)},
    )

    result = build_effective_config_store_verification(
        store,
        left_manifest=left_manifest,
        right_manifest=right_manifest,
    )

    assert result["available"] is True
    assert result["semantic_equivalent"] is True
    assert result["occurrence_only"] is True
    assert result["missing_evidence"] == []
    assert result["anchor_matches"] == {
        "left_artifact_id": True,
        "right_artifact_id": True,
        "left_effective_config_hash": True,
        "right_effective_config_hash": True,
    }


def test_build_effective_config_store_verification_reports_missing_store() -> None:
    run_id = RunID(uuid4())
    manifest = _make_manifest(run_id=run_id, artifact_id="artifact-1")

    result = build_effective_config_store_verification(
        None,
        left_manifest=manifest,
        right_manifest=manifest,
    )

    assert result == {
        "available": False,
        "semantic_equivalent": False,
        "occurrence_only": False,
        "missing_evidence": ["effective_config_store_unconfigured"],
    }
