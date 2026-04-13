"""Tests for the public composite checkpoint facade."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.checkpoint.anchor_context import (
    ExpectedCheckpointContext,
    create_expected_checkpoint_context,
    fresh_checkpoint_state,
    merge_expected_anchors,
)
from bioetl.domain.composite.state import CompositePipelineState


def test_public_facade_exports_anchor_context_helpers() -> None:
    anchors = create_expected_checkpoint_context(
        effective_config_hash=" sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
        contract_ref=" ChemBL.Activity ",
        contract_version=" v2 ",
        manifest_id=" manifest-123 ",
        composite_run_identity=" run-42 ",
    )

    assert isinstance(anchors, ExpectedCheckpointContext)
    assert anchors.effective_config_hash == (
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    assert anchors.contract_ref == "chembl.activity"
    assert anchors.contract_version == "2.0.0"


def test_public_facade_merges_runtime_anchors_into_checkpoint_state() -> None:
    anchors = create_expected_checkpoint_context(
        effective_config_hash=" sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
        contract_ref=" ChemBL.Activity ",
        contract_version=" v2 ",
        manifest_id=" manifest-123 ",
        composite_run_identity=" run-42 ",
    )
    state = CompositeCheckpointState(
        composite_name="composite_publication",
        run_id="run-1",
        state=CompositePipelineState.SEED_RUNNING,
    )

    merged = merge_expected_anchors(state, anchors)
    fresh = fresh_checkpoint_state(
        composite_name="composite_publication",
        run_id="run-2",
        anchors=anchors,
    )

    assert merged.effective_config_hash == anchors.effective_config_hash
    assert merged.contract_ref == anchors.contract_ref
    assert merged.contract_version == anchors.contract_version
    assert merged.manifest_id == "manifest-123"
    assert merged.composite_run_identity == "run-42"
    assert fresh.effective_config_hash == anchors.effective_config_hash
    assert fresh.contract_ref == anchors.contract_ref
    assert fresh.state == CompositePipelineState.NOT_STARTED
