"""Unit tests for workflow execution control-plane orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pytest

from bioetl.application.services.control_plane import (
    WorkflowExecutionService,
    WorkflowLedgerService,
    WorkflowManifestService,
)
from bioetl.application.services.workflow_runner_service import (
    WorkflowRunExecutionResult,
    WorkflowTransformDestructiveCommit,
    WorkflowStepExecutionResult,
)
from bioetl.domain.control_plane import (
    WorkflowExecutionState,
    WorkflowLedgerEntry,
    WorkflowManifest,
    WorkflowStepState,
)
from bioetl.domain.ports import LockPort
from bioetl.domain.types import RunID
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig
from tests.helpers.clock import FIXED_TEST_TIME


@dataclass
class _InMemoryWorkflowManifestPort:
    by_manifest_id: dict[str, WorkflowManifest] = field(default_factory=dict)
    by_run_id: dict[str, WorkflowManifest] = field(default_factory=dict)

    def save(self, manifest: WorkflowManifest) -> None:
        self.by_manifest_id[manifest.manifest_id] = manifest
        self.by_run_id[str(manifest.workflow_run_id)] = manifest

    def get(self, manifest_id: str) -> WorkflowManifest | None:
        return self.by_manifest_id.get(manifest_id)

    def get_by_run_id(self, workflow_run_id: RunID) -> WorkflowManifest | None:
        return self.by_run_id.get(str(workflow_run_id))


@dataclass
class _InMemoryWorkflowLedgerPort:
    entries: list[WorkflowLedgerEntry] = field(default_factory=list)

    def append(self, entry: WorkflowLedgerEntry) -> None:
        self.entries.append(entry)

    def list_entries(self, manifest_id: str) -> list[WorkflowLedgerEntry]:
        return [entry for entry in self.entries if entry.manifest_id == manifest_id]

    def list_entries_by_run_id(
        self, workflow_run_id: RunID
    ) -> list[WorkflowLedgerEntry]:
        return [
            entry
            for entry in self.entries
            if str(entry.workflow_run_id) == str(workflow_run_id)
        ]


def _create_workflow_ledger_service(
    ledger_port: _InMemoryWorkflowLedgerPort,
    manifest: WorkflowManifest,
) -> WorkflowLedgerService:
    return WorkflowLedgerService(
        ledger_port=ledger_port,
        manifest_id=manifest.manifest_id,
        workflow_run_id=manifest.workflow_run_id,
        workflow_name=manifest.workflow_name,
    )


@dataclass
class _InMemoryWorkflowStatePort:
    by_run_id: dict[str, WorkflowExecutionState] = field(default_factory=dict)
    by_manifest_id: dict[str, WorkflowExecutionState] = field(default_factory=dict)
    latest_by_workflow: dict[str, WorkflowExecutionState] = field(default_factory=dict)

    def save(self, state: WorkflowExecutionState) -> None:
        self.by_run_id[str(state.workflow_run_id)] = state
        self.by_manifest_id[state.manifest_id] = state
        self.latest_by_workflow[state.workflow_name] = state

    def get_by_run_id(self, workflow_run_id: RunID) -> WorkflowExecutionState | None:
        return self.by_run_id.get(str(workflow_run_id))

    def get_by_manifest_id(self, manifest_id: str) -> WorkflowExecutionState | None:
        return self.by_manifest_id.get(manifest_id)

    def get_latest(self, workflow_name: str) -> WorkflowExecutionState | None:
        return self.latest_by_workflow.get(workflow_name)


@dataclass
class _FakeLockPort(LockPort):
    held: bool = False
    acquire_calls: list[tuple[str, str]] = field(default_factory=list)
    release_calls: list[tuple[str, str]] = field(default_factory=list)

    async def acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> object | None:
        del ttl, wait, wait_timeout, exclusive
        self.acquire_calls.append((key, str(owner_id)))
        if self.held:
            return None
        self.held = True
        return object()

    async def release(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        del exclusive
        self.release_calls.append((key, str(owner_id)))
        self.held = False
        return True

    async def heartbeat(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        del key, owner_id, exclusive
        return True

    async def validate_owner(self, key: str, owner_id: RunID) -> bool:
        del key, owner_id
        return self.held

    async def validate_fencing_token(self, key: str, token: object) -> bool:
        del key, token
        return True

    async def aclose(self) -> None:
        self.held = False


@dataclass
class _FakeWorkflowRunner:
    received_completed_step_ids: frozenset[str] | None = None

    async def run_workflow(
        self,
        config: WorkflowConfig,
        *,
        completed_step_ids: frozenset[str] | None = None,
        completed_transform_fingerprints: dict[str, str] | None = None,
        step_started_callback: object | None = None,
        step_completed_callback: object | None = None,
        transform_commit_callback: object | None = None,
    ) -> WorkflowRunExecutionResult:
        del completed_transform_fingerprints, transform_commit_callback
        self.received_completed_step_ids = completed_step_ids
        if step_started_callback is not None:
            for step in config.steps:
                step_started_callback(step, fingerprint=None)
                if step.step_id in (completed_step_ids or frozenset()):
                    continue
                step_completed_callback(
                    WorkflowStepExecutionResult(
                        step_id=step.step_id,
                        step_kind="pipeline",
                        status="success",
                    )
                )
        return WorkflowRunExecutionResult(
            workflow_name=config.name,
            status="success",
            steps=tuple(
                WorkflowStepExecutionResult(
                    step_id=step.step_id,
                    step_kind="pipeline",
                    status=(
                        "skipped"
                        if step.step_id in (completed_step_ids or frozenset())
                        else "success"
                    ),
                    error_type=(
                        "AlreadyCompletedOnResume"
                        if step.step_id in (completed_step_ids or frozenset())
                        else None
                    ),
                )
                for step in config.steps
            ),
        )


def _build_config() -> WorkflowConfig:
    return WorkflowConfig(
        name="chembl_core",
        steps=(
            WorkflowStepConfig(
                step_id="chembl_activity_ingest",
                pipeline_name="chembl_activity",
            ),
            WorkflowStepConfig(
                step_id="chembl_assay_ingest",
                pipeline_name="chembl_assay",
                depends_on=("chembl_activity_ingest",),
            ),
        ),
    )


def _build_transform_config() -> WorkflowConfig:
    from bioetl.domain.workflow import TransformStepConfig

    return WorkflowConfig(
        name="chembl_repair",
        steps=(
            TransformStepConfig(
                step_id="reconcile_assay_target_orphans",
                transform_name="reconcile_foreign_keys",
                config={
                    "source_table": "chembl_assay",
                    "reference_table": "chembl_target",
                    "source_key": "target_id",
                    "reference_key": "target_id",
                    "primary_keys": ["assay_id"],
                    "action": "delete_orphans",
                },
            ),
        ),
    )


@pytest.mark.asyncio
async def test_workflow_execution_service_persists_manifest_ledger_and_state() -> None:
    manifest_port = _InMemoryWorkflowManifestPort()
    ledger_port = _InMemoryWorkflowLedgerPort()
    state_port = _InMemoryWorkflowStatePort()
    lock_port = _FakeLockPort()
    service = WorkflowExecutionService(
        workflow_runner=_FakeWorkflowRunner(),  # type: ignore[arg-type]
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "workflow-manifest-1",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=lock_port,
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000111")),
    )

    result = await service.run_workflow(_build_config())

    assert result.status == "success"
    assert result.manifest_id == "workflow-manifest-1"
    assert result.workflow_run_id == "00000000-0000-0000-0000-000000000111"
    assert manifest_port.get("workflow-manifest-1") is not None
    assert len(ledger_port.entries) >= 3
    latest_state = state_port.get_latest("chembl_core")
    assert latest_state is not None
    assert latest_state.status == "success"
    assert lock_port.acquire_calls == [
        ("workflow:chembl_core", "00000000-0000-0000-0000-000000000111")
    ]
    assert lock_port.release_calls == [
        ("workflow:chembl_core", "00000000-0000-0000-0000-000000000111")
    ]


@pytest.mark.asyncio
async def test_workflow_execution_service_resume_last_skips_completed_steps() -> None:
    manifest_port = _InMemoryWorkflowManifestPort()
    ledger_port = _InMemoryWorkflowLedgerPort()
    state_port = _InMemoryWorkflowStatePort()
    lock_port = _FakeLockPort()
    manifest = WorkflowManifestService(
        manifest_port=manifest_port,
        created_at_factory=lambda: FIXED_TEST_TIME,
        _manifest_id_factory=lambda: "workflow-manifest-1",
    ).create_manifest(
        request=type(
            "_Request",
            (),
            {
                "workflow_run_id": RunID(UUID("00000000-0000-0000-0000-000000000111")),
                "config": _build_config(),
                "launch_context": {},
                "resumed_from_manifest_id": None,
            },
        )()
    )
    state_port.save(
        WorkflowExecutionState(
            workflow_run_id=manifest.workflow_run_id,
            manifest_id=manifest.manifest_id,
            workflow_name=manifest.workflow_name,
            execution_fingerprint=manifest.execution_fingerprint,
            status="failed",
            started_at=FIXED_TEST_TIME,
            updated_at=FIXED_TEST_TIME,
            completed_at=FIXED_TEST_TIME,
            selected_step_ids=manifest.selected_step_ids,
            steps=(
                WorkflowStepState(
                    step_id="chembl_activity_ingest",
                    step_kind="pipeline",
                    status="success",
                ),
                WorkflowStepState(
                    step_id="chembl_assay_ingest",
                    step_kind="pipeline",
                    status="failed",
                    error_type="RuntimeError",
                    error_message="boom",
                ),
            ),
            completed_transform_fingerprints={},
            last_error_type="RuntimeError",
            last_error_message="boom",
        )
    )
    fake_runner = _FakeWorkflowRunner()
    service = WorkflowExecutionService(
        workflow_runner=fake_runner,  # type: ignore[arg-type]
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "workflow-manifest-2",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=lock_port,
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000222")),
    )

    result = await service.run_workflow(_build_config(), resume_last=True)

    assert result.status == "success"
    assert result.resumed is True
    assert result.manifest_id == "workflow-manifest-1"
    assert fake_runner.received_completed_step_ids == frozenset(
        {"chembl_activity_ingest"}
    )


@pytest.mark.asyncio
async def test_workflow_execution_service_fails_when_lock_is_held() -> None:
    manifest_port = _InMemoryWorkflowManifestPort()
    state_port = _InMemoryWorkflowStatePort()
    lock_port = _FakeLockPort(held=True)
    service = WorkflowExecutionService(
        workflow_runner=_FakeWorkflowRunner(),  # type: ignore[arg-type]
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "workflow-manifest-1",
        ),
        workflow_ledger_port=_InMemoryWorkflowLedgerPort(),
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=lock_port,
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000111")),
    )

    with pytest.raises(RuntimeError, match="already running"):
        await service.run_workflow(_build_config())


@pytest.mark.asyncio
async def test_workflow_execution_service_requires_explicit_repair_after_ambiguous_commit() -> (
    None
):
    manifest_port = _InMemoryWorkflowManifestPort()
    ledger_port = _InMemoryWorkflowLedgerPort()
    state_port = _InMemoryWorkflowStatePort()
    lock_port = _FakeLockPort()

    @dataclass
    class _CrashAfterCommitRunner:
        async def run_workflow(
            self,
            config: WorkflowConfig,
            *,
            completed_step_ids: frozenset[str] | None = None,
            completed_transform_fingerprints: dict[str, str] | None = None,
            step_started_callback: object | None = None,
            step_completed_callback: object | None = None,
            transform_commit_callback: object | None = None,
        ) -> WorkflowRunExecutionResult:
            del (
                completed_step_ids,
                completed_transform_fingerprints,
                step_completed_callback,
            )
            step = config.steps[0]
            if step_started_callback is not None:
                step_started_callback(step, fingerprint="transform-fingerprint-1")
            if transform_commit_callback is not None:
                transform_commit_callback(
                    WorkflowTransformDestructiveCommit(
                        step_id="reconcile_assay_target_orphans",
                        transform_name="reconcile_foreign_keys",
                        fingerprint="transform-fingerprint-1",
                        details={
                            "source_table": "chembl_assay",
                            "orphan_rows_deleted": 2,
                        },
                    )
                )
            raise RuntimeError("simulated crash after commit")

    service = WorkflowExecutionService(
        workflow_runner=_CrashAfterCommitRunner(),  # type: ignore[arg-type]
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "workflow-manifest-crash",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=lock_port,
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000333")),
    )

    with pytest.raises(RuntimeError, match="simulated crash after commit"):
        await service.run_workflow(_build_transform_config())

    latest_state = state_port.get_latest("chembl_repair")
    assert latest_state is not None
    assert latest_state.repair_required is True
    assert latest_state.ambiguous_step_ids == ("reconcile_assay_target_orphans",)
    assert any(
        entry.event_type == "workflow_step_commit_pending_confirmation"
        for entry in ledger_port.entries
    )

    resume_service = WorkflowExecutionService(
        workflow_runner=_FakeWorkflowRunner(),  # type: ignore[arg-type]
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "workflow-manifest-resume",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=_FakeLockPort(),
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000444")),
    )

    with pytest.raises(RuntimeError, match="explicit --repair-steps or --force-steps"):
        await resume_service.run_workflow(_build_transform_config(), resume_last=True)


@pytest.mark.asyncio
async def test_workflow_execution_service_incremental_offset_progression() -> None:
    """Test that incremental runs correctly progress offset across multiple executions."""
    manifest_port = _InMemoryWorkflowManifestPort()
    ledger_port = _InMemoryWorkflowLedgerPort()
    state_port = _InMemoryWorkflowStatePort()
    lock_port = _FakeLockPort()

    # Build config with limit
    from bioetl.domain.workflow import WorkflowRunOptionsConfig

    config_with_limit = WorkflowConfig(
        name="chembl_core",
        steps=(
            WorkflowStepConfig(
                step_id="chembl_activity_ingest",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(limit=1000),
            ),
            WorkflowStepConfig(
                step_id="chembl_assay_ingest",
                pipeline_name="chembl_assay",
                depends_on=("chembl_activity_ingest",),
                run_options=WorkflowRunOptionsConfig(limit=1000),
            ),
        ),
    )

    # First incremental run
    service1 = WorkflowExecutionService(
        workflow_runner=_FakeWorkflowRunner(),  # type: ignore[arg-type]
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "workflow-manifest-1",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=lock_port,
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000111")),
    )

    result1 = await service1.run_workflow(config_with_limit, incremental=True)
    assert result1.status == "success"

    # Check state after first run
    state1 = state_port.get_latest("chembl_core")
    assert state1 is not None
    assert state1.status == "success"
    assert state1.last_start_offset == 0  # None treated as 0
    assert state1.last_limit == 1000

    # Second incremental run with different limit
    config_with_limit_2 = WorkflowConfig(
        name="chembl_core",
        steps=(
            WorkflowStepConfig(
                step_id="chembl_activity_ingest",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(limit=500),
            ),
            WorkflowStepConfig(
                step_id="chembl_assay_ingest",
                pipeline_name="chembl_assay",
                depends_on=("chembl_activity_ingest",),
                run_options=WorkflowRunOptionsConfig(limit=500),
            ),
        ),
    )

    service2 = WorkflowExecutionService(
        workflow_runner=_FakeWorkflowRunner(),  # type: ignore[arg-type]
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "workflow-manifest-2",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=_FakeLockPort(),
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000222")),
    )

    result2 = await service2.run_workflow(config_with_limit_2, incremental=True)
    assert result2.status == "success"

    # Check state after second run
    state2 = state_port.get_latest("chembl_core")
    assert state2 is not None
    assert state2.status == "success"
    # Offset should be 0 + 1000 = 1000 from first run, limit should be 500 from second run
    assert state2.last_start_offset == 1000
    assert state2.last_limit == 500

    # Third incremental run
    service3 = WorkflowExecutionService(
        workflow_runner=_FakeWorkflowRunner(),  # type: ignore[arg-type]
        manifest_service=WorkflowManifestService(
            manifest_port=manifest_port,
            created_at_factory=lambda: FIXED_TEST_TIME,
            _manifest_id_factory=lambda: "workflow-manifest-3",
        ),
        workflow_ledger_port=ledger_port,
        workflow_ledger_factory=_create_workflow_ledger_service,
        workflow_state_port=state_port,
        workflow_lock_port=_FakeLockPort(),
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: RunID(UUID("00000000-0000-0000-0000-000000000333")),
    )

    result3 = await service3.run_workflow(config_with_limit_2, incremental=True)
    assert result3.status == "success"

    # Check state after third run
    state3 = state_port.get_latest("chembl_core")
    assert state3 is not None
    assert state3.status == "success"
    # Offset should be 1000 + 500 = 1500 from second run
    assert state3.last_start_offset == 1500
    assert state3.last_limit == 500
