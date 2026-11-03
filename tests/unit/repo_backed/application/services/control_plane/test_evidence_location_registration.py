# pyright: reportArgumentType=false
"""RF-004 evidence-location registration and finalize consistency."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.application.services.evidence_location import (
    EVIDENCE_LOCATION_OBSERVATION_DOMAIN,
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationService,
    record_registration_soft_failure_observation,
)
from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    reset_run_observations,
    run_observations,
)
from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationKind,
    build_run_evidence_location,
)
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

_SOURCE = "a" * 64
_RUN = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"
_WF = "3dc8ffe4-305b-5d4b-a945-fe8e78f03828"


def _service(tmp_path: Path) -> EvidenceLocationRegistrationService:
    report_root = tmp_path / "run-reports"
    report_root.mkdir()
    return EvidenceLocationRegistrationService(
        locations=FileEvidenceLocationStore(report_root=report_root)
    )


def test_register_standalone_pipeline(tmp_path: Path) -> None:
    service = _service(tmp_path)
    outcome = service.register_pipeline_run(
        pipeline_name="chembl_assay",
        run_id=_RUN,
        runtime_source_id=_SOURCE,
        relative_data_root=".",
    )
    assert outcome.code == "registered"
    found = service.locations.get(
        kind=EvidenceLocationKind.PIPELINE, owner="chembl_assay", run_id=_RUN
    )
    assert found is not None
    assert found.relative_data_root == "."
    assert found.workflow_run_id is None


def test_register_workflow_child_and_parent_reciprocal(tmp_path: Path) -> None:
    service = _service(tmp_path)
    child = service.register_pipeline_run(
        pipeline_name="chembl_assay",
        run_id=_RUN,
        runtime_source_id=_SOURCE,
        relative_data_root="workflow-a/chembl_assay",
        workflow_run_id=_WF,
    )
    parent = service.register_workflow_run(
        workflow_name="chembl_assay_pack",
        workflow_run_id=_WF,
        runtime_source_id=_SOURCE,
        relative_data_root="workflow-a/chembl_assay",
    )
    assert child.code == "registered"
    assert parent.code == "registered"
    child_loc = service.locations.get(
        kind=EvidenceLocationKind.PIPELINE, owner="chembl_assay", run_id=_RUN
    )
    parent_loc = service.locations.get(
        kind=EvidenceLocationKind.WORKFLOW, owner="chembl_assay_pack", run_id=_WF
    )
    assert child_loc is not None and child_loc.workflow_run_id == _WF
    assert parent_loc is not None and parent_loc.workflow_run_id is None


def test_register_idempotent_identical(tmp_path: Path) -> None:
    service = _service(tmp_path)
    first = service.register_pipeline_run(
        pipeline_name="chembl_assay",
        run_id=_RUN,
        runtime_source_id=_SOURCE,
        relative_data_root=".",
    )
    second = service.register_pipeline_run(
        pipeline_name="chembl_assay",
        run_id=_RUN,
        runtime_source_id=_SOURCE,
        relative_data_root=".",
    )
    assert first.code == "registered"
    assert second.code == "already_identical"


def test_register_conflict_is_diagnostic(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.register_pipeline_run(
        pipeline_name="chembl_assay",
        run_id=_RUN,
        runtime_source_id=_SOURCE,
        relative_data_root=".",
    )
    conflict = service.register_pipeline_run(
        pipeline_name="chembl_assay",
        run_id=_RUN,
        runtime_source_id=_SOURCE,
        relative_data_root="other-root",
    )
    assert conflict.code == "conflict"


def test_soft_failure_observation_surfaces_conflict_not_success() -> None:
    token = bind_run_observations()
    try:
        record_registration_soft_failure_observation(
            code="registered",
            facts={"kind": "pipeline"},
        )
        assert EVIDENCE_LOCATION_OBSERVATION_DOMAIN not in run_observations()

        record_registration_soft_failure_observation(
            code="skipped_missing_runtime_source_id",
            facts={"kind": "pipeline"},
        )
        assert EVIDENCE_LOCATION_OBSERVATION_DOMAIN not in run_observations()

        record_registration_soft_failure_observation(
            code="conflict",
            detail="binding_conflict",
            facts={"kind": "workflow", "owner": "chembl_assay_pack"},
        )
        observations = run_observations()
        assert observations[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["verdict"] == "ERROR"
        assert (
            observations[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["reason"] == "conflict"
        )
    finally:
        reset_run_observations(token)


def test_verify_observation_does_not_require_ready(tmp_path: Path) -> None:
    service = _service(tmp_path)
    token = bind_run_observations()
    try:
        missing = service.record_verify_observation(
            EvidenceLocationRegisterRequest(
                kind=EvidenceLocationKind.PIPELINE,
                owner="chembl_assay",
                run_id=_RUN,
                runtime_source_id=_SOURCE,
                relative_data_root=".",
            )
        )
        assert missing.code == "location_missing"
        assert missing.verdict == "INCOMPLETE"
        observations = run_observations()
        assert EVIDENCE_LOCATION_OBSERVATION_DOMAIN in observations
        assert observations[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["verdict"] == (
            "INCOMPLETE"
        )

        service.locations.register(
            build_run_evidence_location(
                kind=EvidenceLocationKind.PIPELINE,
                owner="chembl_assay",
                run_id=_RUN,
                runtime_source_id=_SOURCE,
                root_alias=DEFAULT_EVIDENCE_ROOT_ALIAS,
                relative_data_root=".",
            )
        )
        ok = service.record_verify_observation(
            EvidenceLocationRegisterRequest(
                kind=EvidenceLocationKind.PIPELINE,
                owner="chembl_assay",
                run_id=_RUN,
                runtime_source_id=_SOURCE,
                relative_data_root=".",
            )
        )
        assert ok.code == "ok"
        assert ok.verdict == "OK"
    finally:
        reset_run_observations(token)


def test_workflow_manifest_service_surfaces_register_exception_observation() -> None:
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from uuid import UUID

    from bioetl.application.services.control_plane.workflow.manifest_models import (
        WorkflowManifestCreateSpec,
    )
    from bioetl.application.services.control_plane.workflow.manifest_service import (
        WorkflowManifestService,
    )
    from bioetl.domain.types import RunID
    from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig

    def _boom(_manifest: object) -> None:
        raise RuntimeError("locator boom")

    service = WorkflowManifestService(
        manifest_port=SimpleNamespace(save=lambda _manifest: None),
        created_at_factory=lambda: datetime(2026, 1, 1, tzinfo=UTC),
        _manifest_id_factory=lambda: "workflow-manifest-soft",
        evidence_location_register=_boom,
    )
    token = bind_run_observations()
    try:
        manifest = service.create_manifest(
            WorkflowManifestCreateSpec(
                workflow_run_id=RunID(UUID(_WF)),
                config=WorkflowConfig(
                    name="chembl_assay_pack",
                    steps=(
                        WorkflowStepConfig(
                            step_id="ingest",
                            pipeline_name="chembl_assay",
                        ),
                    ),
                ),
                launch_context={},
            )
        )
        assert manifest.workflow_name == "chembl_assay_pack"
        observations = run_observations()
        assert (
            observations[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["reason"]
            == "registration_exception"
        )
        assert observations[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["verdict"] == "ERROR"
    finally:
        reset_run_observations(token)


def test_soft_failure_observation_surfaces_verify_exception() -> None:
    token = bind_run_observations()
    try:
        record_registration_soft_failure_observation(
            code="verify_exception",
            detail="RuntimeError: verify boom",
            facts={"kind": "pipeline", "owner": "chembl_assay", "run_id": _RUN},
        )
        observations = run_observations()
        assert observations[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["verdict"] == "ERROR"
        assert (
            observations[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["reason"]
            == "verify_exception"
        )
    finally:
        reset_run_observations(token)


def test_bind_if_unbound_preserves_outer_prepare_scope() -> None:
    from bioetl.application.services.run_reports.observations import (
        bind_run_observations_if_unbound,
        reset_run_observations_if_bound,
    )

    outer = bind_run_observations()
    try:
        record_registration_soft_failure_observation(
            code="registration_exception",
            detail="RuntimeError: locator boom",
            facts={"kind": "workflow", "owner": "chembl_assay_pack", "run_id": _WF},
        )
        nested = bind_run_observations_if_unbound()
        assert nested is None
        observations = run_observations()
        assert (
            observations[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["reason"]
            == "registration_exception"
        )
        reset_run_observations_if_bound(nested)
        assert (
            run_observations()[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["reason"]
            == "registration_exception"
        )
    finally:
        reset_run_observations(outer)


def test_bind_if_unbound_creates_scope_when_missing() -> None:
    from bioetl.application.services.run_reports.observations import (
        bind_run_observations_if_unbound,
        reset_run_observations_if_bound,
    )

    token = bind_run_observations_if_unbound()
    try:
        assert token is not None
        record_registration_soft_failure_observation(
            code="verify_exception",
            facts={"kind": "workflow"},
        )
        assert (
            run_observations()[EVIDENCE_LOCATION_OBSERVATION_DOMAIN]["reason"]
            == "verify_exception"
        )
    finally:
        reset_run_observations_if_bound(token)
