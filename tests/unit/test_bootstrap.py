"""Unit tests for bootstrap module."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.runner import PipelineRunner
from bioetl.domain.context import PipelineRunContext, VacuumConfig
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


@pytest.fixture
def mock_services():
    """Create mock PipelineService."""
    services = MagicMock()
    services.data_source = MagicMock()
    services.storage = MagicMock()
    services.lock = MagicMock()
    services.checkpoint = MagicMock()
    services.quarantine = MagicMock()
    services.metrics = MagicMock()
    return services


@pytest.fixture
def mock_pipeline_config():
    """Create mock pipeline config."""
    config = MagicMock()
    config.source = {"api": {"rate_limit": 10.0}}
    # Mock DQ overrides with valid defaults to satisfy Pydantic literal checks
    config.dq_overrides.soft_fail_threshold = 0.05
    config.dq_overrides.hard_fail_threshold = 0.20
    config.dq_overrides.invalid_record_policy = "quarantine"
    config.dq_overrides.report.format = "json"
    config.dq_overrides.report.output_path = "reports/dq"
    config.dq_overrides.report.enabled = True
    config.dq_overrides.field_validations = []
    config.dq_overrides.cross_field_validations = []
    config.dq_overrides.conditional_validations = []
    return config


@pytest.mark.unit
class TestBootstrapLogger:
    """Tests for bootstrap_logger_port function."""

    def test_bootstrap_logger_port_creates_logger(self):
        """Test that bootstrap_logger_port creates a logger."""
        from bioetl.composition.bootstrap import bootstrap_logger_port

        run_id = uuid4()
        logger = bootstrap_logger_port(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="INFO",
        )

        assert logger is not None


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

    @patch("bioetl.composition.bootstrap.runtime.pipeline.get_default_registry")
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
        mock_get_registry: MagicMock,
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
        mock_get_registry.return_value = mock_registry

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
    @patch("bioetl.composition.bootstrap.runtime.pipeline.get_default_registry")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.bootstrap_observability_bundle"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_providers")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.load_pipeline_config")
    def test_bootstrap_pipeline_chembl_activity(
        self,
        mock_load_config,
        mock_register_pipelines,
        mock_register_providers,
        mock_observability_bundle,
        mock_get_registry,
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
        mock_get_registry.return_value.get.return_value.factory = mock_factory

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


@pytest.mark.unit
class TestChemblActivityFactory:
    """Tests for chembl_activity_factory (GenericPipelineFactory instance)."""

    @pytest.fixture(autouse=True)
    def _restore_factory_state(self):
        """Restore factory state after each test to prevent pollution."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )

        # Save original _create_data_source
        original_creator = chembl_activity_factory._create_data_source
        yield
        # Restore after test
        chembl_activity_factory._create_data_source = original_creator

    @patch("bioetl.composition.factories.pipeline_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.pipeline_factory.load_pipeline_config")
    def test_build_services_creates_data_source(
        self,
        mock_load_config,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_services,
        mock_pipeline_config,
    ):
        """Test build_services creates data source through DataSourceRegistry."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services

        # Mock the data source creator function stored in the factory
        mock_data_source = MagicMock()
        chembl_activity_factory._create_data_source = MagicMock(
            return_value=mock_data_source
        )

        services = chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        chembl_activity_factory._create_data_source.assert_called_once()

    @patch("bioetl.composition.factories.pipeline_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.pipeline_factory.load_pipeline_config")
    def test_build_services_calls_base_services_factory(
        self,
        mock_load_config,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_services,
        mock_pipeline_config,
    ):
        """Test build_services uses BaseServicesFactory."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services

        # Mock the data source creator
        mock_data_source = MagicMock()
        chembl_activity_factory._create_data_source = MagicMock(
            return_value=mock_data_source
        )

        chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_base_services.create_common_services.assert_called_once()

    @patch("bioetl.composition.factories.pipeline_factory.BaseServicesFactory")
    @patch("bioetl.composition.factories.pipeline_factory.load_pipeline_config")
    def test_build_services_uses_provided_config(
        self,
        mock_load_config,
        mock_base_services,
        mock_settings,
        mock_logger,
        mock_services,
        mock_pipeline_config,
    ):
        """Test build_services uses provided config."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )

        mock_base_services.create_common_services.return_value = mock_services

        # Mock the data source creator
        mock_data_source = MagicMock()
        chembl_activity_factory._create_data_source = MagicMock(
            return_value=mock_data_source
        )

        chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
            config=mock_pipeline_config,
        )

        # Should NOT call load_pipeline_config when config is provided
        mock_load_config.assert_not_called()

    @patch("bioetl.composition.factories.pipeline_factory.compute_config_hash")
    @patch("bioetl.composition.factories.pipeline_factory.yaml_config_to_domain")
    @patch("bioetl.composition.factories.pipeline_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.pipeline_factory.BaseServicesFactory")
    def test_create_with_services(
        self,
        mock_base_services,
        mock_load_config,
        mock_yaml_to_domain,
        mock_compute_hash,
        mock_settings,
        mock_logger,
        mock_services,
        mock_pipeline_config,
    ):
        """Test create_with_services creates pipeline with run_id."""
        from bioetl.composition.factories.pipeline_factories import (
            chembl_activity_factory,
        )
        from bioetl.domain.config import RuntimeConfig

        mock_load_config.return_value = mock_pipeline_config
        mock_base_services.create_common_services.return_value = mock_services
        mock_domain_config = MagicMock()
        mock_yaml_to_domain.return_value = mock_domain_config
        mock_compute_hash.return_value = "mock_config_hash_12345"

        # Mock the data source creator
        mock_data_source = MagicMock()
        chembl_activity_factory._create_data_source = MagicMock(
            return_value=mock_data_source
        )

        # Create a mock pipeline class
        mock_pipeline_class = MagicMock()
        mock_pipeline = MagicMock()
        mock_pipeline_class.create.return_value = mock_pipeline

        # Temporarily replace pipeline_class
        original_class = chembl_activity_factory.pipeline_class
        chembl_activity_factory.pipeline_class = mock_pipeline_class

        try:
            runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
            run_id = uuid4()
            result = chembl_activity_factory.create_with_services(
                run_id=run_id,
                runtime=runtime,
                settings=mock_settings,
                logger=mock_logger,
            )

            # Verify run_id is passed to pipeline.create()
            # Note: transformer is created by factory via DI and passed to pipeline
            mock_pipeline_class.create.assert_called_once_with(
                run_id=run_id,
                runtime=runtime,
                services=mock_services,
                config=mock_domain_config,
                transformer=ANY,  # Transformer instance created by factory
            )
            assert result is mock_pipeline
        finally:
            # Restore original class
            chembl_activity_factory.pipeline_class = original_class


@pytest.mark.unit
class TestBootstrapMetrics:
    """Tests for bootstrap_metrics_port function with metrics configuration.

    Note: After refactoring, bootstrap_metrics_port() only creates the MetricsPort
    without starting the server. Server startup is now handled by
    maybe_start_metrics_server() which is called by entrypoints.
    """

    @patch("bioetl.composition.bootstrap.runtime.observability.PrometheusMetrics")
    def test_bootstrap_metrics_returns_prometheus_when_enabled(
        self,
        mock_prometheus: MagicMock,
    ) -> None:
        """Test that bootstrap_metrics_port returns PrometheusMetrics when enabled."""
        from bioetl.composition.bootstrap import bootstrap_metrics_port

        # Create mock settings with metrics config
        settings = MagicMock()
        settings.observability.metrics_enabled = True

        mock_metrics = MagicMock()
        mock_prometheus.return_value = mock_metrics

        result = bootstrap_metrics_port(settings)

        assert result is mock_metrics
        mock_prometheus.assert_called_once()

    def test_bootstrap_metrics_disabled_returns_noop_metrics(self) -> None:
        """Test that disabled metrics returns NoOpMetrics (not None).

        Per Unified Observability Contract, bootstrap_metrics_port() always
        returns a valid MetricsPort implementation. When metrics are
        disabled, NoOpMetrics is used as a silent fallback.
        """
        from bioetl.composition.bootstrap import bootstrap_metrics_port
        from bioetl.domain.ports import NoOpMetrics

        settings = MagicMock()
        settings.observability.metrics_enabled = False

        result = bootstrap_metrics_port(settings)

        assert result is not None
        assert isinstance(result, NoOpMetrics)


@pytest.mark.unit
class TestMaybeStartMetricsServer:
    """Tests for maybe_start_metrics_server function.

    This function handles metrics server startup as a side-effect
    that was removed from bootstrap_metrics_port() to keep bootstrap pure.
    """

    @patch("bioetl.composition.bootstrap.runtime.observability.start_metrics_server")
    def test_maybe_start_metrics_server_passes_config_params(
        self,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that maybe_start_metrics_server passes config params correctly."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server

        # Create mock settings with metrics config
        settings = MagicMock()
        settings.metrics_port = 9090
        settings.metrics_addr = "0.0.0.0"
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 5
        settings.observability.metrics_retry_delay = 2.0

        mock_start_server.return_value = True

        result = maybe_start_metrics_server(settings)

        assert result is True
        mock_start_server.assert_called_once_with(
            port=9090,
            addr="0.0.0.0",
            fail_fast=False,
            retry_count=5,
            retry_delay=2.0,
        )

    @patch("bioetl.composition.bootstrap.runtime.observability.start_metrics_server")
    def test_maybe_start_metrics_server_fail_fast_true_raises_error(
        self,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that fail_fast=True propagates MetricsServerError."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server
        from bioetl.interfaces.observability import MetricsServerError

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = True
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0

        # Simulate server failure in fail_fast mode
        mock_start_server.side_effect = MetricsServerError(
            port=8000, reason="port_in_use"
        )

        with pytest.raises(MetricsServerError) as exc_info:
            maybe_start_metrics_server(settings)

        assert exc_info.value.port == 8000
        assert exc_info.value.reason == "port_in_use"

    @patch("bioetl.composition.bootstrap.runtime.observability.start_metrics_server")
    def test_maybe_start_metrics_server_fail_fast_false_propagates_error(
        self,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that fail_fast=False still propagates exceptions to entrypoints."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0

        # Simulate exception - should propagate to entrypoints for handling
        mock_start_server.side_effect = Exception("Random failure")

        # Exceptions now propagate instead of being suppressed
        with pytest.raises(Exception, match="Random failure"):
            maybe_start_metrics_server(settings)

    def test_maybe_start_metrics_server_disabled_returns_false(self) -> None:
        """Test that disabled metrics returns False without calling server."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server

        settings = MagicMock()
        settings.observability.metrics_enabled = False

        result = maybe_start_metrics_server(settings)

        assert result is False

    def test_maybe_start_metrics_server_server_disabled_returns_false(self) -> None:
        """Test that disabled metrics server returns False."""
        from bioetl.composition.bootstrap import maybe_start_metrics_server

        settings = MagicMock()
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = False

        result = maybe_start_metrics_server(settings)

        assert result is False


@pytest.mark.unit
class TestBootstrapVacuumConfig:
    """Tests for bootstrap_pipeline_runner vacuum configuration merging."""

    @patch("bioetl.composition.bootstrap.runtime.pipeline.get_default_registry")
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
        mock_get_registry: MagicMock,
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
        mock_get_registry.return_value = mock_registry

        # Context without CLI vacuum options (disabled VacuumConfig)
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            # vacuum defaults to VacuumConfig(enabled=False)
        )

        bootstrap_pipeline_runner(ctx)

        # Verify runtime config was passed with YAML values
        call_args = mock_factory.create_runner.call_args
        runtime = call_args.kwargs.get("runtime") or call_args[1].get("runtime")
        assert runtime.vacuum_after_run is True
        assert runtime.vacuum_retention_days == 14

    @patch("bioetl.composition.bootstrap.runtime.pipeline.get_default_registry")
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
        mock_get_registry: MagicMock,
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
        mock_get_registry.return_value = mock_registry

        # Context with CLI overrides (explicit enabled=True and 30 days)
        # Note: enabled=True means CLI is overriding, so its retention_days is used
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            vacuum=VacuumConfig(enabled=True, retention_days=30),  # CLI override
        )

        bootstrap_pipeline_runner(ctx)

        # Verify runtime config was passed with CLI values (overriding YAML)
        call_args = mock_factory.create_runner.call_args
        runtime = call_args.kwargs.get("runtime") or call_args[1].get("runtime")
        assert runtime.vacuum_after_run is True  # CLI enabled=True
        assert runtime.vacuum_retention_days == 30
