"""Pre-coercion manifest evidence regressions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest

from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
    EvidenceScopeContext,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)

pytestmark = pytest.mark.integration


def _manifest() -> RunManifest:
    return RunManifest(
        manifest_id="manifest-raw-evidence",
        execution_fingerprint="fingerprint-raw-evidence",
        created_at=datetime(2026, 8, 9, tzinfo=UTC),
        run_id=RunID(UUID("00000000-0000-0000-0000-000000008491")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"required_persistence_profile": "degraded_observable"},
    )


def _scope(manifest: RunManifest) -> EvidenceScopeContext:
    return EvidenceScopeContext(
        requested_pipeline="chembl_activity",
        selected_run_id=str(manifest.run_id),
        selected_run_types=(manifest.run_type.value,),
        resolved_via="selected_run_id",
        manifest=manifest,
    )


def _reasons(payload: dict[str, object]) -> set[str]:
    rows = cast("list[dict[str, object]]", payload["rows"])
    return {str(row["reason"]) for row in rows}


def test_manifest_validation_reports_raw_schema_errors_before_coercion(
    tmp_path: Path,
) -> None:
    manifest = _manifest()
    store = FileRunManifestStore(tmp_path / "run_manifest")
    store.save(manifest)
    path = store.base_path / f"{manifest.manifest_id}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw.update(
        {
            "pipeline_name": {"spoofed": "pipeline"},
            "provider": ["chembl"],
            "entity": 42,
            "launch_context": ["wrong-shape"],
            "source_refs": {"wrong": "shape"},
        }
    )
    path.write_text(json.dumps(raw), encoding="utf-8")
    service = ControlPlaneEvidenceService(manifest_inspector=store)
    coerced_manifest = store.get(manifest.manifest_id)
    assert coerced_manifest is not None

    payload = service.manifest_validation(scope=_scope(coerced_manifest))

    assert payload["status"] == "ERROR"
    assert {
        "manifest_pipeline_name_not_string",
        "manifest_provider_not_string",
        "manifest_entity_not_string",
        "manifest_launch_context_not_object",
        "manifest_source_refs_not_array",
    } <= _reasons(payload)
    assert payload["pipeline"] == "chembl_activity"
    assert payload["manifest_id"] is None
    assert "spoofed" not in str(payload)
    assert "wrong-shape" not in str(payload)


def test_manifest_validation_distinguishes_raw_parse_failure(tmp_path: Path) -> None:
    manifest = _manifest()
    store = FileRunManifestStore(tmp_path / "run_manifest")
    store.save(manifest)
    path = store.base_path / f"{manifest.manifest_id}.json"
    path.write_text("{broken-json", encoding="utf-8")

    payload = ControlPlaneEvidenceService(manifest_inspector=store).manifest_validation(
        scope=_scope(manifest)
    )

    assert payload["status"] == "ERROR"
    assert "manifest_parse_error" in _reasons(payload)
    assert "manifest_raw_schema_not_observable" in _reasons(payload)
    assert "broken-json" not in str(payload)
