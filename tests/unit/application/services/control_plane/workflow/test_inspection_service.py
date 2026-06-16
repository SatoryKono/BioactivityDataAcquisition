"""Unit tests for workflow inspection service."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.workflow.inspection_service import (
    WorkflowInspectionService,
)
from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowStepState
from bioetl.domain.types import RunID


def _make_state() -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000201")),
        manifest_id="manifest-1",
        workflow_name="chembl_baseline",
        execution_fingerprint="fingerprint-1",
        status="failed",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
        completed_at=None,
        selected_step_ids=("extract",),
        steps=(
            WorkflowStepState(
                step_id="extract",
                step_kind="pipeline",
                status="failed",
                error_type="RuntimeError",
                error_message="boom",
            ),
        ),
        completed_transform_fingerprints={},
        repair_required=True,
        repair_hint="resume from checkpoint",
        ambiguous_step_ids=("extract",),
        last_error_type="RuntimeError",
        last_error_message="boom",
    )


def test_inspect_latest_returns_none_when_state_missing() -> None:
    service = WorkflowInspectionService(
        manifest_port=SimpleNamespace(),
        ledger_port=SimpleNamespace(),
        state_port=SimpleNamespace(get_latest=lambda workflow_name: None),
    )

    assert service.inspect_latest("chembl_baseline") is None


def test_inspection_service_builds_result_from_state_and_manifest() -> None:
    state = _make_state()
    manifest = SimpleNamespace(workflow_version="1.2.0")
    service = WorkflowInspectionService(
        manifest_port=SimpleNamespace(get=lambda manifest_id: manifest),
        ledger_port=SimpleNamespace(
            list_entries=lambda manifest_id: [object(), object(), object()]
        ),
        state_port=SimpleNamespace(
            get_latest=lambda workflow_name: state,
            get_by_run_id=lambda run_id: state,
        ),
    )

    result = service.inspect_latest("chembl_baseline")

    assert result is not None
    assert result.workflow_name == "chembl_baseline"
    assert result.workflow_version == "1.2.0"
    assert result.ledger_entry_count == 3
    assert result.step_states[0]["step_id"] == "extract"
    assert service.inspect_run_id(str(state.workflow_run_id)) == result


def test_inspection_service_raises_when_manifest_is_missing() -> None:
    state = _make_state()
    service = WorkflowInspectionService(
        manifest_port=SimpleNamespace(get=lambda manifest_id: None),
        ledger_port=SimpleNamespace(list_entries=lambda manifest_id: []),
        state_port=SimpleNamespace(get_latest=lambda workflow_name: state),
    )

    with pytest.raises(RuntimeError, match="persisted manifest could not be loaded"):
        service.inspect_latest("chembl_baseline")
