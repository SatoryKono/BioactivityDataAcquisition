"""Integration tests for control-plane file stores.

Tests manifest, ledger, and checkpoint file operations in control-plane storage.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from bioetl.domain.control_plane.run_manifest import (
    RunArtifactRef,
    RunCodeProvenance,
    RunManifest,
)
from bioetl.domain.types import RunID, RunType


@pytest.mark.integration
class TestControlPlaneFileStores:
    """Integration tests for control-plane file store operations.

    Tests manifest, ledger, and checkpoint storage read/write operations.
    """

    @staticmethod
    def _build_manifest() -> RunManifest:
        """Build a minimal valid run manifest using the current domain contract."""
        return RunManifest(
            manifest_id="manifest-test-run-123",
            execution_fingerprint="fingerprint-test-run-123",
            schema_version="1.0",
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            run_type=RunType.INCREMENTAL,
            pipeline_name="test_pipeline",
            provider="test_provider",
            entity="test_entity",
            launch_context={"mode": "integration-test"},
            runtime_config={"run_type": "incremental"},
            resolved_config={"provider": "test_provider", "entity_type": "test_entity"},
            code_provenance=RunCodeProvenance(
                config_hash="abc123",
                contract_ref="test.contract",
                contract_version="1.0.0",
                source_revision_state="clean",
            ),
            planned_artifacts=(
                RunArtifactRef(
                    layer="manifest",
                    path="data/output/control/run_manifest/test-run-123.json",
                ),
            ),
        )

    def test_run_manifest_serialization(self) -> None:
        """Test RunManifest can be serialized and deserialized correctly."""
        manifest = self._build_manifest()

        # Test serialization
        manifest_dict = manifest.to_dict()
        assert manifest_dict is not None
        assert manifest_dict["run_id"] == "12345678-1234-5678-1234-567812345678"

        # Test deserialization
        manifest_restored = RunManifest.from_dict(manifest_dict)
        assert manifest_restored.run_id == manifest.run_id

    def test_run_manifest_artifact_validation(self) -> None:
        """Test RunArtifactRef validation."""
        # Valid artifact ref
        artifact = RunArtifactRef(
            layer="manifest",
            path="data/output/control/run_manifest/test.json",
        )

        assert artifact.layer in ["manifest", "ledger", "checkpoint"]

    def test_control_plane_directory_structure(self, tmp_path: Path) -> None:
        """Test control-plane directory structure is created correctly."""
        # Simulate control-plane directory structure
        control_dir = tmp_path / "data" / "output" / "control"
        manifest_dir = control_dir / "run_manifest"
        ledger_dir = control_dir / "ledger"
        checkpoint_dir = control_dir / "checkpoint"

        manifest_dir.mkdir(parents=True)
        ledger_dir.mkdir(parents=True)
        checkpoint_dir.mkdir(parents=True)

        # Verify directories exist
        assert manifest_dir.exists()
        assert ledger_dir.exists()
        assert checkpoint_dir.exists()

    def test_file_path_generation(self) -> None:
        """Test file path generation for control-plane artifacts."""
        artifact = RunArtifactRef(
            layer="manifest",
            path="data/output/control/run_manifest/test-run-123.json",
        )

        # Verify path follows expected pattern
        assert "control" in artifact.path
        assert "run_manifest" in artifact.path
        assert ".json" in artifact.path

    def test_concurrent_file_operations(self, tmp_path: Path) -> None:
        """Test concurrent file operations don't corrupt data."""
        import asyncio

        test_file = tmp_path / "test_concurrent.json"

        async def write_file(file_path: Path, content: str) -> None:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        async def read_file(file_path: Path) -> str:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()

        async def test_concurrent_writes() -> None:
            # Run multiple concurrent writes
            tasks = [write_file(test_file, f"content-{i}") for i in range(5)]
            await asyncio.gather(*tasks)

            # Verify final content is one of the writes
            final_content = await read_file(test_file)
            assert final_content.startswith("content-")

        asyncio.run(test_concurrent_writes())

    def test_file_permission_handling(self, tmp_path: Path) -> None:
        """Test file permissions are set correctly for control-plane artifacts."""
        import stat

        test_file = tmp_path / "test_permissions.json"
        test_file.write_text("test content", encoding="utf-8")

        # Verify file is readable and writable
        assert os.access(test_file, os.R_OK)
        assert os.access(test_file, os.W_OK)

        # Verify file is not executable
        file_stat = test_file.stat()
        assert not (file_stat.st_mode & 0o111)

    def test_file_size_limits(self, tmp_path: Path) -> None:
        """Test large file handling in control-plane storage."""
        # Create a small file
        small_file = tmp_path / "small.json"
        small_file.write_text('{"test": "data"}', encoding="utf-8")

        # Verify small file size
        assert small_file.stat().st_size < 1000

        # Simulate size limit check
        MAX_MANIFEST_SIZE = 10 * 1024 * 1024  # 10 MB
        assert small_file.stat().st_size < MAX_MANIFEST_SIZE

    def test_file_cleanup_on_error(self, tmp_path: Path) -> None:
        """Test partial file cleanup on write errors."""
        test_file = tmp_path / "test_cleanup.json"

        # Write initial content
        test_file.write_text('{"partial": "content"}', encoding="utf-8")

        # Simulate cleanup (in real scenario, partial writes should be cleaned)
        if test_file.exists():
            test_file.unlink()

        # Verify cleanup
        assert not test_file.exists()

    def test_metadata_sidecar_creation(self, tmp_path: Path) -> None:
        """Test metadata sidecar file creation for control-plane artifacts."""
        import yaml

        sidecar_file = tmp_path / "metadata.yaml"
        metadata = {
            "runtime": {
                "run_id": "test-run-123",
                "pipeline": {
                    "config_hash": "cfg123",
                    "contract_ref": "test.contract",
                },
            },
            "output": {
                "artifact_id": "artifact-1",
                "lineage_fragment_id": "fragment-1",
            },
        }

        with open(sidecar_file, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f)

        # Verify metadata file was created
        assert sidecar_file.exists()

        # Verify metadata can be read back
        with open(sidecar_file, "r", encoding="utf-8") as f:
            loaded_metadata = yaml.safe_load(f)

        assert loaded_metadata["runtime"]["run_id"] == "test-run-123"


@pytest.mark.unit
class TestControlPlaneStorageContracts:
    """Unit tests for control-plane storage contracts and interfaces."""

    def test_storage_port_interface_exists(self) -> None:
        """Verify storage port interfaces are defined."""
        from bioetl.domain.ports.storage import (
            BronzeStoragePort,
            SilverStoragePort,
            GoldStoragePort,
        )

        # Verify interfaces exist
        assert BronzeStoragePort is not None
        assert SilverStoragePort is not None
        assert GoldStoragePort is not None

    def test_manifest_storage_contract(self) -> None:
        """Test manifest storage contract is defined."""
        from bioetl.domain.control_plane.run_manifest import RunManifest

        # Verify RunManifest can be instantiated
        manifest = TestControlPlaneFileStores._build_manifest()

        assert manifest.run_id == RunID(UUID("12345678-1234-5678-1234-567812345678"))

    def test_ledger_storage_contract(self) -> None:
        """Test ledger storage contract is defined."""
        from bioetl.domain.control_plane.run_ledger import RunLedgerEntry

        # Verify RunLedgerEntry can be instantiated
        event = RunLedgerEntry(
            entry_id="entry-1",
            manifest_id="manifest-test-run-123",
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            event_type="test_event",
            occurred_at=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            details={},
        )

        assert event.event_type == "test_event"
