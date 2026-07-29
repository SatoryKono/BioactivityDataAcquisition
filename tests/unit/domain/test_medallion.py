# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for medallion layer policies.

Tests MedallionPolicy, ClearPolicy, and LoadingStrategy domain objects.
"""

from __future__ import annotations

import pytest

from bioetl.domain.medallion import ClearPolicy, LoadingStrategy, MedallionPolicy
from bioetl.domain.types import RunType


@pytest.mark.unit
class TestClearPolicy:
    """Test ClearPolicy enum."""

    def test_medallion_clear_policy__enum_values__5c77c925(self):
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

    def test_medallion_policy__is_frozen__9f83465b(self):
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


@pytest.mark.unit
class TestLoadingStrategy:
    """Test LoadingStrategy enum (ADR-031)."""

    def test_loading_strategy__enum_values__68aeeb25(self):
        """Test LoadingStrategy enum has correct string values."""
        assert LoadingStrategy.FULL_SCAN_ONLY.value == "full_scan_only"

    def test_from_string_valid_values(self):
        """Test from_string converts valid string values."""
        assert (
            LoadingStrategy.from_string("full_scan_only")
            == LoadingStrategy.FULL_SCAN_ONLY
        )

    def test_loading_strategy__case_insensitive__dd820758(self):
        """Test from_string is case insensitive."""
        assert (
            LoadingStrategy.from_string("FULL_SCAN_ONLY")
            == LoadingStrategy.FULL_SCAN_ONLY
        )

    def test_from_string_invalid_raises_value_error(self):
        """Test from_string raises ValueError for invalid values."""
        with pytest.raises(ValueError) as exc_info:
            LoadingStrategy.from_string("invalid_strategy")

        assert "Invalid loading strategy" in str(exc_info.value)
        assert "invalid_strategy" in str(exc_info.value)

    def test_allows_checkpoint_resume_full_scan_only(self):
        """Test FULL_SCAN_ONLY does not allow checkpoint resume."""
        assert LoadingStrategy.FULL_SCAN_ONLY.allows_checkpoint_resume is False

    def test_string_enum_comparison(self):
        """Test LoadingStrategy can be compared with strings."""
        assert LoadingStrategy.FULL_SCAN_ONLY == "full_scan_only"
