"""Split diff-focused owner tests for RunManifestInspectionService."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

pytestmark = pytest.mark.unit

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.domain.control_plane import RunSourceRef
from bioetl.domain.types import RunID, RunType
from tests.unit.application.services.test_run_manifest_inspection_service import *
from tests.unit.application.services.test_run_manifest_inspection_service import (
    _InMemoryRunManifestStore,
    _make_manifest,
    _run_id,
)


def test_diff_reports_changed_top_level_fields() -> None:
    manifest_store = _InMemoryRunManifestStore()
    left_run_id = _run_id("diff-left")
    right_run_id = _run_id("diff-right")
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=left_run_id,
        run_type=RunType.INCREMENTAL,
        config_hash="hash-left",
        limit=100,
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=right_run_id,
        run_type=RunType.REBUILD,
        config_hash="hash-right",
        limit=500,
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.diff("manifest-left", "manifest-right")

    diff_fields = {entry.field for entry in result.differences}
    assert result.left_manifest_id == "manifest-left"
    assert result.right_manifest_id == "manifest-right"
    assert result.classification == "semantic_drift"
    assert result.semantic_equivalent is False
    assert result.occurrence_only is False
    assert "run_type" in result.semantic_difference_fields
    assert "manifest_id" in diff_fields
    assert "run_id" in diff_fields
    assert "run_type" in diff_fields
    assert "launch_context" in diff_fields
    assert "runtime_config" in diff_fields
    assert "code_provenance" in diff_fields
    assert result.cross_surface_replay_diff["verdict"] == "semantic_drift"
    assert (
        result.cross_surface_replay_diff["effective_config"]["semantic_equivalent"]
        is True
    )
    assert (
        "execution_fingerprint"
        in result.cross_surface_replay_diff["checkpoint_anchors"]["mismatched_fields"]
    )


def test_diff_classifies_occurrence_only_replay_runs() -> None:
    manifest_store = _InMemoryRunManifestStore()
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000201")),
        execution_fingerprint="fingerprint-same",
        created_at=created_at,
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000202")),
        execution_fingerprint="fingerprint-same",
        created_at=created_at,
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.diff("manifest-left", "manifest-right")

    assert result.classification == "occurrence_only"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is True
    assert result.occurrence_difference_fields == ("manifest_id", "run_id")
    assert result.semantic_difference_fields == ()
    assert result.noncanonical_difference_fields == ()
    assert result.cross_surface_replay_diff["verdict"] == "occurrence_only_replay"
    assert result.cross_surface_replay_diff["checkpoint_anchors"]["compatible"] is True


def test_diff_keeps_legacy_config_hash_outside_semantic_replay_identity() -> None:
    manifest_store = _InMemoryRunManifestStore()
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    shared_fingerprint = "fingerprint-config-hash-compat"
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000221")),
        execution_fingerprint=shared_fingerprint,
        created_at=created_at,
        config_hash="a" * 64,
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000222")),
        execution_fingerprint=shared_fingerprint,
        created_at=created_at,
        config_hash="f" * 64,
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.diff("manifest-left", "manifest-right")

    assert result.classification == "semantic_equivalent_with_noncanonical_differences"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is False
    assert result.occurrence_difference_fields == ("manifest_id", "run_id")
    assert result.semantic_difference_fields == ()
    assert result.noncanonical_difference_fields == ("code_provenance",)
    assert result.cross_surface_replay_diff["verdict"] == "semantic_equivalent_replay"
    assert (
        result.cross_surface_replay_diff["effective_config"]["semantic_equivalent"]
        is True
    )
    assert result.cross_surface_replay_diff["checkpoint_anchors"]["compatible"] is True


def test_diff_classifies_semantic_equivalent_noncanonical_differences() -> None:
    manifest_store = _InMemoryRunManifestStore()
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    shared_fingerprint = "fingerprint-same"
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000203")),
        execution_fingerprint=shared_fingerprint,
        created_at=created_at,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                query="fixture://a",
            ),
            RunSourceRef(
                provider="pubchem",
                entity="activity",
                pipeline_name="chembl_activity",
                query="fixture://b",
            ),
        ),
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000204")),
        execution_fingerprint=shared_fingerprint,
        created_at=created_at,
        source_refs=tuple(reversed(left.source_refs)),
    )
    manifest_store.save(left)
    manifest_store.save(right)
    service = RunManifestInspectionService(manifest_port=manifest_store)

    result = service.diff("manifest-left", "manifest-right")

    assert result.classification == "semantic_equivalent_with_noncanonical_differences"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is False
    assert result.noncanonical_difference_fields == ("source_refs",)
    assert result.cross_surface_replay_diff["verdict"] == "semantic_equivalent_replay"
    assert result.cross_surface_replay_diff["manifest"][
        "noncanonical_difference_fields"
    ] == ["source_refs"]
