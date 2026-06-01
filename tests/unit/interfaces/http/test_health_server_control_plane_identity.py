"""Tests for health-server control-plane identity endpoints."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

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
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.interfaces.http import _health_server_identity_evidence
from bioetl.interfaces.http import _health_server_routing_support
from bioetl.interfaces.http.control_plane_selector_context import (
    build_selector_filter_options_payload,
)
from bioetl.interfaces.http.control_plane_identity import (
    IDENTITY_EVIDENCE_CONTRACT,
    build_control_plane_identity_evidence_payload,
)
from bioetl.interfaces.http.control_plane_identity.checkpoint import (
    build_checkpoint_compare,
)
from bioetl.interfaces.http.control_plane_identity.source_model import (
    DRILLDOWN_TARGET_BY_NAME,
    SOURCE_MODEL_BY_NAME,
)
from bioetl.interfaces.http.control_plane_identity.severity import domain_severity
from bioetl.interfaces.http.control_plane_identity.specs import (
    ALLOWED_LOW_CARDINALITY_LABELS,
    ANCHOR_SPECS,
    OVERVIEW_NAMES,
    SPEC_BY_NAME,
)
from bioetl.interfaces.http.health_server import HealthServer
from tests.helpers.control_plane import InMemoryRunLedgerStore, InMemoryRunManifestStore
from tests.helpers.clock import fixed_test_clock


def test_control_plane_identity_evidence_static_contract_is_frozen() -> None:
    """The refactored identity evidence package must preserve the audit contract."""
    assert IDENTITY_EVIDENCE_CONTRACT == "control_plane_identity_evidence_v1"
    assert (
        _health_server_identity_evidence.build_control_plane_identity_evidence_payload
        is build_control_plane_identity_evidence_payload
    )

    p0_names = {spec.name for spec in ANCHOR_SPECS if spec.priority == "P0"}
    assert p0_names == {
        "run_id",
        "manifest_id",
        "pipeline_name",
        "provider_entity",
        "runtime_mode",
        "execution_fingerprint",
        "git_commit",
        "pipeline_version",
        "effective_config_hash",
        "effective_config_artifact_id",
        "contract_ref",
        "contract_version",
        "contract_schema_hash",
        "input_snapshot_identity_fingerprint",
        "input_snapshot_count",
        "replay_mode",
        "replay_of_run_id",
        "replay_of_manifest_id",
        "checkpoint_anchor_status",
        "composite_run_identity",
        "identity_graph_complete",
    }
    assert OVERVIEW_NAMES == {
        "run_id",
        "manifest_id",
        "pipeline_name",
        "provider_entity",
        "runtime_mode",
        "execution_fingerprint",
        "effective_config_hash",
        "contract_ref",
        "contract_version",
        "input_snapshot_identity_fingerprint",
        "replay_capability",
        "replay_mode",
        "checkpoint_anchor_status",
        "composite_run_identity",
        "identity_graph_complete",
    }
    assert OVERVIEW_NAMES - p0_names == {"replay_capability"}
    anchor_names = {spec.name for spec in ANCHOR_SPECS}
    assert set(SOURCE_MODEL_BY_NAME) == anchor_names
    assert set(DRILLDOWN_TARGET_BY_NAME) == anchor_names
    assert SPEC_BY_NAME["resolved_config_hash"].priority == "P1"
    assert (
        SOURCE_MODEL_BY_NAME["resolved_config_hash"].source_quality == "authoritative"
    )
    assert SPEC_BY_NAME["config_hash"].priority == "P2"
    assert SOURCE_MODEL_BY_NAME["config_hash"].source_quality == "compatibility_alias"

    forbidden_label_names = {
        "run_id",
        "manifest_id",
        "execution_fingerprint",
        "effective_config_hash",
        "effective_config_artifact_id",
        "resolved_config_hash",
        "config_hash",
        "contract_schema_hash",
        "dq_contract_compatibility_hash",
        "input_snapshot_identity_fingerprint",
        "input_snapshot_ids",
        "input_snapshot_content_hashes",
        "replay_of_run_id",
        "replay_of_manifest_id",
        "composite_run_identity",
        "lineage_fragment_ids",
        "artifact_refs",
        "checkpoint_file_id",
        "latest_event_id",
        "bronze_batch_ids",
    }
    assert forbidden_label_names.isdisjoint(ALLOWED_LOW_CARDINALITY_LABELS)


def test_control_plane_identity_checkpoint_compare_classifies_partial() -> None:
    """Persisted checkpoint anchors can be present but incomplete."""
    manifest = RunManifest(
        manifest_id="manifest-partial",
        execution_fingerprint="fingerprint-partial",
        schema_version="1.0",
        created_at=datetime(2026, 5, 12, 8, 21, tzinfo=UTC),
        run_id=RunID(uuid4()),
        run_type=RunType.REBUILD,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={
            "checkpoint_metadata": {
                "manifest_id": "manifest-partial",
                "execution_fingerprint": "fingerprint-partial",
            }
        },
        resolved_config={},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            effective_config_hash=(
                "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            ),
            effective_config_artifact_id="effective-config-partial",
        ),
    )

    compare = build_checkpoint_compare(manifest)
    rows = {str(item["anchor"]): item for item in compare["rows"]}

    assert compare["status"] == "PARTIAL"
    assert rows["manifest_id"]["status"] == "OK"
    assert rows["effective_config_hash"]["status"] == "MISSING"
    assert rows["effective_config_hash"]["ui_status"] == "WARN"


def _identity_severity_manifest(*, exact_replay: bool = False) -> RunManifest:
    return RunManifest(
        manifest_id="manifest-severity",
        execution_fingerprint="fingerprint-severity",
        schema_version="1.0",
        created_at=datetime(2026, 5, 12, 8, 21, tzinfo=UTC),
        run_id=RunID(uuid4()),
        run_type=RunType.REBUILD,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"exact_replay": exact_replay},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )


@pytest.mark.parametrize(
    ("checkpoint_status", "expected"),
    [
        ("OK", "OK"),
        ("MISMATCH", "FAILING"),
        ("PARTIAL", "DEGRADED"),
        ("UNKNOWN", "DEGRADED"),
    ],
)
def test_control_plane_identity_domain_severity_maps_checkpoint_status(
    checkpoint_status: str, expected: str
) -> None:
    assert (
        domain_severity(
            SPEC_BY_NAME["checkpoint_anchor_status"],
            value=checkpoint_status,
            present=True,
            manifest=None,
            ledger_entries=(),
            checkpoint_status=checkpoint_status,
            applicable=True,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (True, "OK"),
        ("complete (0 gaps)", "OK"),
        ("missing run_id", "FAILING"),
        ("partial graph", "DEGRADED"),
    ],
)
def test_control_plane_identity_domain_severity_maps_identity_graph_value(
    value: object, expected: str
) -> None:
    assert (
        domain_severity(
            SPEC_BY_NAME["identity_graph_complete"],
            value=value,
            present=True,
            manifest=None,
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == expected
    )


def test_control_plane_identity_domain_severity_fails_exact_replay_missing_anchor() -> (
    None
):
    assert (
        domain_severity(
            SPEC_BY_NAME["effective_config_hash"],
            value=None,
            present=False,
            manifest=_identity_severity_manifest(exact_replay=True),
            ledger_entries=(),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )


def test_control_plane_identity_domain_severity_fails_terminal_missing_manifest() -> (
    None
):
    run_id = RunID(uuid4())
    terminal_entry = RunLedgerEntry(
        entry_id="ledger-terminal",
        manifest_id="manifest-severity",
        run_id=run_id,
        event_type=RUN_FAILED_EVENT,
        occurred_at=datetime(2026, 5, 12, 8, 22, tzinfo=UTC),
        status="failed",
    )

    assert (
        domain_severity(
            SPEC_BY_NAME["manifest_id"],
            value=None,
            present=False,
            manifest=_identity_severity_manifest(),
            ledger_entries=(terminal_entry,),
            checkpoint_status="OK",
            applicable=True,
        )
        == "FAILING"
    )


class _CountingRunLedgerStore(InMemoryRunLedgerStore):
    """Ledger fake that records selector lookup fan-out."""

    def __init__(self) -> None:
        super().__init__()
        self.lookup_run_ids: list[str] = []

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        self.lookup_run_ids.append(str(run_id))
        return super().list_entries_by_run_id(run_id)


def test_control_plane_filter_options_narrows_manifest_catalog_before_ledger_reads() -> (
    None
):
    """Scoped run_id queries should not walk unrelated manifests/ledger entries."""
    manifest_store = InMemoryRunManifestStore()
    ledger_store = _CountingRunLedgerStore()
    created_at = datetime(2026, 5, 12, 8, 21, tzinfo=UTC)
    run_id_1 = RunID(uuid4())
    run_id_2 = RunID(uuid4())
    run_id_3 = RunID(uuid4())

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
            launch_context={},
            runtime_config={"run_type": "incremental"},
            resolved_config={"pipeline_name": "chembl_activity"},
            code_provenance=RunCodeProvenance(),
        )
    )
    manifest_store.save(
        RunManifest(
            manifest_id="manifest-2",
            execution_fingerprint="fingerprint-2",
            schema_version="1.0",
            created_at=created_at + timedelta(minutes=1),
            run_id=run_id_2,
            run_type=RunType.BACKFILL,
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            launch_context={},
            runtime_config={"run_type": "backfill"},
            resolved_config={"pipeline_name": "chembl_activity"},
            code_provenance=RunCodeProvenance(),
        )
    )
    manifest_store.save(
        RunManifest(
            manifest_id="manifest-3",
            execution_fingerprint="fingerprint-3",
            schema_version="1.0",
            created_at=created_at + timedelta(minutes=2),
            run_id=run_id_3,
            run_type=RunType.INCREMENTAL,
            pipeline_name="pubchem_compound",
            provider="pubchem",
            entity="compound",
            launch_context={},
            runtime_config={"run_type": "incremental"},
            resolved_config={"pipeline_name": "pubchem_compound"},
            code_provenance=RunCodeProvenance(),
        )
    )

    payload = build_selector_filter_options_payload(
        manifests=manifest_store.list_all(),
        ledger_port=ledger_store,
        dimension="run_id",
        response_shape="list",
        requested_pipeline="chembl_activity",
        selected_pipelines=("chembl_activity",),
        selected_run_types=("incremental",),
    )

    assert payload == {"items": ["-", str(run_id_1)]}
    assert ledger_store.lookup_run_ids == [str(run_id_1)]


class TestHealthServerControlPlaneSelector:
    """Tests for /ops/control-plane/* selector helper endpoints."""

    @pytest_asyncio.fixture(loop_scope="module")
    async def running_server_without_run_catalog(
        self,
    ) -> AsyncGenerator[HealthServer, None]:
        """Start server without control-plane run catalog."""
        server = HealthServer(host="127.0.0.1", port=0)
        await server.start()
        yield server
        await server.stop()

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
        run_id_1 = RunID(uuid4())
        run_id_2 = RunID(uuid4())
        run_id_3 = RunID(uuid4())
        run_id_4 = RunID(uuid4())
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
    async def test_control_plane_endpoint_requires_run_catalog(
        self,
        running_server_without_run_catalog: HealthServer,
    ) -> None:
        """Selector endpoint should return 503 when run catalog is not configured."""
        port = self._get_server_port(running_server_without_run_catalog)
        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?dimension=run_id&pipeline=chembl_activity",
        )

        assert status_code == 503
        assert status_text == "Control-plane selector catalog unavailable"
        assert "Control-plane selector catalog unavailable" in body

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_requires_pipeline_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Selector endpoint should reject unscoped control-plane reads."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?dimension=run_id",
        )

        assert status_code == 400
        assert status_text == "Missing required query parameter: pipeline"
        assert "Missing required query parameter: pipeline" in body

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_filters_run_ids_by_pipeline_and_run_type(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Selector endpoint should expose exact run IDs from persisted manifests."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        expected_incremental_ids = [
            str(manifest.run_id)
            for manifest in manifest_store.list_all()
            if manifest.pipeline_name == "chembl_activity"
            and manifest.run_type == RunType.INCREMENTAL
        ]

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=run_id&pipeline=chembl_activity&run_type=incremental",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["pipeline"] == "chembl_activity"
        assert data["run_type"] == ["incremental"]
        assert data["run_ids"] == expected_incremental_ids

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_treats_all_run_type_as_unbounded_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Grafana All run_type should not collapse the selector to an empty scope."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        expected_run_ids = [
            str(manifest.run_id)
            for manifest in manifest_store.list_all()
            if manifest.pipeline_name == "chembl_activity"
        ]

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=run_id&pipeline=chembl_activity&run_type=$__all",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["pipeline"] == "chembl_activity"
        assert data["run_type"] == []
        assert data["run_ids"] == expected_run_ids

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_treats_all_pipeline_as_aggregate_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Grafana All pipeline should expose aggregate run IDs for exact-run handoff."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        expected_incremental_ids = [
            str(manifest.run_id)
            for manifest in manifest_store.list_all()
            if manifest.run_type == RunType.INCREMENTAL
        ]

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=run_id&pipeline=$__all&run_type=incremental",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["pipeline"] == "$__all"
        assert data["run_type"] == ["incremental"]
        assert data["run_ids"] == expected_incremental_ids

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_supports_list_shape_for_variable_queries(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Variable queries may request a plain list wrapper for Infinity parsing."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        expected_run_ids = [
            str(manifest.run_id)
            for manifest in manifest_store.list_all()
            if manifest.pipeline_name == "chembl_activity"
        ]

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=run_id&response_shape=list&pipeline=chembl_activity&run_type=$__all",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data == {"items": ["-", *expected_run_ids]}

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_supports_brace_expanded_grafana_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Grafana brace-expanded All scope should still resolve run IDs."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        expected_run_ids = [
            str(manifest.run_id)
            for manifest in manifest_store.list_all()
            if manifest.pipeline_name in {"chembl_activity", "pubchem_compound"}
            and manifest.run_type == RunType.INCREMENTAL
        ]

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=run_id&response_shape=list"
            "&pipeline={chembl_activity,pubchem_compound}"
            "&run_type={incremental}",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data == {"items": ["-", *expected_run_ids]}

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_selector_context_resolves_latest_terminal_run(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Selector context should choose latest terminal evidence for a pipeline."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        latest_manifest = next(
            manifest
            for manifest in manifest_store.list_all()
            if manifest.manifest_id == "manifest-2"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/selector-context?pipeline=chembl_activity",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["contract"] == "control_plane_selector_context_v1"
        assert data["resolved_via"] == "latest_terminal_run_for_scope"
        assert data["selected"]["pipeline"] == "chembl_activity"
        assert data["selected"]["run_type"] == "backfill"
        assert data["selected"]["run_id"] == str(latest_manifest.run_id)
        assert data["selected"]["run_status"] == "failed"
        assert data["selected"]["completed_at_source"] == "run_ledger_terminal_event"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_selector_context_run_id_overrides_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Exact run_id should resolve the selected manifest even with stale scope."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        selected_manifest = next(
            manifest
            for manifest in manifest_store.list_all()
            if manifest.manifest_id == "manifest-1"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/selector-context?"
            f"pipeline=pubchem_compound&run_id={selected_manifest.run_id}",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["resolved_via"] == "selected_run_id"
        assert data["selected"]["pipeline"] == "chembl_activity"
        assert data["selected"]["run_type"] == "incremental"
        assert data["selected"]["run_id"] == str(selected_manifest.run_id)

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_selector_context_supports_workflow_alias_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Workflow aliases should narrow selector context to the matching pipeline."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/selector-context?workflow=workflow_chembl_activity",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["selected"]["pipeline"] == "chembl_activity"
        assert data["selected"]["run_type"] == "backfill"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_filter_options_exposes_pipeline_dimension(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Selector catalog should expose non-run_id dimensions for variable shells."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=pipeline&response_shape=list&workflow=chembl_activity",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data == {"items": ["chembl_activity"]}

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_returns_latest_manifest_for_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Identity table should resolve latest persisted manifest for scope."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?pipeline=chembl_activity",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "latest_manifest_for_scope"
        assert rows["Manifest ID [Control Plane]"] == "manifest-2"
        assert rows["Provider.Entity [Version]"] == "chembl.activity [1.0.0]"
        assert rows["Run ID [Pipeline]"]
        assert rows["Contract [Schema]"] == (
            "chembl.activity.2026.05 "
            "[bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb]"
        )
        assert rows["Execution [Type|Context|Git]"] == (
            "backfill | isolated | git=def5678"
        )
        assert rows["Resume|Dry run|Cached Bronze"] == "No | No | No"
        assert rows["Replay [Capability.Mode]"] == "Yes [Supported.Backfill]"
        assert rows["Checkpoint [Anchors]"] == "OK"
        assert rows["Identity Health [Gaps]"] == "Complete [6 gaps]"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_compact_health_matches_identity_evidence(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Compact ID panel health must not drift from identity-evidence summary."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        table_status, _, table_body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?pipeline=chembl_activity",
        )
        evidence_status, _, evidence_body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-evidence?"
            "pipeline=chembl_activity&view=overview",
        )

        assert table_status == 200
        assert evidence_status == 200
        table = json.loads(table_body)
        evidence = json.loads(evidence_body)
        rows = {item["parameter"]: item["value"] for item in table["rows"]}
        summary = evidence["summary"]

        assert rows["Checkpoint [Anchors]"] == summary["checkpoint_anchor_status"]
        expected_status = (
            "Complete" if summary["identity_graph_complete"] else "Incomplete"
        )
        assert rows["Identity Health [Gaps]"] == (
            f"{expected_status} [{summary['identity_gap_count']} gaps]"
        )

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_treats_all_run_type_as_unbounded_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """ID panel should still resolve a concrete pipeline when run_type=All."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?"
            "pipeline=chembl_activity&run_type=$__all",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "latest_manifest_for_scope"
        assert rows["Manifest ID [Control Plane]"] == "manifest-2"
        assert rows["Provider.Entity [Version]"] == "chembl.activity [1.0.0]"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_unknown_pipeline_scope_fails_fast(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Dashboard fallback scope should return no-manifest state without guessing."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?"
            "pipeline=unknown&run_type=__all&run_id=-",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "no_manifest_for_scope"
        assert data["pipeline"] == "unknown"
        assert data["run_type"] == []
        assert data["selected_run_id"] is None
        assert rows["Manifest ID [Control Plane]"] == "not available for current scope"
        assert rows["Provider.Entity [Version]"] == "unknown"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_treats_run_id_dash_as_unselected(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Overview v3 Run ID placeholder should not count as exact selection."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?pipeline=chembl_activity&run_id=-",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "latest_manifest_for_scope"
        assert rows["Manifest ID [Control Plane]"] == "manifest-2"
        assert rows["Provider.Entity [Version]"] == "chembl.activity [1.0.0]"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_prefers_selected_run_id(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Identity table should resolve exact manifest when run_id is selected."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        selected_manifest = next(
            manifest
            for manifest in manifest_store.list_all()
            if manifest.manifest_id == "manifest-1"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?"
            f"pipeline=chembl_activity&run_id={selected_manifest.run_id}",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "selected_run_id"
        assert rows["Manifest ID [Control Plane]"] == "manifest-1"
        assert rows["Run ID [Pipeline]"] == str(selected_manifest.run_id)
        assert rows["Execution [Type|Context|Git]"] == (
            "incremental | isolated | git=abc1234"
        )
        assert rows["Checkpoint [Anchors]"] == "MISSING"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_supports_all_pipeline_with_selected_run_id(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Aggregate pipeline scope should resolve the exact manifest when run_id is explicit."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        selected_manifest = next(
            manifest
            for manifest in manifest_store.list_all()
            if manifest.manifest_id == "manifest-3"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?"
            f"pipeline=$__all&run_type=incremental&run_id={selected_manifest.run_id}",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "selected_run_id"
        assert rows["Manifest ID [Control Plane]"] == "manifest-3"
        assert rows["Provider.Entity [Version]"] == "pubchem.compound [1.0.0]"
        assert rows["Run ID [Pipeline]"] == str(selected_manifest.run_id)

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_requires_exact_run_id_for_all_pipeline_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Aggregate pipeline scope should not guess one manifest without explicit run_id."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?pipeline=$__all&run_type=incremental",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "aggregate_scope_requires_exact_run_id"
        assert (
            rows["Manifest ID [Control Plane]"]
            == "select one concrete pipeline or exact run_id"
        )
        assert rows["Run ID [Pipeline]"] == (
            "select one concrete pipeline or exact run_id"
        )
        assert rows["Provider.Entity [Version]"] == "$__all"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_treats_brace_expanded_pipeline_scope_as_aggregate(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Brace-expanded pipeline sets must not be mistaken for one concrete pipeline."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?"
            "pipeline={chembl_activity,chembl_assay,chembl_publication,chembl_target,test_pipe}"
            "&run_type={incremental,full,rebuild}",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert data["resolved_via"] == "aggregate_scope_requires_exact_run_id"
        assert (
            rows["Manifest ID [Control Plane]"]
            == "select one concrete pipeline or exact run_id"
        )
        assert rows["Run ID [Pipeline]"] == (
            "select one concrete pipeline or exact run_id"
        )
        assert (
            rows["Provider.Entity [Version]"]
            == "{chembl_activity,chembl_assay,chembl_publication,chembl_target,test_pipe}"
        )

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_requires_pipeline_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Identity table should reject unscoped reads."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table",
        )

        assert status_code == 400
        assert status_text == "Missing required query parameter: pipeline"
        assert "Missing required query parameter: pipeline" in body

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_freezes_compact_contract(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """The shared shell ID endpoint must stay compact and backward compatible."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?pipeline=chembl_activity",
        )

        assert status_code == 200
        data = json.loads(body)
        assert [item["parameter"] for item in data["rows"]] == [
            "Run ID [Pipeline]",
            "Manifest ID [Control Plane]",
            "Provider.Entity [Version]",
            "Contract [Schema]",
            "Execution [Type|Context|Git]",
            "Resume|Dry run|Cached Bronze",
            "Replay [Capability.Mode]",
            "Checkpoint [Anchors]",
            "Identity Health [Gaps]",
        ]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_table_adds_composite_row_conditionally(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Composite run identity belongs in the compact shell only for composite runs."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        composite_manifest = next(
            manifest
            for manifest in manifest_store.list_all()
            if manifest.manifest_id == "manifest-4"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-table?"
            f"pipeline=$__all&run_id={composite_manifest.run_id}",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["parameter"]: item["value"] for item in data["rows"]}
        assert rows["Composite Run"] == "composite-run-4"
        assert rows["Execution [Type|Context|Git]"] == (
            "rebuild | composite | git=jkl3456"
        )
        assert rows["Replay [Capability.Mode]"] == "No [Rebuild only.Exact Replay]"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_evidence_returns_anchor_contract(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Dedicated identity endpoint should expose P0/P1/P2 evidence rows."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-evidence?"
            "pipeline=chembl_activity&view=anchors",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["contract"] == "control_plane_identity_evidence_v1"
        assert data["resolved_via"] == "latest_manifest_for_scope"
        rows = {item["name"]: item for item in data["anchors"]}
        assert rows["run_id"]["priority"] == "P0"
        assert rows["manifest_id"]["value_full"] == "manifest-2"
        assert rows["effective_config_hash"]["value_full"] == (
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        assert rows["effective_config_hash"]["value_short"] == "aaaaaaaaaaaa"
        assert rows["effective_config_hash"]["source_type"] == (
            "effective_config_artifact"
        )
        assert rows["effective_config_hash"]["source_quality"] == "authoritative"
        assert rows["resolved_config_hash"]["value_full"] == "feedface"
        assert rows["resolved_config_hash"]["source_quality"] == "authoritative"
        assert rows["config_hash"]["source_quality"] == "compatibility_alias"
        assert rows["config_hash"]["copy"] is False
        assert rows["effective_config_hash"]["drilldown_type"] == "effective_config"
        assert rows["effective_config_hash"]["drilldown_target"] == (
            "effective_config.hash:"
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        assert rows["contract_ref"]["value_full"] == "chembl.activity"
        assert rows["input_snapshot_count"]["value_full"] == "1"
        assert rows["checkpoint_anchor_status"]["value_full"] == "OK"
        assert rows["identity_graph_complete"]["value_full"] == "complete"
        assert rows["identity_graph_complete"]["missing_severity"] == "OK"
        assert data["summary"]["identity_graph_complete"] is True
        assert data["summary"]["correlation_anchor_gaps"] == {}
        assert data["identity_diagnostics"]["checkpoint_anchor_status"] == "OK"
        assert rows["runtime_mode"]["copy"] is False
        assert rows["effective_config_hash"]["copy"] is True
        assert {item["priority"] for item in data["anchors"]} == {"P0", "P1", "P2"}

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_evidence_fail_closes_aggregate_scope(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Aggregate identity evidence must not guess one manifest without run_id."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-evidence?"
            "pipeline=$__all&run_type=incremental&view=overview",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["resolved_via"] == "aggregate_scope_requires_exact_run_id"
        assert data["summary"]["overall_status"] == "UNKNOWN"
        rows = {item["name"]: item for item in data["rows"]}
        assert rows["run_id"]["value_full"] == "not available for current scope"
        assert rows["manifest_id"]["value_full"] == "not available for current scope"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_evidence_replay_parent_gap_is_critical(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Exact replay evidence must not silently ignore missing parent anchors."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        composite_manifest = next(
            manifest
            for manifest in manifest_store.list_all()
            if manifest.manifest_id == "manifest-4"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-evidence?"
            f"pipeline=$__all&run_id={composite_manifest.run_id}&view=gaps",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["name"]: item for item in data["rows"]}
        assert rows["replay_of_run_id"]["missing_severity"] == "FAILING"
        assert rows["replay_of_run_id"]["ui_status"] == "CRIT"
        assert rows["replay_of_manifest_id"]["missing_severity"] == "FAILING"
        assert (
            "replay_of_manifest_id"
            in data["identity_diagnostics"]["identity_gap_names"]
        )

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_evidence_checkpoint_compare_mismatch(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Checkpoint compare view should classify current vs persisted anchors."""
        server, manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        composite_manifest = next(
            manifest
            for manifest in manifest_store.list_all()
            if manifest.manifest_id == "manifest-4"
        )

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-evidence?"
            f"pipeline=$__all&run_id={composite_manifest.run_id}"
            "&view=checkpoint_compare",
        )

        assert status_code == 200
        data = json.loads(body)
        assert data["checkpoint_compare"]["status"] == "MISMATCH"
        rows = {item["anchor"]: item for item in data["rows"]}
        assert rows["effective_config_hash"]["status"] == "MISMATCH"
        assert rows["effective_config_hash"]["ui_status"] == "CRIT"
        assert rows["effective_config_hash"]["source_type"] == (
            "checkpoint_metadata_compare"
        )
        assert rows["effective_config_hash"]["drilldown_target"] == (
            "checkpoint.compare:effective_config_hash"
        )

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_identity_evidence_copy_values_are_full_values(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Copy handoffs should exist only for copyable full-value anchors."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)

        status_code, _, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/identity-evidence?"
            "pipeline=chembl_activity&view=copy_values",
        )

        assert status_code == 200
        data = json.loads(body)
        rows = {item["name"]: item for item in data["rows"]}
        assert "runtime_mode" not in rows
        assert rows["effective_config_hash"]["copy_value"] == (
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        )
        assert rows["contract_ref"]["copy_value"] == "chembl.activity"

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
        run_id = RunID(uuid4())
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
            f"/ops/control-plane/checkpoint-freshness?pipeline={pipeline}&run_type=incremental&run_id=-",
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

    @pytest.mark.asyncio(loop_scope="module")
    async def test_control_plane_endpoint_rejects_unknown_dimension(
        self,
        running_server_with_run_catalog: tuple[HealthServer, InMemoryRunManifestStore],
    ) -> None:
        """Selector endpoint should fail closed for unsupported filter dimensions."""
        server, _manifest_store = running_server_with_run_catalog
        port = self._get_server_port(server)
        status_code, status_text, body = await self._send_request(
            port,
            "GET",
            "/ops/control-plane/filter-options?"
            "dimension=manifest_id&pipeline=chembl_activity",
        )

        assert status_code == 400
        assert status_text == "Unsupported control-plane filter dimension: manifest_id"
        assert "Unsupported control-plane filter dimension: manifest_id" in body
