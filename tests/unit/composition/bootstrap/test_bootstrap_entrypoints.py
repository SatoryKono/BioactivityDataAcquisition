"""Unit tests for pipeline bootstrap entrypoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.runner import PipelineRunner
from bioetl.domain.context import PipelineRunContext, VacuumSettings
from bioetl.domain.types import RunType


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.env = "staging"
    settings.strict_error_handling = False
    settings.aws = MagicMock()
    settings.aws.endpoint_url = None
    settings.aws.region = "us-east-1"
    settings.aws.access_key_id = None
    settings.aws.secret_access_key = None
    settings.s3 = MagicMock()
    settings.s3.bucket_bronze = "bronze"
    settings.s3.bucket_silver = "silver"
    settings.s3.bucket_gold = "gold"
    settings.s3.bucket_checkpoints = "checkpoints"
    settings.storage_options = {}
    settings.metrics = None
    # Pipeline settings for RuntimeConfig
    settings.pipeline = MagicMock()
    settings.pipeline.heartbeat_interval = 30
    return settings


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    return logger


@pytest.mark.unit
class TestBootstrapPipeline:
    """Tests for bootstrap_pipeline_runner function."""

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.bootstrap_observability_bundle"
    )
    @patch("bioetl.infrastructure.config.get_settings")
    def test_bootstrap_pipeline_unknown_pipeline_raises(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_observability_bundle: MagicMock,
        mock_settings: MagicMock,
        mock_logger: MagicMock,
    ):
        """Test that unknown pipeline name raises ValueError."""
        from bioetl.composition.bootstrap import bootstrap_pipeline_runner

        # Configure settings with required observability attributes
        mock_settings.metrics_port = 8000
        mock_settings.test_mode = False
        mock_settings.observability = MagicMock()
        mock_settings.observability.metrics_enabled = True
        mock_settings.observability.metrics_server_enabled = True
        mock_settings.observability.metrics_fail_fast = False
        mock_settings.observability.metrics_retry_count = 3
        mock_settings.observability.metrics_retry_delay = 1.0
        mock_settings.observability.tracing_enabled = False
        mock_settings.observability.dq_baseline_window = 7
        mock_settings.observability.dq_z_score_threshold = 2.5
        mock_settings.observability.dq_min_baseline_samples = 3
        mock_settings.observability.dq_error_rate_max = 0.10
        mock_settings.observability.dq_quality_score_min = 0.80

        mock_get_settings.return_value = mock_settings

        # Now raises "Configuration file not found" because load_pipeline_config is called first
        ctx = PipelineRunContext(
            pipeline_name="unknown_pipeline",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=None,
        )
        with pytest.raises(ValueError, match="Configuration file not found"):
            bootstrap_pipeline_runner(ctx)

    @patch("bioetl.composition.bootstrap.runtime.pipeline.create_registry")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.assemble_filter_config")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.load_pipeline_config")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.bootstrap_observability_bundle"
    )
    @patch("bioetl.infrastructure.config.get_settings")
    def test_bootstrap_pipeline_creates_runner_without_starting_server(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_observability_bundle: MagicMock,
        mock_load_config: MagicMock,
        mock_assemble_filter: MagicMock,
        mock_create_registry: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that bootstrap_pipeline_runner creates runner without starting metrics server.

        After refactoring, bootstrap_metrics_port() no longer starts the metrics server.
        Server startup is handled by entrypoints via maybe_start_metrics_server().
        This test verifies that bootstrap_pipeline_runner creates a runner successfully
        regardless of metrics server state.
        """
        from bioetl.composition.bootstrap import bootstrap_pipeline_runner

        # Create proper mock settings with required attributes
        test_settings = MagicMock()
        test_settings.metrics_port = 8000
        test_settings.test_mode = False
        test_settings.pipeline = MagicMock()
        test_settings.pipeline.heartbeat_interval = 30
        test_settings.pipeline.vacuum_retention_days = 7
        # Add observability settings for bootstrap_metrics_port()
        test_settings.observability = MagicMock()
        test_settings.observability.metrics_enabled = True
        test_settings.observability.metrics_server_enabled = True
        test_settings.observability.metrics_fail_fast = False
        test_settings.observability.metrics_retry_count = 3
        test_settings.observability.metrics_retry_delay = 1.0
        test_settings.observability.tracing_enabled = False
        test_settings.observability.dq_monitor_enabled = False

        mock_get_settings.return_value = test_settings

        # Mock observability bundle
        mock_obs = MagicMock()
        mock_obs.logger = mock_logger
        mock_bootstrap_observability_bundle.return_value = mock_obs

        mock_assemble_filter.return_value = None

        # Setup pipeline registry mock
        mock_config = MagicMock()
        mock_config.business_primary_keys = ["activity_id"]
        mock_config.primary_keys = None
        mock_config.technical_primary_key = "entity_id"
        mock_config.maintenance.auto_vacuum = False
        mock_config.maintenance.vacuum_retention_days = 7
        mock_config.input_filter = MagicMock()
        mock_load_config.return_value = mock_config
        mock_factory = MagicMock()
        mock_runner = MagicMock()
        mock_factory.create_runner.return_value = mock_runner
        mock_registry = MagicMock()
        mock_registry.get.return_value.factory = mock_factory
        mock_create_registry.return_value = mock_registry

        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=None,
        )

        # Should return runner - bootstrap no longer starts metrics server
        result = bootstrap_pipeline_runner(ctx)

        assert result is mock_runner
        # Verify observability was bootstrapped (creates MetricsPort, but doesn't start server)
        mock_bootstrap_observability_bundle.assert_called_once()

    @patch("bioetl.infrastructure.config.get_settings")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.create_registry")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.bootstrap_observability_bundle"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ensure_providers_loaded")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.load_pipeline_config")
    def test_bootstrap_pipeline_chembl_activity(
        self,
        mock_load_config,
        mock_register_pipelines,
        mock_ensure_providers_loaded,
        mock_observability_bundle,
        mock_create_registry,
        mock_get_settings,
        mock_settings,
        mock_logger,
    ):
        """Test bootstrap_pipeline_runner creates chembl_activity pipeline."""
        from bioetl.composition.bootstrap import bootstrap_pipeline_runner

        mock_settings.test_mode = False
        mock_get_settings.return_value = mock_settings

        # Mock YAML config with maintenance settings
        mock_yaml_config = MagicMock()
        mock_yaml_config.business_primary_keys = ["activity_id"]
        mock_yaml_config.primary_keys = None
        mock_yaml_config.technical_primary_key = "entity_id"
        mock_yaml_config.maintenance.auto_vacuum = False
        mock_yaml_config.maintenance.vacuum_retention_days = 7
        # Input filter with disabled state (source_path empty means disabled)
        mock_yaml_config.input_filter.enabled = False
        mock_yaml_config.input_filter.source_path = ""
        mock_yaml_config.input_filter.column_name = ""
        mock_yaml_config.input_filter.filter_field = ""
        mock_load_config.return_value = mock_yaml_config

        # Mock observability with logger
        mock_obs = MagicMock()
        mock_obs.logger = mock_logger
        mock_observability_bundle.return_value = mock_obs

        # Mock factory and runner
        mock_runner = MagicMock(spec=PipelineRunner)
        mock_factory = MagicMock()
        mock_factory.create_runner.return_value = mock_runner
        mock_create_registry.return_value.list_pipelines.return_value = []
        mock_create_registry.return_value.get.return_value.factory = mock_factory

        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=100,
        )
        result = bootstrap_pipeline_runner(ctx)

        assert result is mock_runner
        mock_factory.create_runner.assert_called_once()
        mock_ensure_providers_loaded.assert_called_once_with()
        mock_register_pipelines.assert_called_once_with(
            registry=mock_create_registry.return_value
        )


@pytest.mark.unit
class TestBootstrapVacuumConfig:
    """Tests for bootstrap_pipeline_runner vacuum configuration merging."""

    @patch("bioetl.composition.bootstrap.runtime.pipeline.create_registry")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.assemble_filter_config")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.load_pipeline_config")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.bootstrap_observability_bundle"
    )
    @patch("bioetl.infrastructure.config.get_settings")
    def test_bootstrap_uses_yaml_vacuum_config_when_cli_not_set(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_observability_bundle: MagicMock,
        mock_load_config: MagicMock,
        mock_assemble_filter: MagicMock,
        mock_create_registry: MagicMock,
    ) -> None:
        """Test that YAML auto_vacuum config is used when CLI doesn't override."""
        from bioetl.composition.bootstrap import bootstrap_pipeline_runner

        # Create settings with all required observability attributes
        settings = MagicMock()
        settings.metrics_port = 8000
        settings.test_mode = False
        settings.pipeline.heartbeat_interval = 30
        settings.observability.metrics_enabled = False
        settings.observability.metrics_server_enabled = False
        settings.observability.dq_monitor_enabled = False
        mock_get_settings.return_value = settings

        # Create logger
        logger = MagicMock()
        logger.bind.return_value = logger
        mock_obs = MagicMock()
        mock_obs.logger = logger
        mock_bootstrap_observability_bundle.return_value = mock_obs
        mock_assemble_filter.return_value = None

        # Setup YAML config with auto_vacuum enabled
        yaml_config = MagicMock()
        yaml_config.business_primary_keys = ["activity_id"]
        yaml_config.primary_keys = None
        yaml_config.technical_primary_key = "entity_id"
        yaml_config.maintenance.auto_vacuum = True
        yaml_config.maintenance.vacuum_retention_days = 14
        yaml_config.input_filter = MagicMock()
        mock_load_config.return_value = yaml_config

        # Setup pipeline registry
        mock_factory = MagicMock()
        mock_runner = MagicMock()
        mock_factory.create_runner.return_value = mock_runner
        mock_registry = MagicMock()
        mock_registry.get.return_value.factory = mock_factory
        mock_create_registry.return_value = mock_registry

        # Context without CLI vacuum options (disabled VacuumSettings)
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            # vacuum defaults to VacuumSettings(enabled=False)
        )

        bootstrap_pipeline_runner(ctx)

        # Verify runtime config was passed with YAML values
        call_args = mock_factory.create_runner.call_args
        runtime = call_args.kwargs.get("runtime") or call_args[1].get("runtime")
        assert runtime.vacuum_after_run is True
        assert runtime.vacuum_retention_days == 14

    @patch("bioetl.composition.bootstrap.runtime.pipeline.create_registry")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.assemble_filter_config")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.load_pipeline_config")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.bootstrap_observability_bundle"
    )
    @patch("bioetl.infrastructure.config.get_settings")
    def test_bootstrap_cli_vacuum_overrides_yaml_config(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_observability_bundle: MagicMock,
        mock_load_config: MagicMock,
        mock_assemble_filter: MagicMock,
        mock_create_registry: MagicMock,
    ) -> None:
        """Test that CLI vacuum options override YAML config."""
        from bioetl.composition.bootstrap import bootstrap_pipeline_runner

        # Create settings with all required observability attributes
        settings = MagicMock()
        settings.metrics_port = 8000
        settings.test_mode = False
        settings.pipeline.heartbeat_interval = 30
        settings.observability.metrics_enabled = False
        settings.observability.metrics_server_enabled = False
        settings.observability.dq_monitor_enabled = False
        mock_get_settings.return_value = settings

        # Create logger
        logger = MagicMock()
        logger.bind.return_value = logger
        mock_obs = MagicMock()
        mock_obs.logger = logger
        mock_bootstrap_observability_bundle.return_value = mock_obs
        mock_assemble_filter.return_value = None

        # Setup YAML config with auto_vacuum enabled
        yaml_config = MagicMock()
        yaml_config.business_primary_keys = ["activity_id"]
        yaml_config.primary_keys = None
        yaml_config.technical_primary_key = "entity_id"
        yaml_config.maintenance.auto_vacuum = True
        yaml_config.maintenance.vacuum_retention_days = 14
        yaml_config.input_filter = MagicMock()
        mock_load_config.return_value = yaml_config

        # Setup pipeline registry
        mock_factory = MagicMock()
        mock_runner = MagicMock()
        mock_factory.create_runner.return_value = mock_runner
        mock_registry = MagicMock()
        mock_registry.get.return_value.factory = mock_factory
        mock_create_registry.return_value = mock_registry

        # Context with CLI overrides (explicit enabled=True and 30 days)
        # Note: enabled=True means CLI is overriding, so its retention_days is used
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            vacuum=VacuumSettings(enabled=True, retention_days=30),  # CLI override
        )

        bootstrap_pipeline_runner(ctx)

        # Verify runtime config was passed with CLI values (overriding YAML)
        call_args = mock_factory.create_runner.call_args
        runtime = call_args.kwargs.get("runtime") or call_args[1].get("runtime")
        assert runtime.vacuum_after_run is True  # CLI enabled=True
        assert runtime.vacuum_retention_days == 30
