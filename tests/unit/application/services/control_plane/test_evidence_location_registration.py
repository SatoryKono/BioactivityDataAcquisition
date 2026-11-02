# pyright: reportArgumentType=false
"""RF-004 evidence-location registration and finalize consistency."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.application.services.control_plane.evidence_location import (
    EVIDENCE_LOCATION_OBSERVATION_DOMAIN,
    EvidenceLocationRegisterRequest,
    EvidenceLocationRegistrationService,
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

pytestmark = pytest.mark.unit

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
