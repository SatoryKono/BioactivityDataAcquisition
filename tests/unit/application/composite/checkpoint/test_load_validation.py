"""Unit tests for composite checkpoint resume-anchor validation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
)
from bioetl.application.composite.checkpoint._load_validation import (
    validate_resume_compatibility,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import CheckpointConflictError

pytestmark = pytest.mark.unit


def _state() -> CompositeCheckpointState:
    return CompositeCheckpointState(
        composite_name="publication",
        run_id="run-001",
        state=CompositePipelineState.MERGING,
        effective_config_hash="a" * 64,
        effective_config_artifact_id="artifact-1",
        execution_fingerprint="fingerprint-1",
        dq_contract_compatibility_hash="dq-hash-1",
        input_snapshot_fingerprint="snapshot-1",
        contract_ref="composite.publication",
        contract_version="1.0.0",
        manifest_id="manifest-1",
        composite_run_identity="composite-run-1",
        created_at=datetime(2026, 6, 19, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 6, 19, 12, 5, tzinfo=UTC),
    )


def _anchors() -> ExpectedCheckpointContext:
    return ExpectedCheckpointContext(
        effective_config_hash="a" * 64,
        effective_config_artifact_id="artifact-1",
        execution_fingerprint="fingerprint-1",
        dq_contract_compatibility_hash="dq-hash-1",
        input_snapshot_fingerprint="snapshot-1",
        contract_ref="composite.publication",
        contract_version="1.0.0",
        manifest_id="manifest-1",
        composite_run_identity="composite-run-1",
    )


def test_validate_resume_compatibility_accepts_matching_anchors() -> None:
    validate_resume_compatibility(
        state=_state(),
        anchors=_anchors(),
        logger=MagicMock(),
        composite_name="publication",
    )


def test_validate_resume_compatibility_reports_missing_required_anchor() -> None:
    logger = MagicMock()
    with pytest.raises(
        CheckpointConflictError, match="checkpoint missing manifest_id anchor"
    ):
        validate_resume_compatibility(
            state=replace(_state(), manifest_id=""),
            anchors=_anchors(),
            logger=logger,
            composite_name="publication",
        )

    logger.error.assert_called_once()


def test_validate_resume_compatibility_reports_multiple_anchor_mismatches() -> None:
    with pytest.raises(CheckpointConflictError) as exc_info:
        validate_resume_compatibility(
            state=replace(
                _state(),
                effective_config_hash="b" * 64,
                composite_run_identity="composite-run-2",
            ),
            anchors=_anchors(),
            logger=MagicMock(),
            composite_name="publication",
        )

    message = str(exc_info.value)
    assert "effective_config_hash" in message
    assert "composite_run_identity" in message
