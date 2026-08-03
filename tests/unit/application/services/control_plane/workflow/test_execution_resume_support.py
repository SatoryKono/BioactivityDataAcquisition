# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for workflow resume preparation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.workflow import (
    _execution_resume_support as support,
)
from bioetl.domain.control_plane import (
    WorkflowExecutionState,
    WorkflowManifest,
    WorkflowManifestStep,
    WorkflowStepState,
)
from bioetl.domain.types import RunID
from tests.helpers.clock import FIXED_TEST_TIME


pytestmark = pytest.mark.unit


@dataclass
class _WorkflowStatePortStub:
    by_run_id: WorkflowExecutionState | None = None
    by_manifest_id: WorkflowExecutionState | None = None
    latest_state: WorkflowExecutionState | None = None
    saved_states: list[WorkflowExecutionState] | None = None

    def get_by_run_id(self, _run_id: RunID) -> WorkflowExecutionState | None:
        return self.by_run_id

    def get_by_manifest_id(self, _manifest_id: str) -> WorkflowExecutionState | None:
        return self.by_manifest_id

    def get_latest(self, _workflow_name: str) -> WorkflowExecutionState | None:
        return self.latest_state

    def save(self, state: WorkflowExecutionState) -> None:
        assert self.saved_states is not None
        self.saved_states.append(state)


def _state(
    *,
    status: str = "failed",
    repair_required: bool = False,
    repair_hint: str | None = None,
    execution_fingerprint: str = "fingerprint-1",
) -> WorkflowExecutionState:
    return WorkflowExecutionState(
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000601")),
        manifest_id="manifest-1",
        workflow_name="chembl_publication",
        execution_fingerprint=execution_fingerprint,
        status=status,
        started_at=FIXED_TEST_TIME,
        updated_at=FIXED_TEST_TIME,
        completed_at=None,
        selected_step_ids=("seed", "enrich"),
        steps=(
            WorkflowStepState(step_id="seed", step_kind="pipeline", status="success"),
            WorkflowStepState(step_id="enrich", step_kind="transform", status="failed"),
        ),
        completed_transform_fingerprints={
            "seed": "fp-seed",
            "enrich": "fp-enrich",
        },
        repair_required=repair_required,
        repair_hint=repair_hint,
    )


def _manifest() -> WorkflowManifest:
    return WorkflowManifest(
        manifest_id="manifest-1",
        workflow_run_id=RunID(UUID("00000000-0000-0000-0000-000000000602")),
        execution_fingerprint="fingerprint-1",
        schema_version="workflow-manifest-v1",
        created_at=FIXED_TEST_TIME,
        workflow_name="chembl_publication",
        workflow_version="1.0.0",
        launch_context={"resume": True},
        defaults={},
        selected_step_ids=("seed",),
        steps=(WorkflowManifestStep(step_id="seed", kind="pipeline"),),
    )


def test_load_resume_state_prefers_run_id_selector() -> None:
    state = _state()

    loaded = support.load_resume_state(
        workflow_state_port=_WorkflowStatePortStub(by_run_id=state),
        workflow_name="chembl_publication",
        resume_manifest_id=None,
        resume_run_id=str(state.workflow_run_id),
    )

    assert loaded is state


def test_load_resume_state_errors_when_resume_manifest_missing() -> None:
    with pytest.raises(RuntimeError, match="--resume-manifest-id=manifest-404"):
        support.load_resume_state(
            workflow_state_port=_WorkflowStatePortStub(),
            workflow_name="chembl_publication",
            resume_manifest_id="manifest-404",
            resume_run_id=None,
        )


def test_validate_resume_state_requires_same_fingerprint() -> None:
    with pytest.raises(RuntimeError, match="same execution fingerprint"):
        support.validate_resume_state(
            latest_state=_state(execution_fingerprint="old"),
            workflow_name="chembl_publication",
            current_fingerprint="new",
            force_steps=(),
            repair_steps=(),
        )


def test_validate_resume_state_requires_explicit_repair_or_force() -> None:
    with pytest.raises(RuntimeError, match="repair the seed step first"):
        support.validate_resume_state(
            latest_state=_state(
                repair_required=True,
                repair_hint="repair the seed step first",
            ),
            workflow_name="chembl_publication",
            current_fingerprint="fingerprint-1",
            force_steps=(),
            repair_steps=(),
        )


def test_load_resume_manifest_errors_when_persisted_manifest_missing() -> None:
    manifest_service = SimpleNamespace(
        manifest_port=SimpleNamespace(get=lambda _id: None)
    )

    with pytest.raises(RuntimeError, match="persisted manifest could not be loaded"):
        support.load_resume_manifest(
            manifest_service=manifest_service,
            latest_state=_state(),
        )


def test_normalize_resume_state_persists_incomplete_state_for_running_resume() -> None:
    state = _state(status="running")
    saved_states: list[WorkflowExecutionState] = []
    port = _WorkflowStatePortStub(saved_states=saved_states)

    normalized = support.normalize_resume_state(
        state,
        workflow_state_port=port,
        now_factory=lambda: FIXED_TEST_TIME,
    )

    assert normalized.status == "incomplete"
    assert saved_states == [normalized]


def test_resolve_resume_outputs_filter_forced_and_repaired_steps() -> None:
    state = _state()

    assert (
        support.resolve_skipped_step_ids(
            state=state,
            force_steps=("seed",),
            repair_steps=(),
        )
        == frozenset()
    )
    assert support.resolve_completed_transform_fingerprints(
        state=state,
        force_steps=(),
        repair_steps=("enrich",),
    ) == {"seed": "fp-seed"}


def test_coerce_resume_run_id_accepts_uuid_instances() -> None:
    raw = UUID("00000000-0000-0000-0000-000000000603")

    assert support.coerce_resume_run_id(raw) == RunID(raw)


def test_load_resume_manifest_returns_persisted_manifest() -> None:
    manifest = _manifest()
    manifest_service = SimpleNamespace(
        manifest_port=SimpleNamespace(get=lambda _manifest_id: manifest)
    )

    loaded = support.load_resume_manifest(
        manifest_service=manifest_service,
        latest_state=_state(),
    )

    assert loaded is manifest
