# pyright: reportArgumentType=false
"""RF-004 composition registration hooks and relative-root binding."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.composition.runtime_builders.evidence_location_registration import (
    build_evidence_location_binding_context,
    register_pipeline_manifest_location,
    register_workflow_manifest_location,
    relative_data_root_under_alias,
    resolve_registration_runtime_source_id,
)
from bioetl.domain.control_plane.run_evidence_location import EvidenceLocationKind
from bioetl.domain.control_plane.run_manifest import RunManifest
from bioetl.domain.control_plane.workflow_manifest import WorkflowManifest
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)

pytestmark = pytest.mark.unit

_SOURCE = "c" * 64
_RUN = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"
_WF = "3dc8ffe4-305b-5d4b-a945-fe8e78f03828"


def test_relative_data_root_standard_and_isolated(tmp_path: Path) -> None:
    alias = (tmp_path / "data").resolve()
    alias.mkdir()
    isolated = alias / "workflow-a" / "chembl_assay"
    isolated.mkdir(parents=True)
    foreign = (tmp_path / "other-data").resolve()
    foreign.mkdir()
    assert (
        relative_data_root_under_alias(write_data_root=alias, alias_base=alias) == "."
    )
    assert (
        relative_data_root_under_alias(write_data_root=isolated, alias_base=alias)
        == "workflow-a/chembl_assay"
    )
    assert (
        relative_data_root_under_alias(write_data_root=foreign, alias_base=alias)
        is None
    )


def test_register_skips_when_write_root_outside_dashboard_alias(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alias = (tmp_path / "dashboard-data").resolve()
    alias.mkdir()
    write_root = (tmp_path / "foreign-data").resolve()
    write_root.mkdir()
    report_root = tmp_path / "run-reports"
    report_root.mkdir()
    monkeypatch.setenv("BIOETL_RUNTIME_SOURCE_ID", _SOURCE)
    settings = SimpleNamespace(
        data_dir=write_root,
        report_root=report_root,
        runtime_source_id=_SOURCE,
        dashboard_data_root=alias,
    )
    binding = build_evidence_location_binding_context(settings)  # type: ignore[arg-type]
    assert binding.skip_reason is not None
    assert binding.alias_base == alias
    manifest = RunManifest(
        manifest_id="0f77f009-8565-539a-8c79-5e75a5039546",
        run_id=RunID(UUID(_RUN)),
        pipeline_name="chembl_assay",
        provider="chembl",
        entity="assay",
    )
    outcome = register_pipeline_manifest_location(
        manifest=manifest,
        settings=settings,  # type: ignore[arg-type]
    )
    assert outcome.code == "skipped_write_root_outside_alias"
    store = FileEvidenceLocationStore(report_root=report_root)
    assert (
        store.get(kind=EvidenceLocationKind.PIPELINE, owner="chembl_assay", run_id=_RUN)
        is None
    )


def test_register_pipeline_manifest_writes_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    report_root = tmp_path / "run-reports"
    report_root.mkdir()
    monkeypatch.setenv("BIOETL_RUNTIME_SOURCE_ID", _SOURCE)

    settings = SimpleNamespace(
        data_dir=data_root,
        report_root=report_root,
        runtime_source_id=_SOURCE,
        dashboard_data_root=data_root,
    )
    binding = build_evidence_location_binding_context(settings)  # type: ignore[arg-type]
    assert binding.relative_data_root == "."
    assert binding.runtime_source_id == _SOURCE

    manifest = RunManifest(
        manifest_id="0f77f009-8565-539a-8c79-5e75a5039546",
        run_id=RunID(UUID(_RUN)),
        pipeline_name="chembl_assay",
        provider="chembl",
        entity="assay",
        workflow_run_id=_WF,
    )
    outcome = register_pipeline_manifest_location(
        manifest=manifest,
        settings=settings,  # type: ignore[arg-type]
    )
    assert outcome.code == "registered"
    store = FileEvidenceLocationStore(report_root=report_root)
    found = store.get(
        kind=EvidenceLocationKind.PIPELINE, owner="chembl_assay", run_id=_RUN
    )
    assert found is not None
    assert found.workflow_run_id == _WF
    assert found.relative_data_root == "."


def test_register_workflow_manifest_parent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_root = (tmp_path / "data").resolve()
    data_root.mkdir()
    report_root = tmp_path / "run-reports"
    report_root.mkdir()
    monkeypatch.setenv("BIOETL_RUNTIME_SOURCE_ID", _SOURCE)

    settings = SimpleNamespace(
        data_dir=data_root,
        report_root=report_root,
        runtime_source_id=_SOURCE,
        dashboard_data_root=data_root,
    )
    manifest = WorkflowManifest(
        manifest_id="wf-manifest-1",
        workflow_run_id=RunID(UUID(_WF)),
        execution_fingerprint="f" * 64,
        schema_version="1.0",
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        workflow_name="chembl_assay_pack",
        workflow_version="1",
        launch_context={},
        defaults={},
        selected_step_ids=("step-1",),
        steps=(),
    )
    outcome = register_workflow_manifest_location(
        manifest=manifest,
        settings=settings,  # type: ignore[arg-type]
    )
    assert outcome.code == "registered"
    store = FileEvidenceLocationStore(report_root=report_root)
    found = store.get(
        kind=EvidenceLocationKind.WORKFLOW, owner="chembl_assay_pack", run_id=_WF
    )
    assert found is not None
    assert found.workflow_run_id is None


def test_composite_path_does_not_call_evidence_location_register() -> None:
    """Composite report path must not invent a locator (RF-004 AC)."""
    from bioetl.application.services.run_reports import composite as composite_mod

    source = Path(composite_mod.__file__).read_text(encoding="utf-8")
    assert "evidence_location" not in source
    assert "EvidenceLocation" not in source


def test_resolve_registration_runtime_source_id_reads_env_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Registration identity must honor repository .env.local like Ops HTTP."""
    from bioetl.application.services.run_reports.source_identity import (
        RUNTIME_SOURCE_ID_ENV,
    )
    import bioetl.composition.runtime_builders.evidence_location_registration as mod

    monkeypatch.delenv(RUNTIME_SOURCE_ID_ENV, raising=False)
    (tmp_path / ".env").write_text(
        f"{RUNTIME_SOURCE_ID_ENV}={'b' * 64}\n", encoding="utf-8"
    )
    (tmp_path / ".env.local").write_text(
        f"{RUNTIME_SOURCE_ID_ENV}={_SOURCE}\n", encoding="utf-8"
    )
    monkeypatch.setattr(mod, "_repository_root", lambda: tmp_path)
    settings = SimpleNamespace(runtime_source_id=None)
    assert resolve_registration_runtime_source_id(settings) == _SOURCE  # type: ignore[arg-type]
