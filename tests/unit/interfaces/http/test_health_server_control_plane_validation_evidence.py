"""HTTP routing tests for control-plane validation evidence endpoints."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.evidence import (
    CONTROL_PLANE_EVIDENCE_CONTRACT,
    FAILURE_REASON_CATEGORIES,
    ControlPlaneEvidenceService,
)
from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_store import (
    FileControlPlaneArtifactLifecycleStore,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.interfaces.http.health_server import HealthServer
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore

pytestmark = pytest.mark.unit


def _manifest() -> RunManifest:
    run_id = RunID(UUID("00000000-0000-0000-0000-000000008500"))
    return RunManifest(
        manifest_id="manifest-8500",
        execution_fingerprint="fingerprint-8500",
        schema_version="1.0",
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"required_persistence_profile": "degraded_observable"},
        code_provenance=RunCodeProvenance(
            contract_ref="chembl.activity",
            contract_version="1.0.0",
        ),
    )


async def _get_json(server: HealthServer, path: str) -> tuple[int, dict[str, object]]:
    assert server._server is not None
    sockets = server._server.sockets
    assert sockets is not None
    port = int(sockets[0].getsockname()[1])
    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    try:
        writer.write(f"GET {path} HTTP/1.1\r\nHost: localhost\r\n\r\n".encode())
        await writer.drain()
        response_line = (await reader.readline()).decode().strip()
        status_code = int(response_line.split(" ", 2)[1])
        headers: dict[str, str] = {}
        while True:
            line = await reader.readline()
            if line in {b"\r\n", b"\n", b""}:
                break
            key, value = line.decode().split(":", 1)
            headers[key.strip().lower()] = value.strip()
        body = await reader.read(int(headers.get("content-length", "0")))
        return status_code, json.loads(body)
    finally:
        writer.close()
        await writer.wait_closed()


@pytest.mark.asyncio
async def test_all_control_plane_validation_routes_publish_stable_contract(
    tmp_path,
) -> None:
    manifest = _manifest()
    manifests = InMemoryRunManifestStore()
    manifests.save(manifest)
    ledger = InMemoryRunLedgerStore()
    checkpoints = LocalCheckpointAdapter(tmp_path / "checkpoints")
    await checkpoints.save(
        manifest.pipeline_name,
        manifest.run_id,
        {
            "manifest_id": manifest.manifest_id,
            "pipeline_name": manifest.pipeline_name,
            "run_type": manifest.run_type.value,
            "execution_fingerprint": manifest.execution_fingerprint,
        },
    )
    service = ControlPlaneEvidenceService(
        ledger_port=ledger,
        lineage_store=FileLineageStore(tmp_path / "control" / "lineage"),
        lifecycle_planner=FileControlPlaneArtifactLifecycleStore(
            tmp_path / "control"
        ),
    )
    server = HealthServer(
        host="127.0.0.1",
        port=0,
        checkpoint_port=checkpoints,
        run_manifest_port=manifests,
        run_ledger_port=ledger,
        control_plane_evidence_service=service,
    )
    await server.start()
    try:
        for endpoint in (
            "checkpoint-validation",
            "manifest-validation",
            "lineage-validation",
            "retention-compliance",
            "failure-reasons",
        ):
            status, payload = await _get_json(
                server,
                f"/ops/control-plane/{endpoint}?pipeline={manifest.pipeline_name}"
                f"&run_type={manifest.run_type.value}&run_id={manifest.run_id}",
            )
            assert status == 200
            assert payload["contract"] == CONTROL_PLANE_EVIDENCE_CONTRACT
            assert payload["endpoint"] == endpoint
            assert payload["run_id"] == str(manifest.run_id)
            assert payload["manifest_id"] == manifest.manifest_id
        _, failure_payload = await _get_json(
            server,
            "/ops/control-plane/failure-reasons?pipeline=chembl_activity"
            f"&run_id={manifest.run_id}",
        )
        assert [row["category"] for row in failure_payload["rows"]] == list(
            FAILURE_REASON_CATEGORIES
        )
    finally:
        await server.stop()
        await checkpoints.aclose()


class _CorruptCheckpointPort:
    async def load_for_manifest_id(self, manifest_id: str) -> object:
        raise ValueError("raw corrupt checkpoint secret")


@pytest.mark.asyncio
async def test_checkpoint_parse_failure_has_stable_reason_without_raw_error() -> None:
    manifest = _manifest()
    manifests = InMemoryRunManifestStore()
    manifests.save(manifest)
    server = HealthServer(
        host="127.0.0.1",
        port=0,
        checkpoint_port=_CorruptCheckpointPort(),  # type: ignore[arg-type]
        run_manifest_port=manifests,
        control_plane_evidence_service=ControlPlaneEvidenceService(),
    )
    await server.start()
    try:
        status, payload = await _get_json(
            server,
            "/ops/control-plane/checkpoint-validation?pipeline=chembl_activity"
            f"&run_id={manifest.run_id}",
        )

        assert status == 200
        assert payload["status"] == "ERROR"
        assert any(
            row.get("reason") == "checkpoint_parse_error"
            for row in payload["rows"]
        )
        assert "raw corrupt checkpoint secret" not in str(payload)
    finally:
        await server.stop()


@pytest.mark.asyncio
async def test_missing_evidence_service_returns_unknown_table_contract() -> None:
    server = HealthServer(host="127.0.0.1", port=0)
    await server.start()
    try:
        status, payload = await _get_json(
            server,
            "/ops/control-plane/manifest-validation?pipeline=chembl_activity",
        )

        assert status == 503
        assert payload["contract"] == CONTROL_PLANE_EVIDENCE_CONTRACT
        assert payload["status"] == "UNKNOWN"
        assert payload["rows"][0]["reason"] == (
            "control_plane_evidence_service_unavailable"
        )
    finally:
        await server.stop()
