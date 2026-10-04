"""Exercise real HTTP replay checks through the production dependency assembly."""

from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import httpx
import pytest

from bioetl.application.services.run_reports.writer import write_pipeline_run_report
from bioetl.composition.bootstrap.assembly import health_server as assembly
from bioetl.domain.control_plane import (
    ReplayCapability,
    RunInputSnapshotRef,
    RunSourceRef,
)
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.domain.run_reports.pipeline_builder import build_pipeline_run_report
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
    tmp_path, monkeypatch, damage, expected, pipeline, portable_ref
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
                        immutable_uri="bronze://batch.jsonl",
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
                "sha256": sha256(child_path.read_bytes()).hexdigest(),
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
