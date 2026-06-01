"""Unit tests for PipelineConfig and RuntimeConfig."""

from __future__ import annotations

import pytest

from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.types import RunType


pytestmark = pytest.mark.unit

class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_valid_config_creation(self):
        """Test creating a valid pipeline config."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="test_provider",
            entity_type="test_entity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test_silver",
            ),
        )

        assert config.pipeline_name == "test_pipeline"
        assert config.provider == "test_provider"
        assert config.entity_type == "test_entity"
        assert config.table.primary_keys == ("id",)  # Lists converted to tuples
        assert config.effective_silver_table == "test_silver"
        assert config.effective_gold_table == f"{config.provider}.{config.entity_type}"
        assert config.batch_size == 100  # default
        assert config.checkpoint_interval == 1000  # default

    def test_config_with_all_fields(self):
        """Test creating config with all optional fields."""
        config = PipelineConfig(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            table=TableConfig(
                primary_keys=["activity_id", "assay_id"],
                silver_table="chembl_activity",
                gold_table="chembl_activity_gold",
            ),
            batch_size=500,
            checkpoint_interval=5000,
        )

        assert config.effective_gold_table == "chembl_activity_gold"
        assert config.batch_size == 500
        assert config.checkpoint_interval == 5000

    def test_config_is_frozen(self):
        """Test that config is immutable."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="test",
            ),
        )

        with pytest.raises(AttributeError):
            config.pipeline_name = "changed"  # type: ignore[misc]

    def test_lock_key_property(self):
        """Test lock_key generation."""
        config = PipelineConfig(
            pipeline_name="my_pipeline",
            provider="provider",
            entity_type="entity",
            table=TableConfig(
                primary_keys=["id"],
                silver_table="table",
            ),
        )

        assert config.lock_key == "pipeline:my_pipeline"

    def test_empty_pipeline_name_raises(self):
        """Test that empty pipeline_name raises ValueError."""
        with pytest.raises(ValueError, match="pipeline_name cannot be empty"):
            PipelineConfig(
                pipeline_name="",
                provider="test",
                entity_type="test",
                table=TableConfig(
                    primary_keys=["id"],
                    silver_table="test",
                ),
            )

    def test_empty_provider_raises(self):
        """Test that empty provider raises ValueError."""
        with pytest.raises(ValueError, match="provider cannot be empty"):
            PipelineConfig(
                pipeline_name="test",
                provider="",
                entity_type="test",
                table=TableConfig(
                    primary_keys=["id"],
                    silver_table="test",
                ),
            )

    def test_empty_entity_type_raises(self):
        """Test that empty entity_type raises ValueError."""
        with pytest.raises(ValueError, match="entity_type cannot be empty"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="",
                table=TableConfig(
                    primary_keys=["id"],
                    silver_table="test",
                ),
            )

    def test_empty_primary_keys_raises(self):
        """Test that empty primary_keys raises ValueError."""
        with pytest.raises(ValueError, match="primary_keys cannot be empty"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                table=TableConfig(
                    primary_keys=[],
                    silver_table="test",
                ),
            )

    def test_invalid_batch_size_raises(self):
        """Test that non-positive batch_size raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                table=TableConfig(
                    primary_keys=["id"],
                    silver_table="test",
                ),
                batch_size=0,
            )

        with pytest.raises(ValueError, match="batch_size must be positive"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                table=TableConfig(
                    primary_keys=["id"],
                    silver_table="test",
                ),
                batch_size=-1,
            )

    def test_invalid_checkpoint_interval_raises(self):
        """Test that non-positive checkpoint_interval raises ValueError."""
        with pytest.raises(ValueError, match="checkpoint_interval must be positive"):
            PipelineConfig(
                pipeline_name="test",
                provider="test",
                entity_type="test",
                table=TableConfig(
                    primary_keys=["id"],
                    silver_table="test",
                ),
                checkpoint_interval=0,
            )


class TestRuntimeConfig:
    """Tests for RuntimeConfig dataclass."""

    def test_valid_runtime_config(self):
        """Test creating a valid runtime config."""
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)

        assert runtime.run_type == RunType.INCREMENTAL
        assert runtime.resume is False  # default
        assert runtime.limit is None  # default

    def test_runtime_config_with_all_fields(self):
        """Test creating runtime config with all fields."""
        runtime = RuntimeConfig(
            run_type=RunType.BACKFILL,
            resume=True,
            limit=1000,
        )

        assert runtime.run_type == RunType.BACKFILL
        assert runtime.resume is True
        assert runtime.limit == 1000

    def test_runtime_config_is_frozen(self):
        """Test that runtime config is immutable."""
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)

        with pytest.raises(AttributeError):
            runtime.resume = True  # type: ignore[misc]

    def test_invalid_limit_raises(self):
        """Test that non-positive limit raises ValueError."""
        with pytest.raises(ValueError, match="limit must be positive or None"):
            RuntimeConfig(
                run_type=RunType.INCREMENTAL,
                limit=0,
            )

        with pytest.raises(ValueError, match="limit must be positive or None"):
            RuntimeConfig(
                run_type=RunType.INCREMENTAL,
                limit=-1,
            )

    def test_all_run_types(self):
        """Test that all RunType values work."""
        for run_type in RunType:
            runtime = RuntimeConfig(run_type=run_type)
            assert runtime.run_type == run_type

    def test_strict_gold_validation_default_true(self):
        """Test that strict_gold_validation defaults to True."""
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
        assert runtime.strict_gold_validation is True

    def test_strict_gold_validation_true(self):
        """Test setting strict_gold_validation to True."""
        runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            strict_gold_validation=True,
        )
        assert runtime.strict_gold_validation is True

    def test_lock_defaults(self):
        """Test that lock parameters have correct defaults (30s/90s).

        REQ-LOCK-001: heartbeat_interval=30s, lock_ttl=90s per ADR-010
        Local-Only Deployment architecture.
        """
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)

        assert runtime.heartbeat_interval == 30
        assert runtime.lock_ttl == 90

    def test_effective_lock_ttl_with_explicit_value(self):
        """Test effective_lock_ttl returns explicit lock_ttl when set."""
        runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            lock_ttl=120,
        )

        assert runtime.effective_lock_ttl == 120

    def test_effective_lock_ttl_with_none(self):
        """Test effective_lock_ttl calculates from heartbeat when lock_ttl is None."""
        runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            heartbeat_interval=15,
            lock_ttl=None,
        )

        # Should be heartbeat_interval * 3
        assert runtime.effective_lock_ttl == 45

    def test_effective_lock_ttl_default(self):
        """Test effective_lock_ttl with default values returns 90s."""
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)

        assert runtime.effective_lock_ttl == 90

    def test_lock_ttl_ratio(self):
        """Test that default TTL is 3x heartbeat interval.

        This ratio ensures at least 2 heartbeats before TTL expiration,
        providing safety margin for heartbeat failures.
        """
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)

        assert runtime.lock_ttl / runtime.heartbeat_interval == 3

    def test_invalid_heartbeat_interval_raises(self):
        """Test that non-positive heartbeat_interval raises ValueError."""
        with pytest.raises(ValueError, match="heartbeat_interval must be positive"):
            RuntimeConfig(
                run_type=RunType.INCREMENTAL,
                heartbeat_interval=0,
            )

        with pytest.raises(ValueError, match="heartbeat_interval must be positive"):
            RuntimeConfig(
                run_type=RunType.INCREMENTAL,
                heartbeat_interval=-1,
            )
