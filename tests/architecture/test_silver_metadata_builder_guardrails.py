"""Architecture guardrails for Silver metadata sidecar identity paths."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = (
    ROOT
    / "src/bioetl/infrastructure/storage/silver/operations/metadata_sidecar_adapter.py"
)
LEGACY_TARGET = (
    ROOT / "src/bioetl/infrastructure/storage/silver/operations/metadata_builders.py"
)
TARGET_MODULE = (
    "bioetl.infrastructure.storage.silver.operations.metadata_sidecar_adapter"
)
LEGACY_TARGET_MODULE = (
    "bioetl.infrastructure.storage.silver.operations.metadata_builders"
)
ACTIVE_SILVER_METADATA_PATHS = (
    ROOT
    / "src/bioetl/infrastructure/storage/silver/operations/metadata_audit_operations.py",
    ROOT
    / "src/bioetl/infrastructure/storage/silver/operations/metadata_dq_operations.py",
    ROOT
    / "src/bioetl/infrastructure/storage/silver/operations/metadata_finalization_operations.py",
    ROOT
    / "src/bioetl/infrastructure/storage/silver/operations/metadata_write_operations.py",
    ROOT
    / "src/bioetl/infrastructure/storage/silver/operations/metadata_write_support.py",
    ROOT
    / "src/bioetl/infrastructure/storage/silver/operations/metadata_finalization_support.py",
    ROOT / "src/bioetl/infrastructure/storage/silver/writer_runtime_facade.py",
)


@pytest.mark.architecture
def test_legacy_silver_metadata_builder_module_has_been_removed() -> None:
    """The old metadata_builders module name must not return to runtime code."""
    assert not LEGACY_TARGET.exists()


@pytest.mark.architecture
def test_silver_metadata_sidecar_adapter_does_not_emit_placeholder_identity() -> None:
    """Silver sidecars must not publish placeholder content or run-derived IDs."""
    source = TARGET.read_text(encoding="utf-8")

    assert "SIDECAR_ADAPTER_PRODUCTION_STATUS" in source
    assert "quarantined_compatibility_only" in source
    assert "placeholder-hash" not in source
    assert "{request.table_name}-{request.run_id" not in source
    assert "build_dataset_content_hash" in source
    assert "DatasetRef" in source


@pytest.mark.architecture
def test_silver_metadata_sidecar_adapter_carries_control_plane_provenance() -> None:
    """The quarantined adapter must not silently drop canonical run anchors."""
    source = TARGET.read_text(encoding="utf-8")
    required_fragments = (
        "extract_control_plane_provenance_from_records",
        "execution_fingerprint=request.execution_fingerprint",
        "git_commit=request.git_commit",
        "dependency_lock_hash=request.dependency_lock_hash",
        "effective_config_hash=request.effective_config_hash",
        "effective_config_artifact_id=request.effective_config_artifact_id",
        "contract_ref=request.contract_ref",
        "normalization_profile_ref=request.normalization_profile_ref",
        "normalization_profile_hash=request.normalization_profile_hash",
        "dq_contract_compatibility_hash=request.dq_contract_compatibility_hash",
    )

    missing = [fragment for fragment in required_fragments if fragment not in source]
    assert not missing


@pytest.mark.architecture
def test_source_tree_does_not_reintroduce_silver_placeholder_identity() -> None:
    """Placeholder hashes and run-derived artifact IDs are forbidden in src."""
    violations: list[str] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if (
            "placeholder-hash" in source
            or "{request.table_name}-{request.run_id" in source
        ):
            violations.append(path.relative_to(ROOT).as_posix())

    assert not violations


@pytest.mark.architecture
def test_runtime_code_does_not_import_quarantined_silver_sidecar_adapter() -> None:
    """Active Silver runtime paths must use MetadataCoordinatorPort, not adapter."""
    importers: set[str] = set()
    for path in sorted((ROOT / "src").rglob("*.py")):
        if path == TARGET:
            continue
        source = path.read_text(encoding="utf-8")
        if TARGET_MODULE in source:
            importers.add(path.relative_to(ROOT).as_posix())

    assert not importers


@pytest.mark.architecture
def test_active_silver_metadata_paths_do_not_extract_record_provenance() -> None:
    """Silver production paths must not assemble provenance from record payloads."""
    forbidden_fragments = (
        "extract_control_plane_provenance_from_records",
        "_CONTROL_PLANE_PROVENANCE_RECORD_KEYS",
        "_build_silver_sidecar_metadata",
        "_SilverMetadataSidecarRequest",
    )
    violations: dict[str, list[str]] = {}
    for path in ACTIVE_SILVER_METADATA_PATHS:
        source = path.read_text(encoding="utf-8")
        found = [fragment for fragment in forbidden_fragments if fragment in source]
        if found:
            violations[path.relative_to(ROOT).as_posix()] = found

    assert not violations


@pytest.mark.architecture
def test_runtime_code_does_not_import_legacy_silver_metadata_builder() -> None:
    """Runtime code must not import the removed metadata_builders module name."""
    importers: list[str] = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if LEGACY_TARGET_MODULE in source:
            importers.append(path.relative_to(ROOT).as_posix())

    assert not importers
