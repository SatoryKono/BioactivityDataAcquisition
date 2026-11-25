"""Identity anchors must read the selected root rather than the live catalog."""

import asyncio
import json

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest

from bioetl.application.services.evidence_location.resolver import (
    EvidenceLocationResolver,
)
from bioetl.application.services.run_reports.evidence_location_paths import (
    default_evidence_root_alias_registry,
)
from bioetl.composition.control_plane_paths import FileEvidenceReadContextFactory
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_evidence_location import (
    build_run_evidence_location,
)
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane.file_evidence_location_store import (
    FileEvidenceLocationStore,
)
from bioetl.infrastructure.control_plane.file_run_ledger_store import FileRunLedgerStore
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.interfaces.http._health_server_control_plane_evidence_scope import (
    EvidenceScopeHost,
)
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope
from bioetl.interfaces.http._health_server_observability_protocols import (
    HealthServerControlPlaneDeps,
)
from bioetl.interfaces.http._identity_evidence_binding import bind_identity_evidence
from bioetl.interfaces.http.control_plane_identity.payload import (
    build_control_plane_identity_evidence_payload,
)
from bioetl.interfaces.http.health_server import HealthServer

pytestmark = pytest.mark.unit
_SOURCE = "a" * 64
_RUN = RunID(UUID("00000000-0000-4000-8000-000000000119"))


@pytest.fixture
def binding(tmp_path: Path):
    alias = tmp_path / "data"
    selected = alias / "isolated"
    manifest = RunManifest(
        manifest_id="selected-manifest",
        execution_fingerprint="fp",
        run_id=_RUN,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_target",
    )
    FileRunManifestStore(base_path=selected / "output/control/run_manifest").save(
        manifest
    )
    ledger = FileRunLedgerStore(base_path=selected / "output/control/run_ledger")
    ledger.append(
        RunLedgerEntry(
            entry_id="selected-event",
            manifest_id=manifest.manifest_id,
            run_id=_RUN,
            event_type="artifact_published",
            occurred_at=datetime(2026, 11, 25, tzinfo=UTC),
            lineage_fragment_id="selected-lineage",
        )
    )
    global_ledger = FileRunLedgerStore(base_path=alias / "output/control/run_ledger")
    global_ledger.append(
        RunLedgerEntry(
            entry_id="wrong-root-event",
            manifest_id=manifest.manifest_id,
            run_id=_RUN,
            event_type="artifact_published",
            occurred_at=datetime(2026, 11, 25, tzinfo=UTC),
            lineage_fragment_id="wrong-root-lineage",
        )
    )
    locations = FileEvidenceLocationStore(report_root=tmp_path / "reports")
    locations.register(
        build_run_evidence_location(
            kind="pipeline",
            owner="chembl_target",
            run_id=str(_RUN),
            runtime_source_id=_SOURCE,
            relative_data_root="isolated",
        )
    )
    resolver = EvidenceLocationResolver(
        locations=locations,
        aliases=default_evidence_root_alias_registry(dashboard_data_root=alias),
        opener=FileEvidenceReadContextFactory(),
    )
    host = SimpleNamespace(
        _evidence_location_resolver=resolver,
        _run_ledger_port=global_ledger,
        _runtime_source_id=_SOURCE,
    )
    scope = _IdentityScope(
        requested_pipeline="chembl_target",
        selected_pipelines=("chembl_target",),
        selected_run_types=("incremental",),
        selected_run_id=str(_RUN),
        resolved_manifest=manifest,
        resolved_via="selected_run_id",
    )
    return host, scope


def test_identity_anchor_uses_locator_root_even_when_global_identity_matches(binding):
    host, scope = binding
    bound, ledger = bind_identity_evidence(cast(EvidenceScopeHost, host), scope)
    payload = build_control_plane_identity_evidence_payload(
        requested_pipeline=bound.requested_pipeline,
        resolved_manifest=bound.resolved_manifest,
        selected_pipelines=bound.selected_pipelines,
        selected_run_id=bound.selected_run_id,
        selected_run_types=bound.selected_run_types,
        resolved_via=bound.resolved_via,
        ledger_port=ledger,
    )
    row = next(r for r in payload["rows"] if r["name"] == "lineage_fragment_ids")
    assert row["present"] is True
    assert "selected-lineage" in row["value_full"]
    assert "wrong-root-lineage" not in str(payload)
    with pytest.raises(ValueError, match="does not match"):
        ledger.list_entries("foreign-manifest")


@pytest.mark.parametrize("change", ["source", "pipeline", "run_type"])
def test_identity_binding_rejects_conflicts_without_global_fallback(binding, change):
    host, scope = binding
    if change == "source":
        host._runtime_source_id = "b" * 64
    elif change == "pipeline":
        scope = replace(scope, requested_pipeline="chembl_assay")
    else:
        scope = replace(scope, selected_run_types=("backfill",))
    with pytest.raises(ValueError):
        bind_identity_evidence(cast(EvidenceScopeHost, host), scope)


def test_unselected_scope_does_not_resolve_a_locator(binding):
    host, scope = binding
    unselected = replace(scope, selected_run_id=None, resolved_manifest=None)
    bound, ledger = bind_identity_evidence(cast(EvidenceScopeHost, host), unselected)
    assert bound is unselected
    assert ledger is host._run_ledger_port


@pytest.mark.asyncio
async def test_identity_http_route_reads_isolated_ledger(binding, tmp_path: Path):
    host, scope = binding
    catalog = FileRunManifestStore(base_path=tmp_path / "live-manifest-catalog")
    catalog.save(scope.resolved_manifest)
    server = HealthServer(
        port=0,
        control_plane=HealthServerControlPlaneDeps(
            run_manifest_port=catalog,
            run_ledger_port=host._run_ledger_port,
            evidence_location_resolver=host._evidence_location_resolver,
            runtime_source_id=_SOURCE,
        ),
    )
    await server.start()
    try:
        port = server._server.sockets[0].getsockname()[1]
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        path = f"/ops/control-plane/identity-evidence?pipeline=chembl_target&run_id={_RUN}&view=anchors"
        writer.write(
            f"GET {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n".encode()
        )
        await writer.drain()
        response = await asyncio.wait_for(reader.read(), timeout=5)
        writer.close()
        await writer.wait_closed()
        headers, body = response.split(b"\r\n\r\n", 1)
        assert headers.startswith(b"HTTP/1.1 200"), response
        payload = json.loads(body)
        row = next(r for r in payload["rows"] if r["name"] == "lineage_fragment_ids")
        assert row["present"] is True
        assert "selected-lineage" in row["value_full"]
        assert "wrong-root-lineage" not in str(payload)
    finally:
        await server.stop()
