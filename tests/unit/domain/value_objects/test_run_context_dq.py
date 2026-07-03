"""Unit tests for RunContext with DQ integration."""

from __future__ import annotations

from datetime import datetime, UTC

import pytest

from bioetl.domain.types import RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext


pytestmark = pytest.mark.unit


class TestRunContextDQIntegration:
    """Tests for RunContext with DQ integration."""

    def test_run_context_creation_with_dq_fields(self) -> None:
        """Test RunContext creation with new DQ fields."""
        context = RunContext(
            run_id=RunID("test-run-123"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            dq_contract_compatibility_hash="test_dq_hash_abc123",
            effective_config_artifact_id="config_artifact_001",
        )

        # Verify DQ fields are set
        assert context.dq_contract_compatibility_hash == "test_dq_hash_abc123"
        assert context.effective_config_artifact_id == "config_artifact_001"

    def test_run_context_creation_without_dq_fields(self) -> None:
        """Test RunContext creation without DQ fields (backward compatibility)."""
        context = RunContext(
            run_id=RunID("test-run-123"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
        )

        # Verify DQ fields are None by default
        assert context.dq_contract_compatibility_hash is None
        assert context.effective_config_artifact_id is None

    def test_run_context_factory_method_with_dq(self) -> None:
        """Test RunContext factory method with DQ fields."""
        context = RunContext.create(
            run_id=RunID("test-run-123"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            provider="chembl",
            entity="activity",
        )

        # Factory method should set DQ fields to None
        assert context.dq_contract_compatibility_hash is None
        assert context.effective_config_artifact_id is None
        assert context.pipeline_name == "chembl_activity"

    def test_run_context_immutability_with_dq_fields(self) -> None:
        """Test that RunContext remains immutable with DQ fields."""
        context = RunContext(
            run_id=RunID("test-run-123"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            dq_contract_compatibility_hash="test_hash",
        )

        # Should not be able to modify DQ fields
        with pytest.raises(Exception):
            context.dq_contract_compatibility_hash = "modified"  # type: ignore

    def test_run_context_validation_with_dq_fields(self) -> None:
        """Test RunContext validation still works with DQ fields."""
        # Test timezone validation
        with pytest.raises(ValueError, match="started_at must be timezone-aware"):
            RunContext(
                run_id=RunID("test-run-123"),
                run_type=RunType.INCREMENTAL,
                started_at=datetime(2023, 1, 1, 12, 0, 0),  # No timezone
                pipeline_name="chembl_activity",
                provider="chembl",
                entity="activity",
                dq_contract_compatibility_hash="test_hash",
            )

        # Test empty field validation
        with pytest.raises(ValueError, match="pipeline_name cannot be empty"):
            RunContext(
                run_id=RunID("test-run-123"),
                run_type=RunType.INCREMENTAL,
                started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
                pipeline_name="",  # Empty
                provider="chembl",
                entity="activity",
                dq_contract_compatibility_hash="test_hash",
            )

    def test_run_context_equality_with_dq_fields(self) -> None:
        """Test RunContext equality comparison with DQ fields."""
        context1 = RunContext(
            run_id=RunID("test-run-123"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            dq_contract_compatibility_hash="test_hash",
        )

        context2 = RunContext(
            run_id=RunID("test-run-123"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            dq_contract_compatibility_hash="test_hash",
        )

        # Should be equal
        assert context1 == context2

        # Different DQ hash should make them unequal
        context3 = RunContext(
            run_id=RunID("test-run-123"),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
            pipeline_name="chembl_activity",
            provider="chembl",
            entity="activity",
            dq_contract_compatibility_hash="different_hash",
        )

        assert context1 != context3
