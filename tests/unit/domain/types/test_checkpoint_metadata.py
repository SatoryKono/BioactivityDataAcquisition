"""Unit tests for checkpoint metadata with DQ contract compatibility.

Tests the CheckpointMetadata and CheckpointCompatibilityResult domain types.
"""

from __future__ import annotations

import pytest

from bioetl.domain.types.checkpoint_metadata import (
    CheckpointCompatibilityResult,
    CheckpointMetadata,
)


class TestCheckpointMetadata:
    """Test CheckpointMetadata domain type."""

    def test_checkpoint_metadata_creation(self) -> None:
        """Test creating CheckpointMetadata with all fields."""
        metadata = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="abc123",
            dq_policy_hash="def456",
            dq_rule_bundle_version="2024.1",
            pipeline_version="1.0.0",
            effective_config_hash="cfg_hash",
            effective_config_artifact_id="artifact-42",
            execution_fingerprint="fingerprint-1",
            run_context={"test": "value"},
        )

        assert metadata.records_processed == 1000
        assert metadata.dq_contract_compatibility_hash == "abc123"
        assert metadata.dq_policy_hash == "def456"
        assert metadata.dq_rule_bundle_version == "2024.1"
        assert metadata.pipeline_version == "1.0.0"
        assert metadata.effective_config_hash == "cfg_hash"
        assert metadata.effective_config_artifact_id == "artifact-42"
        assert metadata.execution_fingerprint == "fingerprint-1"
        assert metadata.run_context == {"test": "value"}

    def test_checkpoint_metadata_minimal(self) -> None:
        """Test creating CheckpointMetadata with minimal fields."""
        metadata = CheckpointMetadata(records_processed=500)

        assert metadata.records_processed == 500
        assert metadata.dq_contract_compatibility_hash is None
        assert metadata.dq_policy_hash is None
        assert metadata.dq_rule_bundle_version is None
        assert metadata.pipeline_version is None
        assert metadata.effective_config_hash is None
        assert metadata.effective_config_artifact_id is None
        assert metadata.execution_fingerprint is None
        assert metadata.run_context is None

    def test_checkpoint_metadata_from_legacy(self) -> None:
        """Test creating CheckpointMetadata from legacy metadata format."""
        legacy_metadata = {
            "records_processed": 750,
            "dq_contract_compatibility_hash": "legacy_hash",
            "dq_policy_hash": "legacy_policy",
            "pipeline_version": "0.9.0",
        }

        metadata = CheckpointMetadata.from_legacy_metadata(legacy_metadata)

        assert metadata.records_processed == 750
        assert metadata.dq_contract_compatibility_hash == "legacy_hash"
        assert metadata.dq_policy_hash == "legacy_policy"
        assert metadata.pipeline_version == "0.9.0"
        assert metadata.dq_rule_bundle_version is None
        assert metadata.effective_config_hash is None
        assert metadata.effective_config_artifact_id is None
        assert metadata.execution_fingerprint is None
        assert metadata.run_context is None

    def test_checkpoint_metadata_to_dict(self) -> None:
        """Test converting CheckpointMetadata to dictionary."""
        metadata = CheckpointMetadata(
            records_processed=200,
            dq_contract_compatibility_hash="hash123",
            pipeline_version="1.1.0",
        )

        metadata_dict = metadata.to_dict()

        assert metadata_dict["records_processed"] == 200
        assert metadata_dict["dq_contract_compatibility_hash"] == "hash123"
        assert metadata_dict["pipeline_version"] == "1.1.0"
        assert "dq_policy_hash" not in metadata_dict
        assert "dq_rule_bundle_version" not in metadata_dict
        assert "effective_config_hash" not in metadata_dict
        assert "effective_config_artifact_id" not in metadata_dict
        assert "execution_fingerprint" not in metadata_dict
        assert "run_context" not in metadata_dict

    def test_checkpoint_metadata_from_dict(self) -> None:
        """Test creating CheckpointMetadata from dictionary."""
        metadata_dict = {
            "records_processed": 300,
            "dq_contract_compatibility_hash": "dict_hash",
            "dq_rule_bundle_version": "2025.1",
            "effective_config_hash": "cfg_hash_2",
            "effective_config_artifact_id": "artifact-2",
            "execution_fingerprint": "fingerprint-2",
            "run_context": {"source": "test"},
        }

        metadata = CheckpointMetadata.from_dict(metadata_dict)

        assert metadata.records_processed == 300
        assert metadata.dq_contract_compatibility_hash == "dict_hash"
        assert metadata.dq_rule_bundle_version == "2025.1"
        assert metadata.effective_config_hash == "cfg_hash_2"
        assert metadata.effective_config_artifact_id == "artifact-2"
        assert metadata.execution_fingerprint == "fingerprint-2"
        assert metadata.run_context == {"source": "test"}
        assert metadata.dq_policy_hash is None
        assert metadata.pipeline_version is None

    def test_checkpoint_metadata_immutability(self) -> None:
        """Test that CheckpointMetadata is immutable."""
        metadata = CheckpointMetadata(records_processed=100)

        with pytest.raises((TypeError, AttributeError)):
            metadata.records_processed = 200  # type: ignore

    def test_checkpoint_metadata_equality(self) -> None:
        """Test equality comparison for CheckpointMetadata."""
        metadata1 = CheckpointMetadata(
            records_processed=100,
            dq_contract_compatibility_hash="hash1",
        )
        metadata2 = CheckpointMetadata(
            records_processed=100,
            dq_contract_compatibility_hash="hash1",
        )
        metadata3 = CheckpointMetadata(
            records_processed=200,
            dq_contract_compatibility_hash="hash2",
        )

        assert metadata1 == metadata2
        assert metadata1 != metadata3


class TestCheckpointCompatibilityResult:
    """Test CheckpointCompatibilityResult domain type."""

    def test_compatible_result(self) -> None:
        """Test creating a compatible result."""
        result = CheckpointCompatibilityResult.compatible_result()

        assert result.compatible is True
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True
        assert result.execution_identity_compatible is True
        assert len(result.messages) == 1
        assert "compatible for resume" in result.messages[0]

    def test_incompatible_result(self) -> None:
        """Test creating an incompatible result."""
        result = CheckpointCompatibilityResult.incompatible_result(
            dq_compatible=False,
            pipeline_compatible=True,
            execution_identity_compatible=False,
            messages=["DQ contract mismatch", "Policy version changed"],
        )

        assert result.compatible is False
        assert result.dq_compatible is False
        assert result.pipeline_compatible is True
        assert result.execution_identity_compatible is False
        assert len(result.messages) == 2
        assert "DQ contract mismatch" in result.messages[0]
        assert "Policy version changed" in result.messages[1]

    def test_incompatible_result_defaults(self) -> None:
        """Test creating an incompatible result with default messages."""
        result = CheckpointCompatibilityResult.incompatible_result()

        assert result.compatible is False
        assert result.dq_compatible is False
        assert result.pipeline_compatible is False
        assert result.execution_identity_compatible is False
        assert len(result.messages) == 0

    def test_checkpoint_compatibility_result_immutability(self) -> None:
        """Test that CheckpointCompatibilityResult is immutable."""
        result = CheckpointCompatibilityResult.compatible_result()

        with pytest.raises((TypeError, AttributeError)):
            result.compatible = False  # type: ignore

    def test_checkpoint_compatibility_result_equality(self) -> None:
        """Test equality comparison for CheckpointCompatibilityResult."""
        result1 = CheckpointCompatibilityResult.compatible_result()
        result2 = CheckpointCompatibilityResult.compatible_result()
        result3 = CheckpointCompatibilityResult.incompatible_result()

        assert result1 == result2
        assert result1 != result3


class TestCheckpointMetadataSerialization:
    """Test serialization round-trip for CheckpointMetadata."""

    def test_serialization_round_trip(self) -> None:
        """Test that metadata can be serialized and deserialized correctly."""
        original = CheckpointMetadata(
            records_processed=1500,
            dq_contract_compatibility_hash="test_hash_123",
            dq_policy_hash="policy_456",
            dq_rule_bundle_version="2024.2",
            pipeline_version="2.0.0",
            effective_config_hash="cfg_roundtrip",
            effective_config_artifact_id="artifact-roundtrip",
            execution_fingerprint="fingerprint-roundtrip",
            run_context={"environment": "test", "debug": True},
        )

        # Serialize to dict
        serialized = original.to_dict()

        # Deserialize from dict
        deserialized = CheckpointMetadata.from_dict(serialized)

        # Should be equal
        assert original == deserialized
        assert original.records_processed == deserialized.records_processed
        assert original.dq_contract_compatibility_hash == deserialized.dq_contract_compatibility_hash
        assert original.dq_policy_hash == deserialized.dq_policy_hash
        assert original.dq_rule_bundle_version == deserialized.dq_rule_bundle_version
        assert original.pipeline_version == deserialized.pipeline_version
        assert original.effective_config_hash == deserialized.effective_config_hash
        assert (
            original.effective_config_artifact_id
            == deserialized.effective_config_artifact_id
        )
        assert original.execution_fingerprint == deserialized.execution_fingerprint
        assert original.run_context == deserialized.run_context

    def test_legacy_serialization_round_trip(self) -> None:
        """Test that legacy metadata can be round-tripped through new format."""
        legacy_data = {
            "records_processed": 800,
            "dq_contract_compatibility_hash": "legacy_hash",
            "pipeline_version": "1.5.0",
        }

        # Convert from legacy
        metadata = CheckpointMetadata.from_legacy_metadata(legacy_data)

        # Serialize to dict
        serialized = metadata.to_dict()

        # Deserialize from dict
        deserialized = CheckpointMetadata.from_dict(serialized)

        # Should maintain all data
        assert deserialized.records_processed == 800
        assert deserialized.dq_contract_compatibility_hash == "legacy_hash"
        assert deserialized.pipeline_version == "1.5.0"

    def test_minimal_serialization(self) -> None:
        """Test serialization of minimal metadata."""
        minimal = CheckpointMetadata(records_processed=50)
        serialized = minimal.to_dict()

        # Should only contain records_processed
        assert serialized == {"records_processed": 50}

        # Deserialize back
        deserialized = CheckpointMetadata.from_dict(serialized)
        assert deserialized == minimal
