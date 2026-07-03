"""Unit tests for domain RuntimeConfig."""

from __future__ import annotations

import pytest

from bioetl.domain.config import RuntimeConfig
from bioetl.domain.types import RunType


@pytest.mark.unit
class TestRuntimeConfig:
    """Tests for RuntimeConfig dataclass."""

    def test_config_runtime_config__default_values__edc0822f(self) -> None:
        """Test default values for optional fields."""
        config = RuntimeConfig(run_type=RunType.INCREMENTAL)

        assert config.run_type == RunType.INCREMENTAL
        assert config.resume is False
        assert config.limit is None
        assert config.heartbeat_interval == 30
        assert config.wait_for_lock is False
        assert config.lock_wait_timeout == 300
        assert config.lock_ttl == 90
        assert config.query is None
        assert config.dry_run is False
        assert config.exact_replay is False
        assert config.replay_anchor_date is None
        assert config.vacuum_after_run is False
        assert config.vacuum_retention_days == 7
        assert config.strict_validation is False
        assert config.strict_gold_validation is True
        assert config.health_check_mode == "strict"
        assert config.silver_filter_compatibility_mode == "structural_only_compat"

    def test_config_runtime_config__custom_values__c572811c(self) -> None:
        """Test custom configuration values."""
        config = RuntimeConfig(
            run_type=RunType.BACKFILL,
            resume=True,
            limit=1000,
            heartbeat_interval=60,
            wait_for_lock=True,
            lock_wait_timeout=600,
            lock_ttl=180,
            query="test_query",
            dry_run=True,
            exact_replay=True,
            replay_anchor_date="2026-04-10",
            vacuum_after_run=True,
            vacuum_retention_days=14,
            strict_validation=True,
            strict_gold_validation=True,
            health_check_mode="probe",
        )

        assert config.run_type == RunType.BACKFILL
        assert config.resume is True
        assert config.limit == 1000
        assert config.heartbeat_interval == 60
        assert config.wait_for_lock is True
        assert config.lock_wait_timeout == 600
        assert config.lock_ttl == 180
        assert config.query == "test_query"
        assert config.dry_run is True
        assert config.exact_replay is True
        assert config.replay_anchor_date == "2026-04-10"
        assert config.vacuum_after_run is True
        assert config.vacuum_retention_days == 14
        assert config.strict_validation is True
        assert config.strict_gold_validation is True
        assert config.health_check_mode == "probe"

    def test_config_runtime_config__immutability__d00ffda1(self) -> None:
        """Test that RuntimeConfig is frozen (immutable)."""
        config = RuntimeConfig(run_type=RunType.INCREMENTAL)

        with pytest.raises(AttributeError):
            config.run_type = RunType.BACKFILL  # type: ignore[misc]

        with pytest.raises(AttributeError):
            config.limit = 100  # type: ignore[misc]

    def test_config_runtime_config__equality__d2f93b6f(self) -> None:
        """Test equality between RuntimeConfig instances."""
        config1 = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=100)
        config2 = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=100)
        config3 = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=200)

        assert config1 == config2
        assert config1 != config3

    def test_config_runtime_config__hashable__ec581be6(self) -> None:
        """Test that RuntimeConfig is hashable."""
        config1 = RuntimeConfig(run_type=RunType.INCREMENTAL)
        config2 = RuntimeConfig(run_type=RunType.INCREMENTAL)

        config_set = {config1, config2}
        assert len(config_set) == 1

    def test_effective_lock_ttl_explicit(self) -> None:
        """Test effective_lock_ttl with explicit lock_ttl."""
        config = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            lock_ttl=100,
            heartbeat_interval=30,
        )
        assert config.effective_lock_ttl == 100

    def test_effective_lock_ttl_derived(self) -> None:
        """Test effective_lock_ttl derived from heartbeat_interval."""
        config = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            lock_ttl=None,
            heartbeat_interval=30,
        )
        # default logic: lock_ttl or heartbeat_interval * 3
        assert config.effective_lock_ttl == 90

    # Validation tests

    def test_zero_limit_raises(self) -> None:
        """Test that zero limit raises ValueError."""
        with pytest.raises(ValueError, match="limit must be positive"):
            RuntimeConfig(run_type=RunType.INCREMENTAL, limit=0)

    def test_negative_limit_raises(self) -> None:
        """Test that negative limit raises ValueError."""
        with pytest.raises(ValueError, match="limit must be positive"):
            RuntimeConfig(run_type=RunType.INCREMENTAL, limit=-5)

    def test_zero_heartbeat_raises(self) -> None:
        """Test that zero heartbeat_interval raises ValueError."""
        with pytest.raises(ValueError, match="heartbeat_interval must be positive"):
            RuntimeConfig(run_type=RunType.INCREMENTAL, heartbeat_interval=0)

    def test_negative_heartbeat_raises(self) -> None:
        """Test that negative heartbeat_interval raises ValueError."""
        with pytest.raises(ValueError, match="heartbeat_interval must be positive"):
            RuntimeConfig(run_type=RunType.INCREMENTAL, heartbeat_interval=-10)

    def test_zero_lock_timeout_raises(self) -> None:
        """Test that zero lock_wait_timeout raises ValueError."""
        with pytest.raises(ValueError, match="lock_wait_timeout must be positive"):
            RuntimeConfig(run_type=RunType.INCREMENTAL, lock_wait_timeout=0)

    def test_negative_lock_timeout_raises(self) -> None:
        """Test that negative lock_wait_timeout raises ValueError."""
        with pytest.raises(ValueError, match="lock_wait_timeout must be positive"):
            RuntimeConfig(run_type=RunType.INCREMENTAL, lock_wait_timeout=-1)

    def test_zero_vacuum_retention_raises(self) -> None:
        """Test that zero vacuum_retention_days raises ValueError."""
        with pytest.raises(ValueError, match="vacuum_retention_days must be positive"):
            RuntimeConfig(run_type=RunType.INCREMENTAL, vacuum_retention_days=0)

    def test_negative_vacuum_retention_raises(self) -> None:
        """Test that negative vacuum_retention_days raises ValueError."""
        with pytest.raises(ValueError, match="vacuum_retention_days must be positive"):
            RuntimeConfig(run_type=RunType.INCREMENTAL, vacuum_retention_days=-7)

    def test_invalid_health_check_mode_raises(self) -> None:
        """Test that invalid health_check_mode raises ValueError."""
        with pytest.raises(ValueError, match="health_check_mode must be"):
            RuntimeConfig(
                run_type=RunType.INCREMENTAL,
                health_check_mode="unsupported",  # type: ignore[arg-type]
            )

    def test_invalid_replay_anchor_date_raises(self) -> None:
        """Replay anchors must use canonical ISO date form."""
        with pytest.raises(ValueError, match="replay_anchor_date must be an ISO date"):
            RuntimeConfig(
                run_type=RunType.INCREMENTAL,
                exact_replay=True,
                replay_anchor_date="2026/04/10",
            )

    def test_historical_silver_filter_mode_is_still_accepted(self) -> None:
        """RuntimeConfig accepts persisted historical Silver filter identity."""
        config = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            silver_filter_compatibility_mode="structural_only_auto_promote",
        )

        assert config.silver_filter_compatibility_mode == "structural_only_auto_promote"

    def test_unsupported_silver_filter_mode_raises(self) -> None:
        """RuntimeConfig only accepts reviewed Silver filter modes."""
        with pytest.raises(
            ValueError,
            match="silver_filter_compatibility_mode must be",
        ):
            RuntimeConfig(
                run_type=RunType.INCREMENTAL,
                silver_filter_compatibility_mode="unsupported_mode",  # type: ignore[arg-type]
            )
