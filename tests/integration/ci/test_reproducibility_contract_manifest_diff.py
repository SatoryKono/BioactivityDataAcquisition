"""Split manifest-diff owner tests for the reproducibility contract suite."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.domain.types import RunID
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from tests.integration.ci.test_reproducibility_contract_suite import (
    _InMemoryRunManifestStore,
    _make_manifest,
)

pytestmark = pytest.mark.integration


def test_reproducibility_contract_manifest_diff_classifies_occurrence_only() -> None:
    store = _InMemoryRunManifestStore()
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000301")),
        execution_fingerprint="fp-stable",
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000302")),
        execution_fingerprint="fp-stable",
    )
    store.save(left)
    store.save(right)

    result = RunManifestInspectionService(manifest_port=store).diff(
        "manifest-left",
        "manifest-right",
    )

    assert result.classification == "occurrence_only"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is True
    assert result.occurrence_difference_fields == ("manifest_id", "run_id")


def test_reproducibility_contract_manifest_diff_treats_created_at_as_occurrence_only() -> (
    None
):
    store = _InMemoryRunManifestStore()
    left = _make_manifest(
        manifest_id="manifest-left-created-at",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000316")),
        execution_fingerprint="fp-created-at-stable",
    )
    right = replace(
        left,
        manifest_id="manifest-right-created-at",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000317")),
        created_at=datetime(2025, 1, 2, tzinfo=UTC),
    )
    store.save(left)
    store.save(right)

    result = RunManifestInspectionService(manifest_port=store).diff(
        "manifest-left-created-at",
        "manifest-right-created-at",
    )

    assert result.classification == "occurrence_only"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is True
    assert result.occurrence_difference_fields == (
        "created_at",
        "manifest_id",
        "run_id",
    )


def test_reproducibility_contract_manifest_diff_classifies_semantic_drift() -> None:
    store = _InMemoryRunManifestStore()
    left = _make_manifest(
        manifest_id="manifest-left",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000303")),
        execution_fingerprint="fp-left",
        config_hash="hash-left",
    )
    right = _make_manifest(
        manifest_id="manifest-right",
        run_id=RunID(UUID("00000000-0000-0000-0000-000000000304")),
        execution_fingerprint="fp-right",
        config_hash="hash-right",
    )
    store.save(left)
    store.save(right)

    result = RunManifestInspectionService(manifest_port=store).diff(
        "manifest-left",
        "manifest-right",
    )

    assert result.classification == "semantic_drift"
    assert result.semantic_equivalent is False
    assert "code_provenance" in result.semantic_difference_fields


def test_reproducibility_contract_strict_resume_rejects_incomplete_legacy_checkpoint_metadata() -> (
    None
):
    """Hydrated legacy checkpoint payloads must fail closed in strict resume."""
    service = CheckpointCompatibilityService(logger=MagicMock())
    current = CheckpointMetadata(
        records_processed=1000,
        dq_contract_compatibility_hash="same-hash",
        pipeline_version="1.0.0",
        execution_fingerprint="fp-current",
        manifest_id="manifest-current",
        effective_config_hash="a" * 64,
        effective_config_artifact_id="eca-current",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        git_commit="b" * 40,
        exact_replay=True,
        input_snapshot_ids=("snapshot-a",),
    )
    checkpoint = CheckpointMetadata.from_legacy_metadata(
        {
            "records_processed": 500,
            "execution_fingerprint": "fp-current",
            "manifest_id": "manifest-current",
            "effective_config_hash": "a" * 64,
            "effective_config_artifact_id": "eca-current",
            "contract_ref": "chembl.activity",
            "contract_version": "1.0.0",
            "git_commit": "b" * 40,
            "exact_replay": True,
        }
    )

    result = service.validate_checkpoint_compatibility(current, checkpoint)

    assert result.compatible is False
    assert result.execution_identity_compatible is False
    assert result.identity_continuity_proven is False
    assert any(
        "checkpoint_missing_required_execution_anchor" in message
        for message in result.messages
    )
    assert any(
        "checkpoint_missing_snapshot_anchor" in message for message in result.messages
    )


def test_reproducibility_contract_manifest_diff_exposes_exact_replay_parentage() -> (
    None
):
    store = _InMemoryRunManifestStore()
    parent_run_id = RunID(UUID("00000000-0000-0000-0000-000000000305"))
    child_run_id = RunID(UUID("00000000-0000-0000-0000-000000000306"))
    parent = _make_manifest(
        manifest_id="manifest-parent",
        run_id=parent_run_id,
        execution_fingerprint="fp-stable",
    )
    child = _make_manifest(
        manifest_id="manifest-child",
        run_id=child_run_id,
        execution_fingerprint="fp-stable",
        replay_of_run_id=str(parent_run_id),
        replay_of_manifest_id="manifest-parent",
    )
    store.save(parent)
    store.save(child)

    result = RunManifestInspectionService(manifest_port=store).diff(
        "manifest-parent",
        "manifest-child",
    )

    assert result.classification == "semantic_equivalent_with_noncanonical_differences"
    assert result.semantic_equivalent is True
    assert result.occurrence_only is False
    assert result.replay_relationship == "right_is_exact_replay_of_left"
    assert "replay_of_manifest_id" in result.noncanonical_difference_fields
