"""Pure tests for run-bounded checkpoint lookup semantics."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.interfaces.http._health_server_checkpoint_lookup import (
    load_checkpoint_freshness_evidence,
)
from bioetl.interfaces.http._health_server_control_plane_scope import _IdentityScope
from bioetl.interfaces.http._health_server_control_plane_evidence_routing import (
    _checkpoint_payload,
)
from bioetl.interfaces.http.health_server import HealthServer
from tests.helpers.control_plane import InMemoryRunManifestStore

pytestmark = pytest.mark.unit


class _CheckpointPort:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def load(self, pipeline: str) -> tuple[object, dict[str, object]] | None:
        self.calls.append(f"latest:{pipeline}")
        return ("other-run", {"manifest_id": "other-manifest"})

    async def load_for_manifest_id(
        self,
        manifest_id: str,
    ) -> tuple[object, dict[str, object]] | None:
        self.calls.append(f"manifest:{manifest_id}")
        return None

    async def load_for_run(
        self,
        pipeline: str,
        run_id: object,
    ) -> tuple[object, dict[str, object]] | None:
        self.calls.append(f"run:{pipeline}:{run_id}")
        return None


class _Host:
    def __init__(self, port: _CheckpointPort) -> None:
        self._checkpoint_port = port

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool:
        return value in {None, "$__all"}


@pytest.mark.asyncio
async def test_selected_run_not_found_never_falls_back_to_latest_checkpoint() -> None:
    port = _CheckpointPort()
    scope = _IdentityScope(
        requested_pipeline="chembl_activity",
        selected_pipelines=("chembl_activity",),
        selected_run_types=("incremental",),
        selected_run_id="00000000-0000-0000-0000-000000008490",
        resolved_manifest=None,
        resolved_via="selected_run_id_not_found",
    )

    evidence = await load_checkpoint_freshness_evidence(
        _Host(port),  # pyright: ignore[reportArgumentType]
        scope=scope,
        target_pipeline="chembl_activity",
    )

    assert evidence == (None, "selected_run_id_not_found", None, False)
    assert port.calls == []


@pytest.mark.asyncio
async def test_legacy_non_object_metadata_maps_to_bounded_endpoint_error(
    tmp_path: Path,
) -> None:
    manifest = RunManifest(
        manifest_id="manifest-checkpoint-wrong-metadata",
        execution_fingerprint="fingerprint-checkpoint-wrong-metadata",
        created_at=datetime(2026, 8, 10, tzinfo=UTC),
        run_id=RunID(UUID("00000000-0000-0000-0000-000000008490")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
    )
    manifests = InMemoryRunManifestStore()
    manifests.save(manifest)
    checkpoint_root = tmp_path / "checkpoints"
    checkpoint_root.mkdir()
    (checkpoint_root / f"{manifest.pipeline_name}.json").write_text(
        json.dumps(
            {
                "pipeline": manifest.pipeline_name,
                "run_id": str(manifest.run_id),
                "metadata": ["raw-secret-wrong-shape"],
                "version": "2.0",
            }
        ),
        encoding="utf-8",
    )
    checkpoint_port = LocalCheckpointAdapter(checkpoint_root)
    server = HealthServer(
        checkpoint_port=checkpoint_port,
        run_manifest_port=manifests,
        control_plane_evidence_service=ControlPlaneEvidenceService(),
    )

    payload = await _checkpoint_payload(
        server,  # type: ignore[arg-type]
        {
            "pipeline": manifest.pipeline_name,
            "run_type": manifest.run_type.value,
        },
    )

    assert payload["status"] == "ERROR"
    assert payload["rows"] == [
        {
            "check": "parse",
            "status": "ERROR",
            "reason": "checkpoint_parse_error",
            "detail": "Persisted control-plane evidence could not be read or parsed.",
        }
    ]
    assert "raw-secret-wrong-shape" not in str(payload)
