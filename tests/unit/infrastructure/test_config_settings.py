"""Unit tests for infrastructure config settings classes."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from bioetl.domain.config import DQConfig as DomainDQConfig
from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config._settings_validation import (
    coerce_silver_dedup_timeout_seconds,
)
from bioetl.infrastructure.config._base import (
    ObservabilitySettings,
    PipelineSettings,
    Settings,
    get_settings,
    yaml_config_to_domain,
)


@pytest.mark.unit
class TestPipelineSettings:
    """Tests for PipelineSettings class."""

    def test_pipeline_settings__default_values__26ec6108(self) -> None:
        """Test default pipeline settings."""
        settings = PipelineSettings()

        assert settings.batch_size == 100
        assert settings.checkpoint_interval == 1000
        assert settings.max_concurrent_batches == 4
        assert settings.heartbeat_interval == 30
        assert settings.silver_resilience_enabled is True
        assert settings.silver_metadata_atomic_retry.max_retries == 20
        assert settings.silver_merge_retry.max_retries == 3
        assert settings.silver_merge_timeout.profile == "default"
        assert settings.silver_merge_timeout.execution_timeout_seconds == pytest.approx(
            45.0
        )
        assert (
            settings.silver_merge_timeout.unit_execution_timeout_seconds
            == pytest.approx(15.0)
        )
        assert (
            settings.silver_merge_timeout.e2e_execution_timeout_seconds
            == pytest.approx(90.0)
        )
        assert settings.silver_merge_timeout.plain_write_process_isolation is False
        assert settings.control_plane.run_manifest_enabled is True
        assert settings.control_plane.run_ledger_enabled is True
        assert settings.control_plane.checkpoint_compatibility_policy == "hard_fail"
        assert settings.control_plane.required_persistence_profile == "replay_ready"

    def test_pipeline_settings__custom_values__695415ca(self) -> None:
        """Test custom pipeline settings."""
        settings = PipelineSettings(
            batch_size=500,
            checkpoint_interval=5000,
            max_concurrent_batches=8,
            heartbeat_interval=30,
            silver_resilience_enabled=False,
            silver_metadata_atomic_retry={"max_retries": 2, "adaptive_backoff": False},
            silver_merge_retry={"max_retries": 1, "jitter_seconds": 0.0},
            silver_merge_timeout={
                "profile": "e2e",
                "execution_timeout_seconds": 60.0,
                "e2e_execution_timeout_seconds": 120.0,
                "plain_write_process_isolation": True,
                "max_retries": 0,
            },
            control_plane={
                "run_manifest_enabled": True,
                "run_ledger_enabled": False,
                "checkpoint_compatibility_policy": "hard_fail",
                "required_persistence_profile": "replay_ready",
            },
        )

        assert settings.batch_size == 500
        assert settings.checkpoint_interval == 5000
        assert settings.max_concurrent_batches == 8
        assert settings.heartbeat_interval == 30
        assert settings.silver_resilience_enabled is False
        assert settings.silver_metadata_atomic_retry.max_retries == 2
        assert settings.silver_metadata_atomic_retry.adaptive_backoff is False
        assert settings.silver_merge_retry.max_retries == 1
        assert settings.silver_merge_timeout.profile == "e2e"
        assert settings.silver_merge_timeout.execution_timeout_seconds == pytest.approx(
            60.0
        )
        assert (
            settings.silver_merge_timeout.e2e_execution_timeout_seconds
            == pytest.approx(120.0)
        )
        assert settings.silver_merge_timeout.plain_write_process_isolation is True
        assert settings.silver_merge_timeout.max_retries == 0
        assert settings.control_plane.run_manifest_enabled is True
        assert settings.control_plane.run_ledger_enabled is False
        assert settings.control_plane.checkpoint_compatibility_policy == "hard_fail"
        assert settings.control_plane.required_persistence_profile == "replay_ready"

    def test_control_plane_validation_requires_manifest_for_ledger(self) -> None:
        """Ledger cannot be enabled when manifest creation is disabled."""
        with pytest.raises(ValidationError):
            PipelineSettings(
                control_plane={
                    "run_manifest_enabled": False,
                    "run_ledger_enabled": True,
                }
            )

    def test_control_plane_checkpoint_policy_validation(self) -> None:
        """Checkpoint compatibility policy must be a supported literal."""
        settings = PipelineSettings(
            control_plane={
                "checkpoint_compatibility_policy": "observe",
                "required_persistence_profile": "degraded_observable",
            }
        )
        assert settings.control_plane.checkpoint_compatibility_policy == "observe"

        with pytest.raises(ValidationError):
            PipelineSettings(
                control_plane={
                    "run_manifest_enabled": True,
                    "run_ledger_enabled": True,
                    "checkpoint_compatibility_policy": "unsupported",
                }
            )

    def test_control_plane_required_replay_ready_requires_manifest(self) -> None:
        """Replay-ready profile cannot run without manifests."""
        with pytest.raises(ValidationError):
            PipelineSettings(
                control_plane={
                    "run_manifest_enabled": False,
                    "run_ledger_enabled": False,
                    "required_persistence_profile": "replay_ready",
                }
            )

    def test_control_plane_required_forensic_grade_requires_ledger(self) -> None:
        """Forensic-grade profile requires both manifest and ledger surfaces."""
        with pytest.raises(ValidationError):
            PipelineSettings(
                control_plane={
                    "run_manifest_enabled": True,
                    "run_ledger_enabled": False,
                    "required_persistence_profile": "forensic_grade",
                }
            )

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (None, 60.0),
            ("", 60.0),
            (False, 60.0),
            (0, 60.0),
            (-1.0, 60.0),
            ("2.5", 2.5),
            (object(), 60.0),
        ],
    )
    def test_silver_dedup_timeout_coercion_bounds_unsafe_values(
        self, value: object, expected: float
    ) -> None:
        assert coerce_silver_dedup_timeout_seconds(value) == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("required_profile", "policy"),
        [
            ("replay_ready", "soft_fail"),
            ("forensic_grade", "soft_fail"),
            ("replay_ready", "observe"),
            ("forensic_grade", "observe"),
        ],
    )
    def test_control_plane_strict_profiles_require_hard_fail_checkpoint_policy(
        self,
        required_profile: str,
        policy: str,
    ) -> None:
        """Strict persistence profiles reject non-hard-fail checkpoint policies."""
        with pytest.raises(ValidationError):
            PipelineSettings(
                control_plane={
                    "run_manifest_enabled": True,
                    "run_ledger_enabled": required_profile == "forensic_grade",
                    "required_persistence_profile": required_profile,
                    "checkpoint_compatibility_policy": policy,
                }
            )

    def test_batch_size_validation(self) -> None:
        """Test batch_size validation."""
        # Valid
        settings = PipelineSettings(batch_size=1)
        assert settings.batch_size == 1

        settings = PipelineSettings(batch_size=10000)
        assert settings.batch_size == 10000

        # Invalid
        with pytest.raises(ValidationError):
            PipelineSettings(batch_size=0)

        with pytest.raises(ValidationError):
            PipelineSettings(batch_size=10001)

    def test_heartbeat_interval_validation(self) -> None:
        """Test heartbeat_interval validation."""
        # Valid boundaries
        settings = PipelineSettings(heartbeat_interval=5)
        assert settings.heartbeat_interval == 5

        settings = PipelineSettings(heartbeat_interval=60)
        assert settings.heartbeat_interval == 60

        # Invalid
        with pytest.raises(ValidationError):
            PipelineSettings(heartbeat_interval=4)

        with pytest.raises(ValidationError):
            PipelineSettings(heartbeat_interval=61)


@pytest.mark.unit
class TestObservabilitySettings:
    """Tests for observability settings defaults."""

    def test_dq_monitor_enabled_by_default(self) -> None:
        """DQ anomaly monitoring is enabled unless explicitly disabled."""
        settings = ObservabilitySettings()

        assert settings.dq_monitor_enabled is True


@pytest.mark.unit
class TestSettings:
    """Tests for main Settings class."""

    def test_settings_settings__default_values__171af853(self, monkeypatch) -> None:
        """Test default main settings."""
        # Clear BIOETL_ENV to test explicit values
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        # Use test_mode to bypass dev validation, explicitly set env
        settings = Settings(test_mode=True, env="dev")

        assert settings.env == "dev"
        assert settings.debug is False
        assert settings.test_mode is True
        assert settings.strict_error_handling is False

    def test_nested_settings(self) -> None:
        """Test nested settings objects."""
        settings = Settings(test_mode=True, _env_file=None)

        assert isinstance(settings.pipeline, PipelineSettings)

    def test_data_dir_default(self, monkeypatch) -> None:
        """Test data_dir default value."""
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        settings = Settings(test_mode=True, _env_file=None)
        assert settings.data_dir == Path("data")

    def test_data_dir_custom(self, monkeypatch) -> None:
        """Test custom data_dir."""
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        settings = Settings(
            test_mode=True, data_dir=Path("/custom/data"), _env_file=None
        )
        assert settings.data_dir == Path("/custom/data")

    def test_path_properties(self, monkeypatch) -> None:
        """Test bronze_path, silver_path, gold_path, checkpoint_path properties.

        Unified path structure: {data_dir}/output/{layer}/
        """
        monkeypatch.delenv("BIOETL_ENV", raising=False)
        settings = Settings(test_mode=True, data_dir=Path("/data"), _env_file=None)

        assert settings.bronze_path == Path("/data/output/bronze")
        assert settings.silver_path == Path("/data/output/silver")
        assert settings.gold_path == Path("/data/output/gold")
        assert settings.checkpoint_path == Path("/data/output/checkpoints")

    def test_staging_env(self, monkeypatch) -> None:
        """Test that staging env works."""
        monkeypatch.setenv("BIOETL_ENV", "staging")
        get_settings.cache_clear()
        settings = Settings()
        assert settings.env == "staging"

    def test_prod_env(self, monkeypatch) -> None:
        """Test that prod env works."""
        monkeypatch.setenv("BIOETL_ENV", "prod")
        get_settings.cache_clear()
        settings = Settings()
        assert settings.env == "prod"


@pytest.mark.unit
class TestYamlConfigToDomain:
    """Tests for yaml_config_to_domain function."""

    def test_basic_mapping(self) -> None:
        """Test basic config mapping with real Pydantic models."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQYamlConfig,
            GoldFiltersConfig,
            PipelineYamlConfig,
            SourceConfig,
        )

        yaml_config = PipelineYamlConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="entity",
            business_primary_keys=["id"],
            silver_table="silver_table",
            gold_table="gold_table",
            gold_filters=GoldFiltersConfig(),
            batch_size=200,
            checkpoint_interval=2000,
            source=SourceConfig(),
            dq_overrides=DQYamlConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
            sink={},
        )

        result = yaml_config_to_domain(yaml_config)

        assert isinstance(result, PipelineConfig)
        assert result.pipeline_name == "test_pipeline"
        assert result.provider == "test"
        assert result.entity_type == "entity"
        assert result.table.primary_keys == ("id",)  # Lists converted to tuples
        assert result.table.silver_table == "silver_table"
        assert result.table.gold_table == "gold_table"
        assert result.batch_size == 200
        assert result.checkpoint_interval == 2000

    def test_fields_extraction(self) -> None:
        """Test field names extraction from source config."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQYamlConfig,
            GoldFiltersConfig,
            PipelineYamlConfig,
            SourceConfig,
        )

        yaml_config = PipelineYamlConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            business_primary_keys=["id"],
            silver_table="silver",
            gold_table=None,
            gold_filters=GoldFiltersConfig(),
            batch_size=100,
            checkpoint_interval=1000,
            source=SourceConfig(
                fields=[
                    {"name": "field1", "type": "string"},
                    {"name": "field2", "type": "int"},
                    {"name": "field3", "type": "float"},
                ]
            ),
            dq_overrides=DQYamlConfig(
                soft_fail_threshold=0.05,
                hard_fail_threshold=0.20,
            ),
            sink={},
        )

        result = yaml_config_to_domain(yaml_config)

        assert result.fields == ("field1", "field2", "field3")

    def test_dq_config_mapping(self) -> None:
        """Test DQ config mapping with real Pydantic models."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQYamlConfig,
            GoldFiltersConfig,
            PipelineYamlConfig,
            SourceConfig,
        )

        yaml_config = PipelineYamlConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            business_primary_keys=["id"],
            silver_table="silver",
            gold_table=None,
            gold_filters=GoldFiltersConfig(),
            batch_size=100,
            checkpoint_interval=1000,
            source=SourceConfig(),
            dq_overrides=DQYamlConfig(
                soft_fail_threshold=0.10,
                hard_fail_threshold=0.30,
            ),
            sink={},
        )

        result = yaml_config_to_domain(yaml_config)

        assert isinstance(result.dq, DomainDQConfig)
        assert result.dq.soft_fail_threshold == pytest.approx(0.10)
        assert result.dq.hard_fail_threshold == pytest.approx(0.30)

    def test_pipeline_yaml_config_converter_function(self) -> None:
        """Test converter function maps PipelineYamlConfig consistently."""
        from bioetl.infrastructure.schemas.pipeline_config import (
            DQYamlConfig,
            GoldFiltersConfig,
            PipelineYamlConfig,
            SourceConfig,
        )

        yaml_config = PipelineYamlConfig(
            pipeline_name="test",
            provider="test",
            entity_type="test",
            business_primary_keys=["id"],
            silver_table="silver",
            gold_table=None,
            gold_filters=GoldFiltersConfig(),
            batch_size=100,
            checkpoint_interval=1000,
            source=SourceConfig(),
            dq_overrides=DQYamlConfig(),
            sink={},
        )

        result = yaml_config_to_domain(yaml_config)

        assert isinstance(result, PipelineConfig)
        assert result.pipeline_name == "test"
        assert result.provider == "test"
        assert result.dq.soft_fail_threshold == pytest.approx(0.05)

    def test_gold_filters_config_to_domain_method(self) -> None:
        """Test GoldFiltersConfig.to_domain() method."""
        from bioetl.domain.filtering import GoldFilterConfig
        from bioetl.infrastructure.schemas.pipeline_config import (
            GoldFiltersConfig,
            GoldListContainsFilterConfig,
            GoldListLengthFilterConfig,
            GoldRangeFilterConfig,
        )

        gold_filters = GoldFiltersConfig(
            columns={"status": ["active", "approved"]},
            ranges={"score": GoldRangeFilterConfig(min=0.5, max=1.0)},
            list_lengths={"targets": GoldListLengthFilterConfig(min=1, max=10)},
            list_contains={"tags": GoldListContainsFilterConfig(values=["important"])},
            required_fields=["name", "id"],
            exclude_if_present=["deprecated"],
        )

        result = gold_filters.to_domain()

        assert isinstance(result, GoldFilterConfig)
        assert len(result.column_filters) == 1
        assert len(result.range_filters) == 1
        assert len(result.list_length_filters) == 1
        assert len(result.list_contains_filters) == 1
        assert result.required_fields == ("name", "id")
        assert result.exclude_if_present == ("deprecated",)


@pytest.mark.unit
class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_cached(self) -> None:
        """Test that get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        with patch.dict(os.environ, {"BIOETL_ENV": "staging"}):
            settings1 = get_settings()
            settings2 = get_settings()

            assert settings1 is settings2

        # Clean up
        get_settings.cache_clear()
