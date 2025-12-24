"""Unit tests for medallion layer policies.

Tests MedallionPolicy and ClearPolicy domain objects.
"""

from __future__ import annotations

import pytest

from bioetl.domain.medallion import ClearPolicy, MedallionPolicy
from bioetl.domain.types import RunType


@pytest.mark.unit
class TestClearPolicy:
    """Test ClearPolicy enum."""

    def test_enum_values(self):
        """Test ClearPolicy enum has correct string values."""
        assert ClearPolicy.NEVER.value == "never"
        assert ClearPolicy.SILVER_ONLY.value == "silver"
        assert ClearPolicy.SILVER_AND_GOLD.value == "both"


@pytest.mark.unit
class TestMedallionPolicy:
    """Test MedallionPolicy dataclass."""

    def test_default_values(self):
        """Test MedallionPolicy has correct defaults."""
        policy = MedallionPolicy()

        assert policy.clear_policy == ClearPolicy.NEVER
        assert policy.vacuum_enabled is False
        assert policy.vacuum_retention_days == 7

    def test_is_frozen(self):
        """Test MedallionPolicy is immutable."""
        policy = MedallionPolicy()

        with pytest.raises(AttributeError):
            policy.clear_policy = ClearPolicy.SILVER_AND_GOLD  # type: ignore[misc]

    def test_custom_values(self):
        """Test MedallionPolicy with custom values."""
        policy = MedallionPolicy(
            clear_policy=ClearPolicy.SILVER_AND_GOLD,
            vacuum_enabled=True,
            vacuum_retention_days=14,
        )

        assert policy.clear_policy == ClearPolicy.SILVER_AND_GOLD
        assert policy.vacuum_enabled is True
        assert policy.vacuum_retention_days == 14


@pytest.mark.unit
class TestMedallionPolicyForRunType:
    """Test MedallionPolicy.for_run_type factory method."""

    def test_rebuild_returns_clear_both(self):
        """Test REBUILD run type creates policy to clear both layers."""
        policy = MedallionPolicy.for_run_type(RunType.REBUILD)

        assert policy.clear_policy == ClearPolicy.SILVER_AND_GOLD
        assert policy.should_clear_silver is True
        assert policy.should_clear_gold is True

    def test_backfill_returns_clear_both(self):
        """Test BACKFILL run type creates policy to clear both layers."""
        policy = MedallionPolicy.for_run_type(RunType.BACKFILL)

        assert policy.clear_policy == ClearPolicy.SILVER_AND_GOLD
        assert policy.should_clear_silver is True
        assert policy.should_clear_gold is True

    def test_incremental_returns_never_clear(self):
        """Test INCREMENTAL run type creates policy to never clear."""
        policy = MedallionPolicy.for_run_type(RunType.INCREMENTAL)

        assert policy.clear_policy == ClearPolicy.NEVER
        assert policy.should_clear_silver is False
        assert policy.should_clear_gold is False


@pytest.mark.unit
class TestMedallionPolicyShouldClear:
    """Test MedallionPolicy.should_clear_* properties."""

    def test_never_policy_clears_nothing(self):
        """Test NEVER policy doesn't clear anything."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.NEVER)

        assert policy.should_clear_silver is False
        assert policy.should_clear_gold is False

    def test_silver_only_policy_clears_silver(self):
        """Test SILVER_ONLY policy clears only Silver."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_ONLY)

        assert policy.should_clear_silver is True
        assert policy.should_clear_gold is False

    def test_silver_and_gold_policy_clears_both(self):
        """Test SILVER_AND_GOLD policy clears both layers."""
        policy = MedallionPolicy(clear_policy=ClearPolicy.SILVER_AND_GOLD)

        assert policy.should_clear_silver is True
        assert policy.should_clear_gold is True
