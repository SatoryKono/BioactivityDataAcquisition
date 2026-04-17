"""CI validation tests for configuration stability.

Tests that ensure DQ configurations remain stable and compatible across runs.
These tests are designed to run in CI pipelines to catch configuration drift.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import yaml

from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointManagerService,
)
from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


class TestConfigStability:
    """Test configuration stability across different scenarios."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        from bioetl.infrastructure.observability.noop_logger import NoOpLogger

        self.logger = NoOpLogger()
        self.service = CheckpointCompatibilityService(logger=self.logger)

    def test_dq_contract_hash_stability(self) -> None:
        """Test that DQ contract hashes remain stable for identical configurations."""
        # Create identical metadata instances
        metadata1 = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="stable_hash_123",
            dq_policy_hash="policy_456",
            pipeline_version="1.0.0",
        )

        metadata2 = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="stable_hash_123",
            dq_policy_hash="policy_456",
            pipeline_version="1.0.0",
        )

        # Should be compatible
        result = self.service.validate_checkpoint_compatibility(metadata1, metadata2)
        assert result.compatible is True
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True

    def test_config_serialization_stability(self) -> None:
        """Test that config serialization produces consistent results."""
        metadata = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="test_hash",
            dq_rule_bundle_version="2024.1",
        )

        # Serialize multiple times
        dict1 = metadata.to_dict()
        dict2 = metadata.to_dict()

        # Should produce identical results
        assert dict1 == dict2
        assert json.dumps(dict1, sort_keys=True) == json.dumps(dict2, sort_keys=True)

    def test_config_deserialization_stability(self) -> None:
        """Test that config deserialization produces consistent results."""
        config_dict = {
            "records_processed": 750,
            "dq_contract_compatibility_hash": "deserialize_hash",
            "pipeline_version": "1.1.0",
        }

        # Deserialize multiple times
        metadata1 = CheckpointMetadata.from_dict(config_dict)
        metadata2 = CheckpointMetadata.from_dict(config_dict)

        # Should produce identical results
        assert metadata1 == metadata2
        assert metadata1.to_dict() == metadata2.to_dict()

    def test_legacy_config_compatibility(self) -> None:
        """Test that legacy configs remain compatible with new format."""
        legacy_config = {
            "records_processed": 200,
            "dq_contract_compatibility_hash": "legacy_hash",
        }

        # Convert from legacy
        metadata = CheckpointMetadata.from_legacy_metadata(legacy_config)

        # Should maintain all legacy data
        assert metadata.records_processed == 200
        assert metadata.dq_contract_compatibility_hash == "legacy_hash"

        # Should serialize back correctly
        serialized = metadata.to_dict()
        assert serialized["records_processed"] == 200
        assert serialized["dq_contract_compatibility_hash"] == "legacy_hash"

    def test_config_file_stability(self, tmp_path: Path) -> None:
        """Test that config files can be written and read consistently."""
        config_file = tmp_path / "test_config.json"

        # Create test metadata
        original_metadata = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="file_test_hash",
            dq_policy_hash="file_policy_hash",
            pipeline_version="2.0.0",
        )

        # Write to file
        with open(config_file, "w") as f:
            json.dump(original_metadata.to_dict(), f)

        # Read back
        with open(config_file) as f:
            config_dict = json.load(f)

        # Deserialize
        loaded_metadata = CheckpointMetadata.from_dict(config_dict)

        # Should be identical
        assert original_metadata == loaded_metadata

    def test_yaml_config_stability(self, tmp_path: Path) -> None:
        """Test that YAML config files maintain stability."""
        config_file = tmp_path / "test_config.yaml"

        # Create test metadata
        original_metadata = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="yaml_test_hash",
            dq_rule_bundle_version="2024.2",
        )

        # Write to YAML
        with open(config_file, "w") as f:
            yaml.dump(original_metadata.to_dict(), f)

        # Read back
        with open(config_file) as f:
            config_dict = yaml.safe_load(f)

        # Deserialize
        loaded_metadata = CheckpointMetadata.from_dict(config_dict)

        # Should be identical
        assert original_metadata == loaded_metadata

    def test_checkpoint_compatibility_stability(self) -> None:
        """Test that checkpoint compatibility results are stable."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="current_hash",
            pipeline_version="1.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="current_hash",
            pipeline_version="1.0.0",
        )

        # Validate multiple times
        result1 = self.service.validate_checkpoint_compatibility(current, checkpoint)
        result2 = self.service.validate_checkpoint_compatibility(current, checkpoint)

        # Should produce identical results
        assert result1 == result2
        assert result1.compatible == result2.compatible
        assert result1.messages == result2.messages

    def test_incompatible_config_stability(self) -> None:
        """Test that incompatible configs produce stable results."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="new_hash",
            pipeline_version="2.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="old_hash",
            pipeline_version="1.0.0",
        )

        # Validate multiple times
        result1 = self.service.validate_checkpoint_compatibility(current, checkpoint)
        result2 = self.service.validate_checkpoint_compatibility(current, checkpoint)

        # Should produce identical incompatible results
        assert result1 == result2
        assert result1.compatible is False
        assert result2.compatible is False
        assert result1.messages == result2.messages

    def test_lenient_mode_stability(self) -> None:
        """Test that lenient mode produces stable results."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="new_hash",
            pipeline_version="1.1.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="old_hash",
            pipeline_version="1.0.0",
        )

        # Validate multiple times in lenient mode
        result1 = self.service.validate_minimum_compatibility(current, checkpoint)
        result2 = self.service.validate_minimum_compatibility(current, checkpoint)

        # Should produce identical results
        assert result1 == result2
        assert result1.compatible == result2.compatible
        assert result1.messages == result2.messages


class TestConfigVersioning:
    """Test configuration versioning and compatibility."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        from bioetl.infrastructure.observability.noop_logger import NoOpLogger

        self.logger = NoOpLogger()
        self.service = CheckpointCompatibilityService(logger=self.logger)

    def test_major_version_compatibility(self) -> None:
        """Test that major version changes are detected correctly."""
        current = CheckpointMetadata(
            records_processed=1000,
            pipeline_version="2.0.0",  # Major version 2
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            pipeline_version="1.5.0",  # Major version 1
        )

        # Should be incompatible due to major version change
        result = self.service.validate_checkpoint_compatibility(current, checkpoint)
        assert result.compatible is False
        assert result.pipeline_compatible is False

    def test_minor_version_compatibility_strict(self) -> None:
        """Test that minor version changes are detected in strict mode."""
        current = CheckpointMetadata(
            records_processed=1000,
            pipeline_version="1.2.0",  # Minor version 2
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            pipeline_version="1.1.0",  # Minor version 1
        )

        # Should be incompatible in strict mode
        result = self.service.validate_checkpoint_compatibility(current, checkpoint)
        assert result.compatible is False
        assert result.pipeline_compatible is False

    def test_minor_version_compatibility_lenient(self) -> None:
        """Test that minor version changes are allowed in lenient mode."""
        current = CheckpointMetadata(
            records_processed=1000,
            pipeline_version="1.2.0",  # Minor version 2
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            pipeline_version="1.1.0",  # Minor version 1
        )

        # Should be compatible in lenient mode
        result = self.service.validate_minimum_compatibility(current, checkpoint)
        assert result.compatible is True
        assert result.pipeline_compatible is True

    def test_patch_version_compatibility(self) -> None:
        """Test that patch version changes are handled correctly."""
        current = CheckpointMetadata(
            records_processed=1000,
            pipeline_version="1.0.2",  # Patch version 2
            dq_contract_compatibility_hash="same_hash",  # Need same DQ hash for compatibility
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            pipeline_version="1.0.1",  # Patch version 1
            dq_contract_compatibility_hash="same_hash",  # Need same DQ hash for compatibility
        )

        # In strict mode, any version mismatch makes it incompatible
        result = self.service.validate_checkpoint_compatibility(current, checkpoint)
        assert result.compatible is False  # Strict mode: versions must match exactly
        assert result.dq_compatible is True
        assert result.pipeline_compatible is False
        assert "Pipeline version mismatch" in result.messages[1]

        # In lenient mode, patch versions should be compatible
        result_lenient = self.service.validate_minimum_compatibility(
            current, checkpoint
        )
        assert (
            result_lenient.compatible is True
        )  # Lenient mode allows patch version changes
        assert result_lenient.dq_compatible is True
        assert result_lenient.pipeline_compatible is True

    def test_malformed_version_handling(self) -> None:
        """Test handling of malformed version strings."""
        current = CheckpointMetadata(
            records_processed=1000,
            pipeline_version="not-a-version",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            pipeline_version="also-not-a-version",
        )

        # Should handle gracefully without crashing
        result = self.service.validate_checkpoint_compatibility(current, checkpoint)
        # Behavior may vary, but should not crash
        assert result is not None


class TestConfigHashStability:
    """Test stability of configuration hashes."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        from bioetl.infrastructure.observability.noop_logger import NoOpLogger

        self.logger = NoOpLogger()
        self.service = CheckpointCompatibilityService(logger=self.logger)

    def test_dq_contract_hash_consistency(self) -> None:
        """Test that DQ contract hashes are used consistently."""
        # Same hash should always be compatible
        metadata1 = CheckpointMetadata(
            records_processed=100,
            dq_contract_compatibility_hash="consistent_hash",
        )

        metadata2 = CheckpointMetadata(
            records_processed=200,
            dq_contract_compatibility_hash="consistent_hash",
        )

        result = self.service.validate_checkpoint_compatibility(metadata1, metadata2)
        assert result.compatible is True
        assert result.dq_compatible is True

    def test_dq_policy_hash_consistency(self) -> None:
        """Test that DQ policy hashes are handled consistently."""
        metadata1 = CheckpointMetadata(
            records_processed=100,
            dq_policy_hash="policy_hash_123",
        )

        metadata2 = CheckpointMetadata(
            records_processed=200,
            dq_policy_hash="policy_hash_123",
        )

        # Policy hashes don't affect basic compatibility
        result = self.service.validate_checkpoint_compatibility(metadata1, metadata2)
        assert result.compatible is True

    def test_rule_bundle_version_consistency(self) -> None:
        """Test that rule bundle versions are handled consistently."""
        metadata1 = CheckpointMetadata(
            records_processed=100,
            dq_rule_bundle_version="2024.1",
        )

        metadata2 = CheckpointMetadata(
            records_processed=200,
            dq_rule_bundle_version="2024.1",
        )

        # Same rule bundle versions should be compatible
        result = self.service.validate_checkpoint_compatibility(metadata1, metadata2)
        assert result.compatible is True

    def test_hash_changes_detected(self) -> None:
        """Test that hash changes are detected correctly."""
        metadata1 = CheckpointMetadata(
            records_processed=100,
            dq_contract_compatibility_hash="original_hash",
        )

        metadata2 = CheckpointMetadata(
            records_processed=200,
            dq_contract_compatibility_hash="changed_hash",
        )

        # Different hashes should be incompatible
        result = self.service.validate_checkpoint_compatibility(metadata1, metadata2)
        assert result.compatible is False
        assert result.dq_compatible is False


class _InMemoryCheckpointPort:
    """Minimal checkpoint port for integration-style resume policy checks."""

    def __init__(self) -> None:
        self._records: dict[str, tuple[object, dict[str, object]]] = {}

    async def save(
        self,
        pipeline: str,
        run_id: object,
        metadata: dict[str, object],
    ) -> None:
        await asyncio.sleep(0)
        self._records[pipeline] = (run_id, metadata)

    async def load(
        self,
        pipeline: str,
    ) -> tuple[object, dict[str, object]] | None:
        await asyncio.sleep(0)
        return self._records.get(pipeline)

    async def list_all(self) -> list[str]:
        await asyncio.sleep(0)
        return sorted(self._records)

    async def delete(self, pipeline: str) -> None:
        await asyncio.sleep(0)
        self._records.pop(pipeline, None)

    async def aclose(self) -> None:
        await asyncio.sleep(0)
        return None


@pytest.mark.integration
class TestCheckpointResumeCompatibilityPolicy:
    """Integration checks for resume behavior under compatibility policies."""

    async def _save_checkpoint_metadata(
        self,
        checkpoint_port: _InMemoryCheckpointPort,
        *,
        run_id: object,
        **metadata: object,
    ) -> None:
        """Persist one checkpoint payload for manager-level resume checks."""
        payload: dict[str, object] = {"records_processed": 100}
        payload.update(metadata)
        await checkpoint_port.save(
            pipeline="chembl_activity",
            run_id=run_id,
            metadata=payload,
        )

    def _build_manager(
        self,
        *,
        checkpoint_port: _InMemoryCheckpointPort,
        logger: MagicMock,
        run_id: object,
        current_metadata: CheckpointMetadata,
        compatibility_policy: str,
    ) -> CheckpointManagerService:
        """Create a manager wired like the real resume path."""
        return CheckpointManagerService(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name="chembl_activity",
            run_id=run_id,
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=logger
            ),
            current_metadata=current_metadata,
            compatibility_policy=compatibility_policy,
        )

    @pytest.mark.asyncio
    async def test_observe_policy_blocks_resume_on_execution_identity_mismatch(
        self,
    ) -> None:
        checkpoint_port = _InMemoryCheckpointPort()
        logger = MagicMock()
        run_id = uuid4()

        await checkpoint_port.save(
            pipeline="chembl_activity",
            run_id=run_id,
            metadata={
                "records_processed": 120,
                "effective_config_hash": "a" * 64,
            },
        )

        manager = CheckpointManagerService(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name="chembl_activity",
            run_id=run_id,
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=logger
            ),
            current_metadata=CheckpointMetadata(
                records_processed=0,
                effective_config_hash="b" * 64,
            ),
            compatibility_policy="observe",
        )

        result = await manager.load_checkpoint()

        assert result is None
        warning_messages = [
            call.args[0] for call in logger.warning.call_args_list if call.args
        ]
        assert any(
            "resume blocked despite observe policy" in message
            for message in warning_messages
        )

    @pytest.mark.asyncio
    async def test_soft_fail_policy_blocks_resume_on_execution_identity_mismatch(
        self,
    ) -> None:
        checkpoint_port = _InMemoryCheckpointPort()
        logger = MagicMock()
        run_id = uuid4()

        await checkpoint_port.save(
            pipeline="chembl_activity",
            run_id=run_id,
            metadata={
                "records_processed": 90,
                "effective_config_hash": "a" * 64,
            },
        )

        manager = CheckpointManagerService(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name="chembl_activity",
            run_id=run_id,
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=logger
            ),
            current_metadata=CheckpointMetadata(
                records_processed=0,
                effective_config_hash="b" * 64,
            ),
            compatibility_policy="soft_fail",
        )

        result = await manager.load_checkpoint()

        assert result is None
        warning_messages = [
            call.args[0] for call in logger.warning.call_args_list if call.args
        ]
        assert any("soft_fail policy" in message for message in warning_messages)

    @pytest.mark.asyncio
    async def test_hard_fail_policy_raises_on_execution_identity_mismatch(self) -> None:
        checkpoint_port = _InMemoryCheckpointPort()
        logger = MagicMock()
        run_id = uuid4()

        await checkpoint_port.save(
            pipeline="chembl_activity",
            run_id=run_id,
            metadata={
                "records_processed": 75,
                "execution_fingerprint": "fingerprint-old",
            },
        )

        manager = CheckpointManagerService(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name="chembl_activity",
            run_id=run_id,
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=logger
            ),
            current_metadata=CheckpointMetadata(
                records_processed=0,
                execution_fingerprint="fingerprint-new",
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(ValueError, match="hard_fail policy"):
            await manager.load_checkpoint()

    @pytest.mark.asyncio
    async def test_hard_fail_policy_raises_on_manifest_identity_mismatch(self) -> None:
        checkpoint_port = _InMemoryCheckpointPort()
        logger = MagicMock()
        run_id = uuid4()

        await self._save_checkpoint_metadata(
            checkpoint_port,
            run_id=run_id,
            manifest_id="manifest-old",
        )

        manager = self._build_manager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            run_id=run_id,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                manifest_id="manifest-new",
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(ValueError, match="Manifest identity mismatch"):
            await manager.load_checkpoint()

    @pytest.mark.asyncio
    async def test_hard_fail_policy_raises_on_contract_reference_mismatch(
        self,
    ) -> None:
        checkpoint_port = _InMemoryCheckpointPort()
        logger = MagicMock()
        run_id = uuid4()

        await self._save_checkpoint_metadata(
            checkpoint_port,
            run_id=run_id,
            contract_ref="chembl.activity",
            contract_version="1.0.0",
        )

        manager = self._build_manager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            run_id=run_id,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                contract_ref="chembl.assay",
                contract_version="1.0.0",
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(ValueError, match="Contract reference mismatch"):
            await manager.load_checkpoint()

    @pytest.mark.asyncio
    async def test_hard_fail_policy_raises_on_exact_replay_snapshot_mismatch(
        self,
    ) -> None:
        checkpoint_port = _InMemoryCheckpointPort()
        logger = MagicMock()
        run_id = uuid4()

        await self._save_checkpoint_metadata(
            checkpoint_port,
            run_id=run_id,
            exact_replay=True,
            input_snapshot_ids=["bronze:chembl.activity:2025-01-01"],
        )

        manager = self._build_manager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            run_id=run_id,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                exact_replay=True,
                input_snapshot_ids=("bronze:chembl.activity:2025-01-02",),
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(ValueError, match="Input snapshot identity mismatch"):
            await manager.load_checkpoint()

    @pytest.mark.asyncio
    async def test_hard_fail_policy_raises_on_composite_run_identity_mismatch(
        self,
    ) -> None:
        checkpoint_port = _InMemoryCheckpointPort()
        logger = MagicMock()
        run_id = uuid4()

        await self._save_checkpoint_metadata(
            checkpoint_port,
            run_id=run_id,
            composite_run_identity="composite-run-old",
        )

        manager = self._build_manager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            run_id=run_id,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                composite_run_identity="composite-run-new",
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(ValueError, match="Composite run identity mismatch"):
            await manager.load_checkpoint()
