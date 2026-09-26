"""Pre-coercion schema diagnostics for file-backed run manifests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.domain.ports import RawRunManifestInspectionPort
from bioetl.infrastructure.control_plane import FileRunManifestStore
from tests.unit.application.services.run_manifest_test_support import (
    make_run_manifest,
)

pytestmark = pytest.mark.unit


def _saved_store(
    tmp_path: Path, manifest_id: str = "manifest-raw"
) -> FileRunManifestStore:
    store = FileRunManifestStore(tmp_path / "run_manifest")
    store.save(make_run_manifest(manifest_id=manifest_id))
    return store


def _manifest_path(store: FileRunManifestStore, manifest_id: str) -> Path:
    return store.base_path / f"{manifest_id}.json"


def test_valid_saved_manifest_passes_raw_inspection(tmp_path: Path) -> None:
    store = _saved_store(tmp_path)

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert isinstance(store, RawRunManifestInspectionPort)
    assert inspection.parse_ok is True
    assert inspection.schema_ok is True
    assert inspection.schema_errors == ()


def test_malformed_json_has_bounded_parse_diagnostic(tmp_path: Path) -> None:
    store = FileRunManifestStore(tmp_path / "run_manifest")
    path = _manifest_path(store, "manifest-broken")
    path.parent.mkdir(parents=True)
    path.write_text("{not-json", encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-broken")

    assert inspection.parse_ok is False
    assert inspection.schema_ok is False
    assert inspection.schema_errors == ("manifest_parse_error",)


def test_non_object_json_has_bounded_schema_diagnostic(tmp_path: Path) -> None:
    """Syntactically valid arrays are distinguished from parse failures."""
    store = FileRunManifestStore(tmp_path / "run_manifest")
    path = _manifest_path(store, "manifest-array")
    path.parent.mkdir(parents=True)
    path.write_text("[]", encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-array")

    assert inspection.parse_ok is True
    assert inspection.schema_errors == ("manifest_payload_not_object",)


def test_manifest_read_error_has_bounded_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filesystem read failures remain distinct from malformed JSON."""
    store = _saved_store(tmp_path, manifest_id="manifest-unreadable")
    path = _manifest_path(store, "manifest-unreadable")
    original_read_text = Path.read_text

    def _read_text(
        candidate: Path,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> str:
        if candidate == path:
            raise OSError("read failed")
        return original_read_text(
            candidate,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    monkeypatch.setattr(Path, "read_text", _read_text)

    inspection = store.inspect_raw_manifest("manifest-unreadable")

    assert inspection.parse_ok is False
    assert inspection.schema_errors == ("manifest_read_error",)


def test_raw_inspection_detects_string_coercion_before_typed_load(
    tmp_path: Path,
) -> None:
    store = _saved_store(tmp_path)
    path = _manifest_path(store, "manifest-raw")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pipeline_name"] = 123
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-raw")
    typed_manifest = store.get("manifest-raw")

    assert typed_manifest is not None
    assert typed_manifest.pipeline_name == "123"
    assert inspection.parse_ok is True
    assert inspection.schema_errors == ("manifest_pipeline_name_not_string",)


def test_raw_inspection_detects_structured_field_type_errors(tmp_path: Path) -> None:
    store = _saved_store(tmp_path)
    path = _manifest_path(store, "manifest-raw")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.update(
        {
            "schema_version": 1,
            "provider": False,
            "entity": ["activity"],
            "launch_context": [],
            "source_refs": {},
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert inspection.parse_ok is True
    assert inspection.schema_errors == (
        "manifest_entity_not_string",
        "manifest_launch_context_not_object",
        "manifest_provider_not_string",
        "manifest_schema_version_not_string",
        "manifest_source_refs_not_array",
    )


def test_raw_inspection_reports_missing_empty_optional_and_identity_shapes(
    tmp_path: Path,
) -> None:
    """Pre-coercion diagnostics retain precise reasons across schema families."""
    store = _saved_store(tmp_path)
    path = _manifest_path(store, "manifest-raw")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("launch_context")
    payload.pop("source_refs")
    payload.update(
        {
            "pipeline_name": " ",
            "run_id": 123,
            "run_type": "not-a-run-type",
            "runtime_config": [],
            "planned_artifacts": {},
            "workflow_name": 7,
        }
    )
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert inspection.schema_errors == (
        "manifest_launch_context_missing",
        "manifest_pipeline_name_empty",
        "manifest_planned_artifacts_not_array",
        "manifest_run_id_not_string",
        "manifest_run_type_invalid",
        "manifest_runtime_config_not_object",
        "manifest_source_refs_missing",
        "manifest_workflow_name_not_string",
    )


def test_raw_inspection_detects_required_anchor_and_identity_errors(
    tmp_path: Path,
) -> None:
    store = _saved_store(tmp_path)
    path = _manifest_path(store, "manifest-raw")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["manifest_id"] = "manifest-other"
    payload["run_id"] = "not-a-uuid"
    payload["created_at"] = "not-a-timestamp"
    payload.pop("execution_fingerprint")
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert inspection.schema_errors == (
        "manifest_created_at_invalid",
        "manifest_execution_fingerprint_missing",
        "manifest_id_mismatch",
        "manifest_run_id_invalid",
    )


def test_raw_inspection_detects_nested_collection_shape_errors(tmp_path: Path) -> None:
    store = _saved_store(tmp_path)
    path = _manifest_path(store, "manifest-raw")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_refs"] = ["not-an-object"]
    payload["planned_artifacts"] = [{"layer": 1, "path": []}]
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert inspection.schema_errors == (
        "manifest_planned_artifact_layer_not_string",
        "manifest_planned_artifact_path_not_string",
        "manifest_source_ref_not_object",
    )


def test_raw_inspection_detects_nested_snapshot_scalar_coercion(tmp_path: Path) -> None:
    store = _saved_store(tmp_path)
    path = _manifest_path(store, "manifest-raw")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_refs"] = [
        {
            "provider": "chembl",
            "entity": "activity",
            "pipeline_name": "chembl_activity",
            "input_snapshots": [
                {
                    "snapshot_id": 123,
                    "content_hash": ["hash"],
                    "immutable_uri": False,
                }
            ],
        }
    ]
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert inspection.schema_errors == (
        "manifest_input_content_hash_not_string",
        "manifest_input_immutable_uri_not_string",
        "manifest_input_snapshot_id_not_string",
    )


def test_raw_inspection_detects_code_provenance_scalar_coercion(
    tmp_path: Path,
) -> None:
    store = _saved_store(tmp_path)
    path = _manifest_path(store, "manifest-raw")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["code_provenance"]["contract_ref"] = 123
    payload["code_provenance"]["contract_version"] = False
    payload["code_provenance"]["contract_schema_hash"] = ["hash"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert inspection.schema_errors == (
        "manifest_code_provenance_contract_ref_not_string",
        "manifest_code_provenance_contract_schema_hash_not_string",
        "manifest_code_provenance_contract_version_not_string",
    )


def test_raw_inspection_rejects_malformed_schema_version_syntax(tmp_path: Path) -> None:
    store = _saved_store(tmp_path)
    path = _manifest_path(store, "manifest-raw")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = "1.foo"
    path.write_text(json.dumps(payload), encoding="utf-8")

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert inspection.schema_errors == ("manifest_schema_version_invalid",)


def test_missing_manifest_returns_bounded_diagnostic(tmp_path: Path) -> None:
    store = FileRunManifestStore(tmp_path / "run_manifest")

    inspection = store.inspect_raw_manifest("missing")

    assert inspection.parse_ok is False
    assert inspection.schema_errors == ("manifest_not_found",)


def test_inspect_raw_manifest_reads_contract_evidence_sidecar(tmp_path: Path) -> None:
    from bioetl.infrastructure.control_plane._raw_run_manifest_inspection import (
        persist_contract_evidence,
    )

    store = _saved_store(tmp_path)
    persist_contract_evidence(
        store.base_path,
        "manifest-raw",
        {
            "contract_comparison_status": "compatible",
            "contract_comparison_reason": "manifest_contract_comparison_compatible",
            "resume_contract": "n/a",
            "resume_contract_reason": "fresh_run_not_resume",
            "lock_owner_id": "n/a",
            "lock_owner_reason": "no_distributed_lock",
        },
    )

    inspection = store.inspect_raw_manifest("manifest-raw")

    assert inspection.contract_comparison_status == "compatible"
    assert inspection.resume_contract == "n/a"
    assert inspection.lock_owner_reason == "no_distributed_lock"
