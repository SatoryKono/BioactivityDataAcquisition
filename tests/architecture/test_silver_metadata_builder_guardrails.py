"""Architecture guardrails for Silver metadata sidecar identity paths."""

from __future__ import annotations

from pathlib import Path
import subprocess

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


def _rg_hits(pattern: str) -> list[str]:
    result = subprocess.run(
        ["rg", "-l", pattern, str(ROOT / "src"), "-g", "*.py"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in {0, 1}:
        raise RuntimeError(result.stderr.strip() or f"rg failed for {pattern!r}")
    return [
        Path(line).resolve().relative_to(ROOT).as_posix()
        for line in result.stdout.splitlines()
        if line.strip()
    ]


@pytest.mark.architecture
def test_legacy_silver_metadata_builder_module_has_been_removed() -> None:
    """The old metadata_builders module name must not return to runtime code."""
    assert not LEGACY_TARGET.exists()


@pytest.mark.architecture
def test_quarantined_silver_metadata_sidecar_adapter_has_been_removed() -> None:
    """The quarantined sidecar adapter must not persist in production src."""
    assert not TARGET.exists()


@pytest.mark.architecture
def test_source_tree_does_not_reintroduce_silver_placeholder_identity() -> None:
    """Placeholder hashes and run-derived artifact IDs are forbidden in src."""
    violations = sorted(
        {
            *_rg_hits("placeholder-hash"),
            *_rg_hits(r"\{request\.table_name\}-\{request\.run_id"),
        }
    )

    assert not violations


@pytest.mark.architecture
def test_runtime_code_does_not_import_quarantined_silver_sidecar_adapter() -> None:
    """Active Silver runtime paths must use MetadataCoordinatorPort, not adapter."""
    importers = _rg_hits(TARGET_MODULE)

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
    importers = _rg_hits(LEGACY_TARGET_MODULE)

    assert not importers
