# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for health-server control-plane checkpoint freshness endpoint."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio

from bioetl.domain.control_plane import (
    ReplayCapability,
    RunCodeProvenance,
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.run_ledger import (
    COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
)
from bioetl.domain.normalization import compute_input_snapshot_identity_fingerprint
from bioetl.domain.types import RunType
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.interfaces.http import _health_server_routing_support
from bioetl.interfaces.http.health_server import HealthServer
from tests.helpers.clock import fixed_test_clock
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite


pytestmark = pytest.mark.unit


class TestHealthServerControlPlaneCheckpointFreshness:
    """Tests for /ops/control-plane/checkpoint-freshness endpoint."""

    @pytest_asyncio.fixture(loop_scope="module")
    async def running_server_with_run_catalog(
        self,
        tmp_path_factory: pytest.TempPathFactory,
    ) -> AsyncGenerator[tuple[HealthServer, InMemoryRunManifestStore], None]:
        """Start server with an in-memory control-plane run catalog."""
        manifest_store = InMemoryRunManifestStore()
        ledger_store = InMemoryRunLedgerStore()
        checkpoint_port = LocalCheckpointAdapter(
            base_path=tmp_path_factory.mktemp("control-plane-checkpoints")
        )
        created_at = datetime(2026, 5, 12, 8, 21, tzinfo=UTC)
        run_id_1 = deterministic_run_uuid_from_callsite(
            "test_health_server_control_plane_checkpoint_freshness"
        )
        run_id_2 = deterministic_run_uuid_from_callsite(
            "test_health_server_control_plane_checkpoint_freshness"
        )
        run_id_3 = deterministic_run_uuid_from_callsite(
            "test_health_server_control_plane_checkpoint_freshness"
        )
        run_id_4 = deterministic_run_uuid_from_callsite(
            "test_health_server_control_plane_checkpoint_freshness"
        )
        input_snapshot = RunInputSnapshotRef(
            snapshot_id="snapshot-chembl-activity-1",
            content_hash="hash-chembl-activity-1",
            immutable_uri="file:///snapshots/chembl/activity/1.jsonl",
            query_fingerprint="query-chembl-activity-1",
        )
        input_snapshot_fingerprint = compute_input_snapshot_identity_fingerprint(
            [
                {
                    "snapshot_id": input_snapshot.snapshot_id,
                    "content_hash": input_snapshot.content_hash,
                    "immutable_uri": input_snapshot.immutable_uri,
                    "query_fingerprint": input_snapshot.query_fingerprint,
                }
            ]
        )
        assert input_snapshot_fingerprint is not None
        manifest_store.save(
            RunManifest(
                manifest_id="manifest-1",
                execution_fingerprint="fingerprint-1",
                schema_version="1.0",
                created_at=created_at,
                run_id=run_id_1,
                run_type=RunType.INCREMENTAL,
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
                launch_context={"limit": 10},
                runtime_config={"run_type": "incremental"},
                resolved_config={"pipeline_name": "chembl_activity"},
                code_provenance=RunCodeProvenance(
                    pipeline_version="1.0.0",
                    git_commit="abc1234",
                    config_hash="deadbeef",
                ),
            )
        )
        manifest_store.save(
            RunManifest(
                manifest_id="manifest-2",
                execution_fingerprint="fingerprint-2",
                schema_version="1.0",
                created_at=created_at,
                run_id=run_id_2,
                run_type=RunType.BACKFILL,
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
                launch_context={"limit": 10},
                runtime_config={
                    "run_type": "backfill",
                    "identity_graph_diagnostics": {
                        "identity_graph_complete": True,
                        "correlation_anchor_gaps": {},
                        "exact_replay_eligible": True,
                        "exact_replay_blockers": [],
                        "replay_capability": "exact_replay_supported",
                    },
                    "checkpoint_metadata": {
                        "manifest_id": "manifest-2",
                        "execution_fingerprint": "fingerprint-2",
                        "effective_config_hash": (
                            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                        ),
                        "effective_config_artifact_id": (
                            "effective-config-chembl-activity-2"
                        ),
                        "input_snapshot_fingerprint": input_snapshot_fingerprint,
                    },
                },
                resolved_config={"pipeline_name": "chembl_activity"},
                code_provenance=RunCodeProvenance(
                    pipeline_version="1.0.0",
                    git_commit="def5678",
                    config_hash="feedface",
                    resolved_config_hash="feedface",
                    effective_config_hash=(
                        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                    ),
                    effective_config_artifact_id="effective-config-chembl-activity-2",
                    contract_ref="chembl.activity",
                    contract_version="2026.05",
                    contract_schema_hash=(
                        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                    ),
                    dq_policy_ref="chembl.activity.dq",
                    rule_bundle_version="2026.05",
                    dq_contract_compatibility_hash=(
                        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
                    ),
                ),
                replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
                source_refs=(
                    RunSourceRef(
                        provider="chembl",
                        entity="activity",
                        pipeline_name="chembl_activity",
                        query="limit=10",
                        input_snapshots=(input_snapshot,),
                    ),
                ),
                planned_artifacts=(),
            )
        )
        manifest_store.save(
            RunManifest(
                manifest_id="manifest-3",
                execution_fingerprint="fingerprint-3",
                schema_version="1.0",
                created_at=created_at,
                run_id=run_id_3,
                run_type=RunType.INCREMENTAL,
                pipeline_name="pubchem_compound",
                provider="pubchem",
                entity="compound",
                launch_context={"limit": 10},
                runtime_config={"run_type": "incremental"},
                resolved_config={"pipeline_name": "pubchem_compound"},
                code_provenance=RunCodeProvenance(
                    pipeline_version="1.0.0",
                    git_commit="ghi9012",
                    config_hash="cafebabe",
                ),
            )
        )
        manifest_store.save(
            RunManifest(
                manifest_id="manifest-4",
                execution_fingerprint="fingerprint-4",
                schema_version="1.0",
                created_at=created_at,
                run_id=run_id_4,
                run_type=RunType.REBUILD,
                pipeline_name="composite_publication",
                provider="composite",
                entity="publication",
                launch_context={"workflow_name": "workflow_composite_publication"},
                runtime_config={
                    "run_type": "rebuild",
                    "exact_replay": True,
                    "checkpoint_metadata": {
                        "manifest_id": "manifest-4",
                        "execution_fingerprint": "fingerprint-4",
                        "effective_config_hash": "checkpoint-different-hash",
                        "effective_config_artifact_id": "effective-config-composite-4",
                        "composite_run_identity": "composite-run-4",
                    },
                    "cross_validation_rule_ids": ["publication-nullification-v1"],
                },
                resolved_config={"pipeline_name": "composite_publication"},
                code_provenance=RunCodeProvenance(
                    pipeline_version="2.0.0",
                    git_commit="jkl3456",
                    config_hash="badc0de",
                    resolved_config_hash="badc0de",
                    effective_config_hash=(
                        "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
                    ),
                    effective_config_artifact_id="effective-config-composite-4",
                    contract_ref="composite.publication",
                    contract_version="2026.05",
                    contract_schema_hash=(
                        "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
                    ),
                ),
            )
        )
        ledger_store.append(
            RunLedgerEntry(
                entry_id="ledger-1",
                manifest_id="manifest-1",
                run_id=run_id_1,
                event_type=RUN_FINISHED_EVENT,
                occurred_at=created_at + timedelta(minutes=1),
                status="success",
            )
        )
        ledger_store.append(
            RunLedgerEntry(
                entry_id="ledger-4",
                manifest_id="manifest-4",
                run_id=run_id_4,
                event_type=COMPOSITE_DEPENDENCY_COMPLETED_EVENT,
                occurred_at=created_at + timedelta(minutes=4),
                status="success",
                details={"component_run_id": str(run_id_1)},
            )
        )
        ledger_store.append(
            RunLedgerEntry(
                entry_id="ledger-2",
                manifest_id="manifest-2",
                run_id=run_id_2,
                event_type=RUN_FAILED_EVENT,
                occurred_at=created_at + timedelta(minutes=5),
                status="failed",
            )
        )
        ledger_store.append(
            RunLedgerEntry(
                entry_id="ledger-3",
                manifest_id="manifest-3",
                run_id=run_id_3,
                event_type=RUN_FINISHED_EVENT,
                occurred_at=created_at + timedelta(minutes=3),
                status="success",
            )
        )
        test_clock = fixed_test_clock()
        now = test_clock.now()
        await checkpoint_port.save(
            "chembl_activity",
            run_id_1,
            {
                "manifest_id": "manifest-1",
                "execution_fingerprint": "fingerprint-1",
                "checkpoint_saved_at_epoch_seconds": (
                    now - timedelta(hours=1)
                ).timestamp(),
            },
        )
        await checkpoint_port.save(
            "chembl_activity",
            run_id_2,
            {
                "manifest_id": "manifest-2",
                "checkpoint_saved_at_epoch_seconds": (
                    now - timedelta(minutes=2)
                ).timestamp(),
            },
        )

        with patch.object(
            _health_server_routing_support,
            "current_utc_time",
            test_clock.now,
        ):
            server = HealthServer(
                host="127.0.0.1",
                port=0,
                checkpoint_port=checkpoint_port,
                run_manifest_port=manifest_store,
                run_ledger_port=ledger_store,
            )
            await server.start()
            yield server, manifest_store
            await server.stop()
            await checkpoint_port.aclose()

    @staticmethod
    def _get_server_port(server: HealthServer) -> int:
        """Get the actual port of the running server."""
        assert server._server is not None
        sockets = server._server.sockets
        assert sockets is not None
        return int(sockets[0].getsockname()[1])

    async def _send_request(
        self, port: int, method: str, path: str
    ) -> tuple[int, str, str]:
        """Send request and return status code, status text, and body."""
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            request = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n\r\n"
            writer.write(request.encode())
            await writer.drain()

            response_line = await reader.readline()
            response_str = response_line.decode("utf-8").strip()
            parts = response_str.split(" ", 2)
            status_code = int(parts[1])
            status_text = parts[2] if len(parts) > 2 else ""

            headers = {}
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
                header_line = line.decode("utf-8").strip()
                if ":" in header_line:
                    key, value = header_line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            content_length = int(headers.get("content-length", 0))
            body = await reader.read(content_length)
            return status_code, status_text, body.decode("utf-8")
        finally:
            writer.close()
            await writer.wait_closed()

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_checkpoint_freshness_returns_latest_pointer(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Checkpoint freshness without run_id should use the mutable latest pointer."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/checkpoint-freshness?pipeline=chembl_activity",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "OK"
        assert data["evidence_source"] == "mutable_latest_pointer"
        assert data["manifest_id"] == "manifest-2"
        assert data["checkpoint_present"] is True
        assert data["age_seconds"] is not None
        assert 0 <= float(data["age_seconds"]) < 900

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_checkpoint_freshness_falls_back_to_latest_pipeline_history(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Missing mutable pointer should fall back to latest immutable pipeline history."""
        server, _manifest_store = running_server_with_run_catalog
        assert server._checkpoint_port is not None
        port = self._get_server_port(server)
        pipeline = "chembl_target"
        run_id = deterministic_run_uuid_from_callsite(
            "test_health_server_control_plane_checkpoint_freshness"
        )
        await server._checkpoint_port.save(
            pipeline,
            run_id,
            {
                "offset": 42,
                "checkpoint_saved_at_epoch_seconds": (
                    fixed_test_clock().now() - timedelta(minutes=3)
                ).timestamp(),
            },
        )
        await server._checkpoint_port.delete(pipeline)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            f"/ops/control-plane/checkpoint-freshness?pipeline={pipeline}"
            "&run_type=incremental&run_id=-",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["pipeline"] == pipeline
        assert data["status"] == "OK"
        assert data["checkpoint_present"] is True
        assert data["checkpoint_run_id"] == str(run_id)
        assert data["evidence_source"] == "immutable_pipeline_history_latest"
        assert data["age_seconds"] is not None

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_checkpoint_freshness_prefers_exact_run_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Exact run_id scope must use immutable checkpoint evidence, not latest pointer."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        manifest = next(
            item
            for item in manifest_store.list_all()
            if item.manifest_id == "manifest-1"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/checkpoint-freshness?"
            f"pipeline=chembl_activity&run_id={manifest.run_id}",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "OK"
        assert data["evidence_source"] == "immutable_manifest_history"
        assert data["manifest_id"] == "manifest-1"
        assert data["checkpoint_run_id"] == str(manifest.run_id)
        assert data["age_seconds"] is not None
        assert float(data["age_seconds"]) >= 3600

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_checkpoint_freshness_fail_closes_aggregate_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Aggregate pipeline scope must not guess one checkpoint age."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/checkpoint-freshness?"
            "pipeline=$__all&run_type=incremental",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["status"] == "UNKNOWN"
        assert data["age_seconds"] is None
        assert data["evidence_source"] == "aggregate_scope_requires_exact_pipeline"
