from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.workflow.manifest_service import (
    WorkflowManifestService,
)
from bioetl.application.services.workflow.control_plane.execution_service import (
    WorkflowExecutionService,
)
from bioetl.application.services.workflow.workflow_runner_service import (
    WorkflowTransformDestructiveCommit,
)
from bioetl.domain.types import RunID
from bioetl.domain.workflow import TransformStepConfig, WorkflowConfig

from tests.helpers.clock import FIXED_TEST_TIME
from tests.unit.application.services.control_plane.test_workflow_execution_service import (
    _InMemoryWorkflowManifestPort,
    _InMemoryWorkflowLedgerPort,
    _InMemoryWorkflowStatePort,
    _FakeLockPort,
    _create_workflow_ledger_service,
    _FakeWorkflowRunner,
)


def _build_two_step_transform_config() -> WorkflowConfig:
    return WorkflowConfig(
        name="chembl_repair_two_step",
        steps=(
            TransformStepConfig(
                step_id="step_a",
                transform_name="reconcile_foreign_keys",
                config={},
            ),
            TransformStepConfig(
                step_id="step_b",
                transform_name="reconcile_foreign_keys",
                config={},
            ),
        ),
    )


@pytest.mark.asyncio
async def test_workflow_execution_partial_repair_incomplete():
    manifest_port = _InMemoryWorkflowManifestPort()
    ledger_port = _InMemoryWorkflowLedgerPort()
    state_port = _InMemoryWorkflowStatePort()
    lock_port = _FakeLockPort()

    @dataclass
    class _CrashAfterTwoCommitsRunner:
        async def run_workflow(
            self,
            config,
            *,
            step_started_callback=None,
            transform_commit_callback=None,
            **kwargs,
        ):
            if step_started_callback is not None:
                step_started_callback(config.steps[0], fingerprint="fp-a")
            if transform_commit_callback is not None:
                transform_commit_callback(
                    WorkflowTransformDestructiveCommit(
                        step_id="step_a",
                        transform_name="reconcile_foreign_keys",
                        fingerprint="fp-a",
                        details={},
                    )
                )
            if step_started_callback is not None:
                step_started_callback(config.steps[1], fingerprint="fp-b")
            if transform_commit_callback is not None:
                transform_commit_callback(
                    WorkflowTransformDestructiveCommit(
                        step_id="step_b",
                        transform_name="reconcile_foreign_keys",
                        fingerprint="fp-b",
                        details={},
                    )
                )
            raise RuntimeError("simulated crash after two commits")

    service = WorkflowExecutionService(
        workflow_runner=_CrashAfterTwoCommitsRunner(),
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "manifest-1",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=lock_port,
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000001")),
    )

    with pytest.raises(RuntimeError, match="simulated crash after two commits"):
        await service.run_workflow(_build_two_step_transform_config())

    state = state_port.get_latest("chembl_repair_two_step")
    assert state.ambiguous_step_ids == ("step_a", "step_b")

    # Repair only B
    fake_runner = _FakeWorkflowRunner()
    resume_service = WorkflowExecutionService(
        workflow_runner=fake_runner,
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "manifest-2",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=_FakeLockPort(),
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000002")),
    )

    result = await resume_service.run_workflow(
        _build_two_step_transform_config(),
        resume_last=True,
        repair_steps=("step_b",),
    )

    assert result.status == "success"
    assert result.resumed is True
    state_after_repair = state_port.get_latest("chembl_repair_two_step")
    assert state_after_repair.status == "incomplete"
    assert state_after_repair.repair_required is True
    assert state_after_repair.ambiguous_step_ids == ("step_a",)

    # Now verify scenario 2: resume doesn't die on "already completed successfully"
    # We should be able to resume with repair_steps=("step_a",)
    fake_runner3 = _FakeWorkflowRunner()
    resume_service3 = WorkflowExecutionService(
        workflow_runner=fake_runner3,
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "manifest-3",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=_FakeLockPort(),
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000003")),
    )

    result3 = await resume_service3.run_workflow(
        _build_two_step_transform_config(),
        resume_last=True,
        repair_steps=("step_a",),
    )

    assert result3.status == "success"
    assert result3.resumed is True
    state_after_full_repair = state_port.get_latest("chembl_repair_two_step")
    assert state_after_full_repair.status == "success"
    assert not state_after_full_repair.ambiguous_step_ids

    # Scenario 3: failure after repair
    state_port.save(state_after_repair)  # revert back to incomplete state

    @dataclass
    class _CrashAfterRepairRunner:
        async def run_workflow(
            self,
            config,
            **kwargs,
        ):
            raise RuntimeError("simulated crash during second repair")

    resume_service_fail = WorkflowExecutionService(
        workflow_runner=_CrashAfterRepairRunner(),
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "manifest-fail",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=_FakeLockPort(),
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000004")),
    )
    with pytest.raises(RuntimeError, match="simulated crash during second repair"):
        await resume_service_fail.run_workflow(
            _build_two_step_transform_config(),
            resume_last=True,
            repair_steps=("step_a",),
        )

    state_after_fail = state_port.get_latest("chembl_repair_two_step")
    # A crash leaves the last persisted running snapshot without a terminal event.
    assert state_after_fail.status == "running"
    assert state_after_fail.repair_required is True
    assert state_after_fail.ambiguous_step_ids == ("step_a",)

    with pytest.raises(RuntimeError, match="explicit --repair-steps or --force-steps"):
        await resume_service_fail.run_workflow(
            _build_two_step_transform_config(), resume_last=True
        )
