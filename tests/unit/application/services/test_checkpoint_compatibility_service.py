"""Unit tests for checkpoint compatibility service.

Tests the CheckpointCompatibilityService for DQ contract validation.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.domain.types.checkpoint_metadata import (
    CheckpointMetadata,
)


class TestCheckpointCompatibilityService:
    """Test CheckpointCompatibilityService."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.logger = MagicMock()
        self.service = CheckpointCompatibilityService(logger=self.logger)

    def test_validate_compatible_checkpoint(self) -> None:
        """Test validation of compatible checkpoint."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="abc123",
            dq_policy_hash="def456",
            pipeline_version="1.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="abc123",
            dq_policy_hash="def456",
            pipeline_version="1.0.0",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is True
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True
        assert len(result.messages) == 1  # "Checkpoint is compatible for resume"
        assert "Checkpoint is compatible for resume" in result.messages[0]

        # Verify logging
        self.logger.info.assert_called_once()
        call_args = self.logger.info.call_args[0]
        assert "compatibility validation passed" in call_args[0]

    def test_validate_incompatible_dq_contract(self) -> None:
        """Test validation fails when DQ contracts differ."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="current_hash",
            pipeline_version="1.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="old_hash",
            pipeline_version="1.0.0",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.dq_compatible is False
        assert result.pipeline_compatible is True
        assert len(result.messages) == 3
        assert "DQ contract mismatch" in result.messages[0]
        assert "Pipeline versions are compatible" in result.messages[1]
        assert "Canonical checkpoint execution identity mismatch" in result.messages[2]

        # Verify logging
        self.logger.warning.assert_called_once()
        call_args = self.logger.warning.call_args[0]
        assert "compatibility validation failed" in call_args[0]

    def test_validate_incompatible_pipeline_version(self) -> None:
        """Test validation fails when pipeline versions differ."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="2.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.dq_compatible is True
        assert result.pipeline_compatible is False
        assert len(result.messages) == 3
        assert "DQ contracts are compatible" in result.messages[0]
        assert "Pipeline version mismatch" in result.messages[1]
        assert "Canonical checkpoint execution identity mismatch" in result.messages[2]

    def test_validate_missing_dq_contract_info(self) -> None:
        """Test validation when DQ contract info is missing (backward compatibility)."""
        current = CheckpointMetadata(
            records_processed=1000,
            # No DQ contract info
            pipeline_version="1.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            # No DQ contract info
            pipeline_version="1.0.0",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is True
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True
        # When DQ info is missing, it should still be compatible
        assert len(result.messages) == 1  # "Checkpoint is compatible for resume"
        assert "Checkpoint is compatible for resume" in result.messages[0]

    def test_validate_partial_dq_info(self) -> None:
        """Test validation when only one side has DQ contract info."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="current_hash",
            pipeline_version="1.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            # No DQ contract info
            pipeline_version="1.0.0",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True
        assert result.execution_identity_compatible is False
        assert any(
            "Canonical checkpoint execution identity mismatch" in msg
            for msg in result.messages
        )

    def test_validate_rule_bundle_version_change(self) -> None:
        """Test that rule bundle version changes are reported but don't block resume."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            dq_rule_bundle_version="2024.2",
            pipeline_version="1.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            dq_rule_bundle_version="2024.1",
            pipeline_version="1.0.0",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is True  # Still compatible
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True
        # Rule bundle changes don't block resume, so should be compatible
        assert len(result.messages) == 1  # "Checkpoint is compatible for resume"
        assert "Checkpoint is compatible for resume" in result.messages[0]

    def test_validate_execution_identity_hash_mismatch(self) -> None:
        """Execution identity mismatch should block resume in strict mode."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            effective_config_hash="a" * 64,
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            effective_config_hash="b" * 64,
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any(
            "Canonical checkpoint execution identity mismatch" in msg
            for msg in result.messages
        )
        assert any("Effective config hash mismatch" in msg for msg in result.messages)

    def test_validate_execution_fingerprint_mismatch(self) -> None:
        """Fingerprint mismatch should override compatible DQ/version checks."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            execution_fingerprint="fp-current",
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            execution_fingerprint="fp-checkpoint",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any("Execution fingerprint mismatch" in msg for msg in result.messages)

    def test_validate_manifest_identity_mismatch(self) -> None:
        """Manifest identity mismatch should block resume."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            manifest_id="manifest-current",
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            manifest_id="manifest-checkpoint",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any("Manifest identity mismatch" in msg for msg in result.messages)

    def test_validate_composite_run_identity_mismatch(self) -> None:
        """Composite run identity mismatch should block resume."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            composite_run_identity="run-current",
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            composite_run_identity="run-checkpoint",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any("Composite run identity mismatch" in msg for msg in result.messages)

    def test_validate_composite_run_identity_missing(self) -> None:
        """Missing composite run identity should block strict resume."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            composite_run_identity="run-current",
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any("Composite run identity missing" in msg for msg in result.messages)

    def test_validate_composite_run_identity_mismatch_overrides_matching_fingerprint(
        self,
    ) -> None:
        """Composite drift should not be misreported as a fingerprint mismatch."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            execution_fingerprint="fp-same",
            composite_run_identity="run-current",
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            execution_fingerprint="fp-same",
            composite_run_identity="run-checkpoint",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any("Composite run identity mismatch" in msg for msg in result.messages)
        assert not any(
            "Execution fingerprint mismatch" in msg for msg in result.messages
        )

    def test_validate_contract_version_mismatch(self) -> None:
        """Contract version mismatch should block resume."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            contract_ref="chembl.activity",
            contract_version="2.0.0",
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            contract_ref="chembl.activity",
            contract_version="1.0.0",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any("Contract version mismatch" in msg for msg in result.messages)

    def test_validate_exact_replay_requires_snapshot_anchors(self) -> None:
        """Exact replay resumes should fail when snapshot anchors are missing."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            exact_replay=True,
            input_snapshot_ids=("snapshot-a",),
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            exact_replay=True,
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any(
            "requires checkpoint input snapshot anchors" in msg
            for msg in result.messages
        )

    def test_validate_input_snapshot_identity_mismatch(self) -> None:
        """Snapshot identity mismatches should block replay-safe resume."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            exact_replay=True,
            input_snapshot_ids=("snapshot-a",),
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
            exact_replay=True,
            input_snapshot_ids=("snapshot-b",),
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert any("Input snapshot identity mismatch" in msg for msg in result.messages)

    def test_strict_resume_blocks_missing_execution_identity_proof(self) -> None:
        """Strict mode should fail closed when identity continuity is unproven."""
        current = CheckpointMetadata(
            records_processed=1000,
            execution_fingerprint="current-fingerprint",
        )
        checkpoint = CheckpointMetadata(records_processed=500)

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert result.identity_continuity_proven is False
        assert any(
            "Execution identity continuity not proven" in msg for msg in result.messages
        )

    def test_strict_resume_blocks_missing_fallback_identity_anchors(self) -> None:
        """Strict mode should not resume when no comparable fallback anchors exist."""
        current = CheckpointMetadata(records_processed=1000)
        checkpoint = CheckpointMetadata(records_processed=500)

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert result.identity_continuity_proven is False
        assert any(
            "Execution identity continuity not proven" in msg for msg in result.messages
        )

    def test_validate_minimum_compatibility_same_contracts(self) -> None:
        """Test lenient mode with same DQ contracts."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.1.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
        )

        result = self.service.validate_minimum_compatibility(current, checkpoint)

        assert result.compatible is True
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True
        assert result.execution_identity_compatible is True
        assert any(
            "Minor pipeline version changed (lenient mode)" in msg
            for msg in result.messages
        )

    def test_validate_minimum_compatibility_different_contracts(self) -> None:
        """Test lenient mode allows resume with different DQ contracts."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="new_hash",
            pipeline_version="1.0.0",
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="old_hash",
            pipeline_version="1.0.0",
        )

        result = self.service.validate_minimum_compatibility(current, checkpoint)

        assert result.compatible is True
        assert (
            result.dq_compatible is True
        )  # Still considered compatible in lenient mode
        assert result.pipeline_compatible is True
        assert result.execution_identity_compatible is True
        assert any(
            "DQ contract changed (lenient mode)" in msg for msg in result.messages
        )

    def test_validate_minimum_compatibility_major_version_change(self) -> None:
        """Test lenient mode blocks major version changes."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="2.0.0",  # Major version 2
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.5.0",  # Major version 1
        )

        result = self.service.validate_minimum_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.dq_compatible is True
        assert result.pipeline_compatible is False
        assert any("Major pipeline version mismatch" in msg for msg in result.messages)

    def test_validate_minimum_compatibility_minor_version_change(self) -> None:
        """Test lenient mode allows minor version changes."""
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.2.0",  # Minor version change
        )

        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.1.0",
        )

        result = self.service.validate_minimum_compatibility(current, checkpoint)

        assert result.compatible is True
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True
        assert result.execution_identity_compatible is True
        assert any(
            "Minor pipeline version changed (lenient mode)" in msg
            for msg in result.messages
        )

    def test_validate_checkpoint_compatibility_emits_metric(self) -> None:
        """Strict and lenient validation should emit aggregate compatibility metrics."""
        metrics = MagicMock()
        service = CheckpointCompatibilityService(
            logger=self.logger,
            metrics=metrics,
            pipeline_name="chembl_activity",
        )
        current = CheckpointMetadata(
            records_processed=1000,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
        )
        checkpoint = CheckpointMetadata(
            records_processed=500,
            dq_contract_compatibility_hash="same_hash",
            pipeline_version="1.0.0",
        )

        service.validate_checkpoint_compatibility(current, checkpoint)
        service.validate_minimum_compatibility(current, checkpoint)

        assert metrics.increment_counter.call_count == 2
        assert metrics.increment_counter.call_args_list[0].args == (
            "bioetl_checkpoint_compatibility_events_total",
            1,
            {
                "pipeline": "chembl_activity",
                "disposition": "strict_compatible",
            },
        )
        assert metrics.increment_counter.call_args_list[1].args == (
            "bioetl_checkpoint_compatibility_events_total",
            1,
            {
                "pipeline": "chembl_activity",
                "disposition": "lenient_compatible",
            },
        )


class TestCheckpointCompatibilityServiceEdgeCases:
    """Test edge cases for checkpoint compatibility service."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.logger = MagicMock()
        self.service = CheckpointCompatibilityService(logger=self.logger)

    def test_empty_metadata(self) -> None:
        """Test with minimal metadata."""
        current = CheckpointMetadata(records_processed=100)
        checkpoint = CheckpointMetadata(records_processed=50)

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.execution_identity_compatible is False
        assert result.identity_continuity_proven is False
        assert any(
            "Execution identity continuity not proven" in msg for msg in result.messages
        )

    def test_malformed_version_strings(self) -> None:
        """Test with malformed version strings."""
        current = CheckpointMetadata(
            records_processed=100,
            pipeline_version="not-a-version",
        )
        checkpoint = CheckpointMetadata(
            records_processed=50,
            pipeline_version="also-not-a-version",
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.dq_compatible is True
        assert result.pipeline_compatible is False
        assert result.execution_identity_compatible is False
        assert result.identity_continuity_proven is True
        assert any("Pipeline version mismatch" in msg for msg in result.messages)

    def test_none_values(self) -> None:
        """Test with None values in metadata."""
        current = CheckpointMetadata(
            records_processed=100,
            dq_contract_compatibility_hash=None,
            pipeline_version=None,
        )
        checkpoint = CheckpointMetadata(
            records_processed=50,
            dq_contract_compatibility_hash=None,
            pipeline_version=None,
        )

        result = self.service.validate_checkpoint_compatibility(current, checkpoint)

        assert result.compatible is False
        assert result.dq_compatible is True
        assert result.pipeline_compatible is True
        assert result.execution_identity_compatible is False
        assert result.identity_continuity_proven is False
