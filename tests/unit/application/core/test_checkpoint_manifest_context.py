"""Checkpoint identity replacement after a manifest successor."""

from __future__ import annotations

import pytest

from bioetl.application.core.lifecycle.checkpoint_manifest_context import (
    metadata_with_manifest,
    rebind_checkpoint_metadata,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

pytestmark = pytest.mark.unit


def test_metadata_with_manifest_starts_empty_checkpoint_at_zero_records() -> None:
    metadata = metadata_with_manifest(
        None,
        RunManifest(manifest_id="m2", execution_fingerprint="fp-2"),
    )

    assert metadata.records_processed == 0
    assert metadata.manifest_id == "m2"
    assert metadata.execution_fingerprint == "fp-2"


def test_rebind_checkpoint_metadata_keeps_progress_and_refreshes_context() -> None:
    current = CheckpointMetadata(
        records_processed=4,
        manifest_id="m1",
        run_context={"manifest_id": "m1", "stage": "extract"},
    )
    identity = CheckpointMetadata(
        records_processed=0,
        manifest_id="m2",
        execution_fingerprint="fp-2",
        input_snapshot_fingerprint="snap-2",
    )

    rebound = rebind_checkpoint_metadata(current, identity)

    assert rebound.records_processed == 4
    assert rebound.manifest_id == "m2"
    assert rebound.execution_fingerprint == "fp-2"
    assert rebound.run_context == {
        "manifest_id": "m2",
        "stage": "extract",
        "execution_fingerprint": "fp-2",
        "input_snapshot_fingerprint": "snap-2",
    }
