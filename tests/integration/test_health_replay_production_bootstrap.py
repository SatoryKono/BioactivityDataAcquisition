"""Exercise real HTTP replay checks through the production dependency assembly."""

from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import httpx
from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
import json
import pytest

from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.composition.bootstrap.assembly import health_server as assembly
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.domain.run_reports.pipeline_report_assembly import (
    build_pipeline_run_report,
)
from bioetl.domain.run_reports.selected_status import DOMAINS
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)
from bioetl.interfaces.cli.commands.domains.health import server_integration_deps as cli
from bioetl.interfaces.http import run_report_ops
from tests.unit.application.services.run_manifest_test_support import (
    RunManifestOverrides,
    make_run_manifest,
)

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("pipeline", ["chembl_activity", "composite_activity"])
@pytest.mark.parametrize("portable_ref", [False, True])
@pytest.mark.parametrize("qualified_snapshot", [False, True])
@pytest.mark.parametrize(
    "damage,expected",
    [
        ("none", "READY"),
        ("missing_config", "INSUFFICIENT"),
        ("missing_lock", "INSUFFICIENT"),
        ("missing_bronze", "INSUFFICIENT"),
        ("changed_lock", "BLOCKED"),
        ("changed_bronze", "BLOCKED"),
        ("changed_config", "BLOCKED"),
        ("missing_child", "BLOCKED"),
        ("changed_child", "BLOCKED"),
        ("failed_child", "BLOCKED"),
        ("warn_child", "BLOCKED"),
        ("lineage_conflict", "BLOCKED"),
        ("incomplete_parent", "INSUFFICIENT"),
        ("wrong_selector", "INSUFFICIENT"),
        ("child_path_escape", "BLOCKED"),
        ("child_identity_mismatch", "BLOCKED"),
    ],
)
async def test_production_http_verifies_saved_replay_objects(
    tmp_path, monkeypatch, damage, expected, pipeline, portable_ref, qualified_snapshot
):
    data, reports = tmp_path / "data", tmp_path / "reports"
    settings = SimpleNamespace(
        data_dir=str(data),
        report_root=reports,
        archive_root=None,
        prometheus_url=None,
        runtime_source_id=None,
    )
    monkeypatch.setattr(assembly, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(run_report_ops, "_effective_root", lambda root: reports)
    deps = assembly.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: AsyncMock(),
        data_root=data,
    )
    control = data / "output" / "control"
    run_id = RunID(UUID("11111111-1111-4111-8111-111111111111"))
    config = {"identity_version": "effective-config-v1", "config_data": {"limit": 100}}
    FileEffectiveConfigArtifactStore(control / "effective_config").save(
        artifact_id="saved-config",
        run_id=run_id,
        payload={
            "artifact_id": "saved-config",
            "semantic_artifact": {"effective_execution_config": config},
        },
    )
    lock_bytes, bronze_bytes = b"original lock", b"original bronze"
    lock_hash = sha256(lock_bytes).hexdigest()
    paths = {
        "config": control / "effective_config" / "saved-config.json",
        "lock": control / "dependency_locks" / lock_hash,
        "bronze": data / "output" / "bronze" / "chembl" / "activity" / "batch.jsonl",
    }
    for key, content in (("lock", lock_bytes), ("bronze", bronze_bytes)):
        paths[key].parent.mkdir(parents=True, exist_ok=True)
        paths[key].write_bytes(content)
    manifest = make_run_manifest(
        run_id=run_id,
        limit=100,
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="batch",
                        content_hash=sha256(bronze_bytes).hexdigest(),
                        immutable_uri=(
                            "bronze://chembl/activity/batch.jsonl"
                            if qualified_snapshot
                            else "bronze://batch.jsonl"
                        ),
                    ),
                ),
            ),
        ),
        overrides=RunManifestOverrides(
            pipeline_name=pipeline,
            provider="composite" if pipeline.startswith("composite_") else "chembl",
            effective_config_hash=stable_json_hash(config),
            effective_config_artifact_id="saved-config",
            dependency_lock_hash="sha256:" + lock_hash,
        ),
    )
    manifest = replace(
        manifest,
        objects={
            "effective_config_hash": True,
            "dependency_lock_hash": True,
            "input_snapshot_fingerprint": True,
        },
    )
    deps.run_manifest_port.save(manifest)
    draft = build_pipeline_run_report(
        identity={
            "pipeline_name": pipeline,
            "run_id": str(run_id),
            "status": "success",
            "run_type": "incremental",
            "started_at": "2026-10-03T00:00:00+00:00",
            "completed_at": "2026-10-03T00:01:00+00:00",
        },
        metrics={},
    )
    report = replace(
        draft,
        observations={
            name: {"verdict": "OK", "reason": "checked", "facts": {}}
            for name in DOMAINS[1:]
        },
    )
    child_id = "22222222-2222-4222-8222-222222222222"
    child_manifest = replace(
        manifest,
        run_id=RunID(UUID(child_id)),
        manifest_id="child-manifest",
        pipeline_name="chembl_activity",
        provider="chembl",
    )
    deps.run_manifest_port.save(child_manifest)
    child_identity = {
        **report.identity,
        "pipeline_name": "chembl_activity",
        "run_id": child_id,
        "manifest_id": child_manifest.manifest_id,
    }
    child_observations = dict(report.observations)
    if damage == "warn_child":
        child_observations["Provider"] = {
            "verdict": "WARN",
            "reason": "health_check_degraded",
            "facts": {},
        }
    if damage == "failed_child":
        child_identity["status"] = "failed"
    if damage == "lineage_conflict":
        child_observations["Control Plane"] = {
            "verdict": "ERROR",
            "reason": "lineage_identity_mismatch",
            "facts": {},
        }
    if damage == "child_identity_mismatch":
        child_identity["manifest_id"] = "wrong-manifest"
    child = replace(report, identity=child_identity, observations=child_observations)
    child_path = write_pipeline_run_report(
        child, root=reports, store=deps.run_report_store
    ).json_path
    paths["child"] = child_path
    report = replace(
        report,
        artifacts=(
            {
                "kind": "composite_child_run_report",
                "pipeline_name": "chembl_activity",
                "run_id": child_id,
                "manifest_id": child_manifest.manifest_id,
                "ref": f"pipeline/chembl_activity/{child_id}/pipeline-run-report.json"
                if portable_ref
                else str(child_path),
                "sha256": canonical_report_sha256(
                    json.loads(child_path.read_text(encoding="utf-8"))
                ),
            },
        ),
    )
    if damage == "incomplete_parent":
        report = replace(report, observations={})
    if damage == "child_path_escape":
        report.artifacts[0]["ref"] = str(tmp_path / "foreign.json")
    written = write_pipeline_run_report(
        report, root=reports, store=deps.run_report_store
    )
    report_before = written.json_path.read_bytes()
    if damage.startswith(("missing_", "changed_")):
        operation, key = damage.split("_")
        if operation == "missing":
            paths[key].unlink()
        elif key == "config":
            paths[key].write_text(paths[key].read_text().replace("100", "101"))
        else:
            paths[key].write_bytes(b"tampered")
    server = cli.build_health_server(
        host="127.0.0.1", port=0, deps=deps, quarantine_service=None
    )
    await server.start()
    try:
        port = server._server.sockets[0].getsockname()[1]
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(
                f"http://127.0.0.1:{port}/ops/observability/selected-run-status",
                params={
                    "pipeline": pipeline,
                    "run_id": str(run_id),
                    "run_type": "rebuild"
                    if damage == "wrong_selector"
                    else "incremental",
                },
            )
            response.raise_for_status()
            result = response.json()
            assert result["replay_readiness"][0]["verdict"] == expected, result
            if damage == "none":
                assert result["verdict"] == "OK", result
                assert result["evidence_completeness"] == "COMPLETE", result
        assert written.json_path.read_bytes() == report_before
        if damage.startswith("missing_"):
            assert not paths[damage.split("_")[1]].exists()
    finally:
        await server.stop()


# Anchor IDs from #12679 / #12678 (machine-local workflow-limit100 series).
_TARGET_WORKFLOW = "3dc8ffe4-305b-5d4b-a945-fe8e78f03828"
_TARGET_RUN = "ac0b4e22-6a6e-5b7e-818e-106aeaf41390"
_TARGET_MANIFEST = "0f77f009-8565-539a-8c79-5e75a5039546"
_FOREIGN_WORKFLOW = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
_FOREIGN_RUN = "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"
_FOREIGN_MANIFEST = "cccccccc-dddd-4eee-8fff-000000000000"


def _materialize_isolated_assay_root(
    *,
    data_root,
    run_id: str,
    manifest_id: str,
    workflow_id: str,
    lock_bytes: bytes,
    bronze_bytes: bytes,
    config_limit: int,
):
    """Write config/lock/Bronze under one isolated data root (manifest saved later)."""
    control = data_root / "output" / "control"
    config = {
        "identity_version": "effective-config-v1",
        "config_data": {"limit": config_limit},
    }
    FileEffectiveConfigArtifactStore(control / "effective_config").save(
        artifact_id=f"cfg-{run_id[:8]}",
        run_id=RunID(UUID(run_id)),
        payload={
            "artifact_id": f"cfg-{run_id[:8]}",
            "semantic_artifact": {"effective_execution_config": config},
        },
    )
    lock_hash = sha256(lock_bytes).hexdigest()
    lock_path = control / "dependency_locks" / lock_hash
    bronze_path = data_root / "output" / "bronze" / "chembl" / "assay" / "batch.jsonl"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    bronze_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(lock_bytes)
    bronze_path.write_bytes(bronze_bytes)
    manifest = make_run_manifest(
        manifest_id=manifest_id,
        run_id=RunID(UUID(run_id)),
        limit=config_limit,
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="assay",
                pipeline_name="chembl_assay",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="batch",
                        content_hash=sha256(bronze_bytes).hexdigest(),
                        immutable_uri="bronze://chembl/assay/batch.jsonl",
                    ),
                ),
            ),
        ),
        overrides=RunManifestOverrides(
            pipeline_name="chembl_assay",
            provider="chembl",
            entity="assay",
            effective_config_hash=stable_json_hash(config),
            effective_config_artifact_id=f"cfg-{run_id[:8]}",
            dependency_lock_hash="sha256:" + lock_hash,
            launch_context={
                "limit": config_limit,
                "strict_exact_replay_supported": True,
            },
            contract_ref="chembl.assay",
            dq_policy_ref="chembl_assay.gold",
        ),
    )
    manifest = replace(
        manifest,
        workflow_run_id=RunID(UUID(workflow_id)),
        workflow_name="workflow-limit100",
        workflow_step_id="run_chembl_assay",
        objects={
            "effective_config_hash": True,
            "dependency_lock_hash": True,
            "input_snapshot_fingerprint": True,
        },
    )
    return {
        "manifest": manifest,
        "paths": {
            "config": control / "effective_config" / f"cfg-{run_id[:8]}.json",
            "lock": lock_path,
            "bronze": bronze_path,
        },
    }


def _write_assay_report(*, reports, run_id: str, workflow_id: str, store):
    draft = build_pipeline_run_report(
        identity={
            "pipeline_name": "chembl_assay",
            "run_id": run_id,
            "status": "success",
            "run_type": "incremental",
            "workflow_id": workflow_id,
            "started_at": "2026-11-02T14:44:03+00:00",
            "completed_at": "2026-11-02T14:45:03+00:00",
        },
        metrics={"bronze_rows": 100, "silver_rows": 100, "gold_rows": 100},
    )
    report = replace(
        draft,
        observations={
            name: {"verdict": "OK", "reason": "checked", "facts": {"rows": 100}}
            for name in DOMAINS[1:]
        },
    )
    return write_pipeline_run_report(report, root=reports, store=store)


async def _query_selected_run(*, deps, reports, monkeypatch, run_id: str):
    monkeypatch.setattr(run_report_ops, "_effective_root", lambda root: reports)
    server = cli.build_health_server(
        host="127.0.0.1", port=0, deps=deps, quarantine_service=None
    )
    await server.start()
    try:
        port = server._server.sockets[0].getsockname()[1]
        async with httpx.AsyncClient(trust_env=False) as client:
            response = await client.get(
                f"http://127.0.0.1:{port}/ops/observability/selected-run-status",
                params={"pipeline": "chembl_assay", "run_id": run_id},
            )
            response.raise_for_status()
            return response.json()
    finally:
        await server.stop()


async def test_isolated_manifest_lost_under_default_data_root(tmp_path, monkeypatch):
    """RF-001: shared report is COMPLETE, but default data root misses the manifest.

    Layout mirrors the diagnosed production split:
    - shared ``reports/`` holds the successful pipeline report;
    - isolated ``data/workflow-…/chembl_assay/`` holds the control-plane manifest;
    - default ``data/`` has no index entry for the target run_id.
    A second foreign isolated root proves evidence cannot be borrowed.
    """
    default_data = tmp_path / "data"
    reports = tmp_path / "reports"
    target_root = (
        default_data / "workflow-limit100-20261102T144403Z" / "chembl_assay"
    )
    foreign_root = (
        default_data / "workflow-limit100-foreign-20261102T150000Z" / "chembl_assay"
    )
    default_data.mkdir(parents=True)
    reports.mkdir(parents=True)

    target = _materialize_isolated_assay_root(
        data_root=target_root,
        run_id=_TARGET_RUN,
        manifest_id=_TARGET_MANIFEST,
        workflow_id=_TARGET_WORKFLOW,
        lock_bytes=b"target-lock-bytes\n",
        bronze_bytes=b'{"assay_id":"CHEMBL1"}\n',
        config_limit=100,
    )
    foreign = _materialize_isolated_assay_root(
        data_root=foreign_root,
        run_id=_FOREIGN_RUN,
        manifest_id=_FOREIGN_MANIFEST,
        workflow_id=_FOREIGN_WORKFLOW,
        lock_bytes=b"foreign-lock-bytes\n",
        bronze_bytes=b'{"assay_id":"CHEMBL999"}\n',
        config_limit=50,
    )

    settings = SimpleNamespace(
        data_dir=str(default_data),
        report_root=reports,
        archive_root=None,
        prometheus_url=None,
        runtime_source_id=None,
    )
    monkeypatch.setattr(assembly, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    # Persist manifests only into their isolated stores (not the default root).
    target_deps = assembly.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: AsyncMock(),
        data_root=target_root,
    )
    foreign_deps = assembly.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: AsyncMock(),
        data_root=foreign_root,
    )
    target_deps.run_manifest_port.save(target["manifest"])
    foreign_deps.run_manifest_port.save(foreign["manifest"])

    written = _write_assay_report(
        reports=reports,
        run_id=_TARGET_RUN,
        workflow_id=_TARGET_WORKFLOW,
        store=target_deps.run_report_store,
    )
    _write_assay_report(
        reports=reports,
        run_id=_FOREIGN_RUN,
        workflow_id=_FOREIGN_WORKFLOW,
        store=foreign_deps.run_report_store,
    )
    report_before = written.json_path.read_bytes()
    target_bytes_before = {
        name: path.read_bytes() for name, path in target["paths"].items()
    }
    foreign_bytes_before = {
        name: path.read_bytes() for name, path in foreign["paths"].items()
    }

    # Bug surface: production bootstrap bound to the shared default data root.
    default_deps = assembly.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: AsyncMock(),
        data_root=default_data,
    )
    assert default_deps.run_manifest_port.get_by_run_id(RunID(UUID(_TARGET_RUN))) is None
    assert (
        target_deps.run_manifest_port.get_by_run_id(RunID(UUID(_TARGET_RUN)))
        is not None
    )

    buggy = await _query_selected_run(
        deps=default_deps, reports=reports, monkeypatch=monkeypatch, run_id=_TARGET_RUN
    )
    checks = {item["code"]: item for item in buggy["replay_checks"]}
    assert buggy["verdict"] == "OK", buggy
    assert buggy["execution_state"] == "SUCCESS", buggy
    assert buggy["evidence_completeness"] == "COMPLETE", buggy
    assert buggy["replay_readiness_now"] == "INSUFFICIENT", buggy
    assert checks["manifest_not_recorded"]["result"] == "unknown", checks
    # Run Explorer maps INSUFFICIENT → INCOMPLETE via presentation layer.
    from bioetl.interfaces.http._recent_run_presentation import _replay_status

    assert _replay_status(buggy) == "INCOMPLETE"
    initial_revision = buggy["revision"]
    initial_digest = sha256(report_before).hexdigest()

    # Control: same HTTP path with the correct isolated data root → READY.
    ready = await _query_selected_run(
        deps=target_deps, reports=reports, monkeypatch=monkeypatch, run_id=_TARGET_RUN
    )
    ready_checks = {item["code"]: item for item in ready["replay_checks"]}
    assert ready["replay_readiness_now"] == "READY", ready
    assert ready["verdict"] == "OK", ready
    assert ready["evidence_completeness"] == "COMPLETE", ready
    assert ready_checks["effective_config_hash"]["result"] == "pass"
    assert ready_checks["dependency_lock_hash"]["result"] == "pass"
    assert ready_checks["input_snapshot_fingerprint"]["result"] == "pass"
    assert ready_checks["exact_replay_family"]["result"] == "pass"
    assert ready_checks["exact_replay_family"]["reason"] == "exact_replay_supported"
    assert "manifest_not_recorded" not in ready_checks
    assert _replay_status(ready) == "OK"

    # Foreign isolated evidence must not satisfy the target run.
    borrowed = await _query_selected_run(
        deps=foreign_deps, reports=reports, monkeypatch=monkeypatch, run_id=_TARGET_RUN
    )
    assert borrowed["replay_readiness_now"] == "INSUFFICIENT", borrowed
    borrowed_checks = {item["code"]: item for item in borrowed["replay_checks"]}
    assert borrowed_checks["manifest_not_recorded"]["result"] == "unknown"

    # Re-reads must not mutate report or isolated objects.
    reread = await _query_selected_run(
        deps=default_deps, reports=reports, monkeypatch=monkeypatch, run_id=_TARGET_RUN
    )
    assert reread["revision"] == initial_revision
    assert reread["replay_readiness_now"] == "INSUFFICIENT"
    assert written.json_path.read_bytes() == report_before
    assert sha256(written.json_path.read_bytes()).hexdigest() == initial_digest
    assert {
        name: path.read_bytes() for name, path in target["paths"].items()
    } == target_bytes_before
    assert {
        name: path.read_bytes() for name, path in foreign["paths"].items()
    } == foreign_bytes_before
