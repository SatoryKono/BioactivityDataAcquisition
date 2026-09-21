"""Archive acceptance rejects missing, corrupt, mismatched and incomplete evidence."""

from __future__ import annotations

import json
from threading import Barrier
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
    RunCodeProvenance,
    RunManifest,
)
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane import file_archive_store as archive_module

pytestmark = pytest.mark.unit


def _assessment_case(archive_case, tmp_path, monkeypatch, *, dq="OK"):
    from bioetl.application.services.run_reports.snapshots import publish_snapshot
    from bioetl.application.services.run_reports.writer import write_json
    from bioetl.application.services.run_reports.observations import (
        record_run_observation,
    )
    from bioetl.composition import archive_assessment
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )

    archive, manifest, plan = archive_case
    root = tmp_path / "reports"
    path = (
        root
        / "pipeline"
        / manifest.pipeline_name
        / str(manifest.run_id)
        / "pipeline-run-report.json"
    )
    report = {
        "identity": {
            "pipeline_name": manifest.pipeline_name,
            "run_id": str(manifest.run_id),
            "status": "success",
        },
        "observations": {
            "Control Plane": {
                "verdict": "INCOMPLETE",
                "reason": "archive_evidence_not_recorded",
            },
            "Data Quality": {"verdict": dq},
            "Data Validation": {"verdict": "OK"},
            "Provider": {"verdict": "OK"},
        },
    }
    adapter = FileRunReportStoreAdapter()
    write_json(path, publish_snapshot(report, path, store=adapter), store=adapter)
    archive = FileArchiveStore(archive.data_root, archive.archive_root, root)

    def capture(*_args):
        assert archive.verify(manifest=manifest, plan=plan)[0] is True
        record_run_observation(
            "Control Plane", verdict="OK", reason="archive_restore_verified", facts={}
        )

    monkeypatch.setattr(
        archive_assessment, "create_run_status_capture", lambda *a, **k: capture
    )
    return archive, manifest, plan, path


@pytest.mark.parametrize("dq, verdict", [("OK", "OK"), ("ERROR", "ERROR")])
def test_archive_assessment_commits_verified_revision_and_preserves_history(
    archive_case, tmp_path, monkeypatch, dq, verdict
):
    from bioetl.composition.archive_assessment import refresh_archived_assessment
    from bioetl.domain.run_reports.selected_status import verify_snapshot

    archive, manifest, plan, path = _assessment_case(
        archive_case, tmp_path, monkeypatch, dq=dq
    )
    original = path.read_bytes()
    old_snapshot = json.loads(original)["selected_run_snapshot"]
    old_pack = archive.create(manifest=manifest, plan=plan)
    old_files = {
        p.relative_to(old_pack): p.read_bytes()
        for p in old_pack.rglob("*")
        if p.is_file()
    }
    result = refresh_archived_assessment(
        data_root=archive.data_root,
        archive_root=archive.archive_root,
        report_root=archive.report_root,
        manifest=manifest,
        plan=plan,
        observed_at=datetime.now(UTC),
    )
    assert result == (True, "archive_restore_verified")
    current = json.loads(path.read_bytes())
    snapshot = current["selected_run_snapshot"]
    assert verify_snapshot(snapshot)
    assert snapshot["assessment"]["verdict"] == verdict
    assert snapshot["revision"] != old_snapshot["revision"]
    assert (
        json.loads(
            (
                path.parent / "status-revisions" / f"{old_snapshot['revision']}.json"
            ).read_text()
        )
        == old_snapshot
    )
    assert all(
        (old_pack / relative).read_bytes() == content
        for relative, content in old_files.items()
    )
    assert archive.verify(manifest=manifest, plan=plan)[0] is True


def test_archive_assessment_failed_candidate_keeps_original_report(
    archive_case, tmp_path, monkeypatch
):
    from bioetl.composition.archive_assessment import refresh_archived_assessment

    archive, manifest, plan, path = _assessment_case(
        archive_case, tmp_path, monkeypatch
    )
    archive.create(manifest=manifest, plan=plan)
    original = path.read_bytes()
    revisions = list(path.parent.glob("status-revisions/*.json"))

    def fail(*args, **kwargs):
        raise OSError("candidate archive failed")

    monkeypatch.setattr(FileArchiveStore, "create", fail)
    with pytest.raises(OSError, match="candidate archive failed"):
        refresh_archived_assessment(
            data_root=archive.data_root,
            archive_root=archive.archive_root,
            report_root=archive.report_root,
            manifest=manifest,
            plan=plan,
            observed_at=datetime.now(UTC),
        )
    assert path.read_bytes() == original
    assert list(path.parent.glob("status-revisions/*.json")) == revisions
    assert archive.verify(manifest=manifest, plan=plan)[0] is True


def test_automatic_archive_resolves_default_report_root(
    archive_case, tmp_path, monkeypatch
):
    from bioetl.composition import control_plane_archive as module
    from bioetl.application.services.run_reports import paths
    from bioetl.application.services.execution.pipeline_runner_models import (
        RunResult,
        PipelineRunResult,
    )

    archive, manifest, plan, path = _assessment_case(
        archive_case, tmp_path, monkeypatch
    )
    monkeypatch.setattr(paths, "DEFAULT_REPORT_ROOT", archive.report_root)
    monkeypatch.setattr(
        module.FileRunManifestStore, "get_by_run_id", lambda *a: manifest
    )
    monkeypatch.setattr(
        module.FileControlPlaneArtifactLifecycleStore,
        "plan_for_manifest",
        lambda *a, **k: plan,
    )
    result = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name=manifest.pipeline_name,
        run_id=str(manifest.run_id),
        run_type="backfill",
        manifest_id=manifest.manifest_id,
    )
    assert module.archive_successful_run(
        result=result,
        options=None,
        data_root=archive.data_root,
        archive_root=archive.archive_root,
        report_root=None,
    ) == (True, "archive_restore_verified")
    assert (
        json.loads(path.read_bytes())["selected_run_snapshot"]["assessment"]["verdict"]
        == "OK"
    )


def test_assessment_rejects_source_changed_during_candidate_archive(
    archive_case, tmp_path, monkeypatch
):
    from bioetl.composition.archive_assessment import refresh_archived_assessment

    archive, manifest, plan, path = _assessment_case(
        archive_case, tmp_path, monkeypatch
    )
    archive.create(manifest=manifest, plan=plan)
    original = path.read_bytes()
    create = FileArchiveStore.create

    def changed(store, **kwargs):
        (archive.data_root / "ledger.jsonl").write_text("changed evidence\n")
        return create(store, **kwargs)

    monkeypatch.setattr(FileArchiveStore, "create", changed)
    outcome = refresh_archived_assessment(
        data_root=archive.data_root,
        archive_root=archive.archive_root,
        report_root=archive.report_root,
        manifest=manifest,
        plan=plan,
        observed_at=datetime.now(UTC),
    )
    assert outcome[0] is not True
    assert path.read_bytes() == original


@pytest.fixture
def archive_case(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    manifest = RunManifest(
        manifest_id="manifest-archive",
        execution_fingerprint="fingerprint",
        schema_version="1.0",
        created_at=datetime(2026, 9, 15, tzinfo=UTC),
        run_id=RunID(UUID(int=14)),
        run_type=RunType.BACKFILL,
        pipeline_name="chembl_assay",
        provider="chembl",
        entity="assay",
        launch_context={"archive_policy": {"required": True, "policy_ref": "local-v1"}},
        code_provenance=RunCodeProvenance(),
    )
    (data / "manifest.json").write_text(
        json.dumps(manifest.to_dict()), encoding="utf-8"
    )
    (data / "ledger.jsonl").write_text("ledger evidence\n", encoding="utf-8")
    artifacts = tuple(
        ControlPlaneArtifactRef(
            surface=surface,
            path=str(data / name),
            artifact_id=manifest.manifest_id,
            decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
            reason="selected",
        )
        for name, surface in (
            ("manifest.json", ControlPlaneArtifactSurface.RUN_MANIFEST),
            ("ledger.jsonl", ControlPlaneArtifactSurface.RUN_LEDGER),
        )
    )
    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=manifest.created_at,
        cutoff=manifest.created_at,
        dry_run=True,
        artifacts=artifacts,
    )
    return FileArchiveStore(data, tmp_path / "archive"), manifest, plan


def test_archive_restores_without_changing_source_and_rejects_overwrite(archive_case):
    store, manifest, plan = archive_case
    before = {p.name: p.read_bytes() for p in store.data_root.iterdir()}
    pack = store.create(manifest=manifest, plan=plan)
    assert store.verify(manifest=manifest, plan=plan) == (
        True,
        "archive_restore_verified",
    )
    assert {p.name: p.read_bytes() for p in store.data_root.iterdir()} == before
    assert (pack / "restored/ledger.jsonl").read_bytes() == before["ledger.jsonl"]
    with pytest.raises(FileExistsError):
        store.create(manifest=manifest, plan=plan)


def test_archive_preserves_selected_run_snapshot_and_revisions(archive_case, tmp_path):
    from bioetl.application.services.run_reports.writer import write_pipeline_run_report
    from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )
    from bioetl.interfaces.http.selected_run_status import load_selected_run_status

    store, manifest, plan = archive_case
    root = tmp_path / "reports"
    report = build_pipeline_run_report(
        identity={
            "run_id": str(manifest.run_id),
            "pipeline_name": manifest.pipeline_name,
            "manifest_id": manifest.manifest_id,
            "status": "success",
        },
        metrics={},
    )
    write_pipeline_run_report(report, root=root, store=FileRunReportStoreAdapter())
    store = replace(store, report_root=root)
    pack = store.create(manifest=manifest, plan=plan)
    original = load_selected_run_status(
        pipeline=manifest.pipeline_name, run_id=str(manifest.run_id), root=root
    )
    restored = load_selected_run_status(
        pipeline=manifest.pipeline_name,
        run_id=str(manifest.run_id),
        root=pack / "restored" / "run-reports",
    )
    assert original == restored
    assert store.verify(manifest=manifest, plan=plan)[0] is True
    revision = next(
        (pack / "restored" / "run-reports").rglob("status-revisions/*.json")
    )
    revision.write_text("broken")
    assert store.verify(manifest=manifest, plan=plan)[0] is False


@pytest.mark.parametrize("area", ["files", "restored"])
@pytest.mark.parametrize("damage", ["delete", "corrupt"])
def test_archive_rechecks_files_on_same_reader(archive_case, area, damage):
    store, manifest, plan = archive_case
    pack = store.create(manifest=manifest, plan=plan)
    target = pack / area / "ledger.jsonl"
    if damage == "delete":
        target.unlink()
    else:
        target.write_bytes(b"corrupted")
    assert store.verify(manifest=manifest, plan=plan)[0] is False


@pytest.mark.parametrize(
    "damage", ["identity", "inventory", "duplicate", "traversal", "source", "index"]
)
def test_archive_rejects_mismatched_evidence(archive_case, damage):
    store, manifest, plan = archive_case
    pack = store.create(manifest=manifest, plan=plan)
    index = pack / "index.json"
    payload = json.loads(index.read_text())
    if damage == "identity":
        payload["manifest_sha256"] = "wrong"
    elif damage == "inventory":
        payload["files"].pop()
    elif damage == "duplicate":
        payload["files"].append(payload["files"][0])
    elif damage == "traversal":
        payload["files"][0]["path"] = "../../outside"
    elif damage == "source":
        (store.data_root / "ledger.jsonl").write_text("changed")
    index.write_text("invalid JSON" if damage == "index" else json.dumps(payload))
    assert store.verify(manifest=manifest, plan=plan)[0] is False


def test_archive_missing_is_unknown_and_different_manifest_is_rejected(archive_case):
    store, manifest, plan = archive_case
    assert store.verify(manifest=manifest, plan=plan) == (
        None,
        "archive_evidence_not_recorded",
    )
    other = replace(manifest, execution_fingerprint="different")
    with pytest.raises(ValueError, match="archive_manifest_mismatch"):
        store.create(manifest=other, plan=plan)


def test_archive_root_must_be_separate(archive_case):
    store, manifest, plan = archive_case
    nested = replace(store, archive_root=store.data_root / "archive")
    with pytest.raises(ValueError, match="archive_root_must_be_separate"):
        nested.create(manifest=manifest, plan=plan)


def test_archive_rejects_source_outside_data_root(archive_case, tmp_path):
    store, manifest, plan = archive_case
    outside = tmp_path / "outside.jsonl"
    outside.write_text("not selected data")
    changed = replace(plan.artifacts[-1], path=str(outside))
    with pytest.raises(ValueError):
        store.create(
            manifest=manifest,
            plan=replace(plan, artifacts=(*plan.artifacts[:-1], changed)),
        )


def test_archive_rejects_junction_copies(archive_case, monkeypatch):
    store, manifest, plan = archive_case
    pack = store.create(manifest=manifest, plan=plan)
    monkeypatch.setattr(Path, "is_junction", lambda path: path == pack / "restored")
    assert store.verify(manifest=manifest, plan=plan) == (
        False,
        "archive_evidence_invalid",
    )


def test_archive_copies_contract_sidecar_without_treating_it_as_manifest(archive_case):
    store, manifest, plan = archive_case
    path = store.data_root / f"{manifest.manifest_id}.contract-evidence.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "contract_evidence_v1",
                "manifest_id": manifest.manifest_id,
            }
        )
    )
    sidecar = replace(plan.artifacts[0], path=str(path))
    with_sidecar = replace(plan, artifacts=(*plan.artifacts, sidecar))
    pack = store.create(manifest=manifest, plan=with_sidecar)
    assert store.verify(manifest=manifest, plan=with_sidecar) == (
        True,
        "archive_restore_verified",
    )
    assert (pack / "restored" / path.name).read_bytes() == path.read_bytes()
    path.write_text("{}")
    assert store.verify(manifest=manifest, plan=with_sidecar)[0] is False


@pytest.mark.parametrize(
    "damage", ["missing_manifest", "wrong_identity", "wrong_schema"]
)
def test_archive_sidecar_cannot_replace_manifest_or_change_identity(
    archive_case, damage
):
    store, manifest, plan = archive_case
    path = store.data_root / f"{manifest.manifest_id}.contract-evidence.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "wrong"
                if damage == "wrong_schema"
                else "contract_evidence_v1",
                "manifest_id": "wrong"
                if damage == "wrong_identity"
                else manifest.manifest_id,
            }
        )
    )
    sidecar = replace(plan.artifacts[0], path=str(path))
    artifacts = (
        (sidecar, *plan.artifacts[1:])
        if damage == "missing_manifest"
        else (*plan.artifacts, sidecar)
    )
    with pytest.raises(
        ValueError, match="archive_manifest_missing|archive_contract_evidence_mismatch"
    ):
        store.create(manifest=manifest, plan=replace(plan, artifacts=artifacts))


def test_archive_parallel_reads_keep_checksum_validation(archive_case, monkeypatch):
    store, manifest, plan = archive_case
    barrier = Barrier(2)
    original = archive_module._entry_error

    def concurrent_verify(*args, **kwargs):
        barrier.wait(timeout=5)
        return original(*args, **kwargs)

    monkeypatch.setattr(archive_module, "_entry_error", concurrent_verify)
    pack = store.create(manifest=manifest, plan=plan)
    (pack / "restored/ledger.jsonl").write_bytes(b"changed")
    assert store.verify(manifest=manifest, plan=plan) == (
        False,
        "archive_checksum_mismatch",
    )


@pytest.mark.parametrize("relative", ["../outside", "nested/../../outside"])
def test_archive_containment_rejects_parent_traversal(tmp_path, relative):
    with pytest.raises(ValueError, match="archive_path_outside_root"):
        archive_module._contained_file(tmp_path, relative)


def test_archive_containment_rechecks_parent_links(archive_case, monkeypatch):
    import stat

    store, manifest, plan = archive_case
    pack = store.create(manifest=manifest, plan=plan)
    original = Path.lstat
    linked = pack / "restored"

    def changed_parent(path, *args, **kwargs):
        metadata = original(path, *args, **kwargs)
        if path == linked:
            from types import SimpleNamespace

            return SimpleNamespace(st_mode=stat.S_IFLNK)
        return metadata

    monkeypatch.setattr(Path, "lstat", changed_parent)
    assert store.verify(manifest=manifest, plan=plan) == (
        False,
        "archive_evidence_invalid",
    )


def test_late_run_evidence_creates_new_archive_version(archive_case, tmp_path):
    from bioetl.application.services.run_reports.writer import write_pipeline_run_report
    from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )

    store, manifest, plan = archive_case
    report_root = tmp_path / "reports"
    store = replace(store, report_root=report_root)
    report = build_pipeline_run_report(
        identity={
            "run_id": str(manifest.run_id),
            "pipeline_name": manifest.pipeline_name,
            "status": "success",
        },
        metrics={},
    )
    writer = FileRunReportStoreAdapter()
    write_pipeline_run_report(report, root=report_root, store=writer)
    first = store.create(manifest=manifest, plan=plan)
    first_index = (first / "index.json").read_bytes()
    report = replace(
        report,
        observations={
            "Workflow": {"verdict": "OK", "reason": "late_completion", "facts": {}}
        },
    )
    write_pipeline_run_report(report, root=report_root, store=writer)
    assert store.verify(manifest=manifest, plan=plan) == (
        None,
        "archive_evidence_not_recorded",
    )
    second = store.create(manifest=manifest, plan=plan)
    assert second != first
    assert (first / "index.json").read_bytes() == first_index
    restored_old = replace(store, report_root=first / "restored" / "run-reports")
    assert restored_old.verify(manifest=manifest, plan=plan) == (
        True,
        "archive_restore_verified",
    )
    assert store.verify(manifest=manifest, plan=plan) == (
        True,
        "archive_restore_verified",
    )
