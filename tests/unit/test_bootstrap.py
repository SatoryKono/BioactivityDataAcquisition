"""Unit tests for bootstrap module."""

from __future__ import annotations

from unittest.mock import ANY, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.runner import PipelineRunner
from bioetl.domain.context import PipelineRunContext
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
    """Create mock PipelineServices."""
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
    return config


@pytest.mark.unit
class TestBootstrapLogger:
    """Tests for bootstrap_logger function."""

    def test_bootstrap_logger_creates_logger(self):
        """Test that bootstrap_logger creates a logger."""
        from bioetl.composition.bootstrap import bootstrap_logger

        run_id = uuid4()
        logger = bootstrap_logger(
            pipeline="test_pipeline",
            run_id=run_id,
            log_level="INFO",
        )

        assert logger is not None


@pytest.mark.unit
class TestBootstrapPipeline:
    """Tests for bootstrap_pipeline function."""

    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition.bootstrap.bootstrap_tracer")
    @patch("bioetl.composition.bootstrap.get_settings")
    @patch("bioetl.composition.bootstrap.bootstrap_logger")
    def test_bootstrap_pipeline_unknown_pipeline_raises(
        self,
        mock_bootstrap_logger: MagicMock,
        mock_get_settings: MagicMock,
        mock_bootstrap_tracer: MagicMock,
        mock_start_metrics: MagicMock,
        mock_settings: MagicMock,
        mock_logger: MagicMock,
    ):
        """Test that unknown pipeline name raises ValueError."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        # Configure settings with required observability attributes
        mock_settings.metrics_port = 8000
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
        mock_bootstrap_logger.return_value = mock_logger
        mock_bootstrap_tracer.return_value = MagicMock()

        # Now raises "Configuration file not found" because load_pipeline_config is called first
        ctx = PipelineRunContext(
            pipeline_name="unknown_pipeline",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=None,
        )
        with pytest.raises(ValueError, match="Configuration file not found"):
            bootstrap_pipeline(ctx)

    @patch("bioetl.composition.bootstrap.PipelineRegistry")
    @patch("bioetl.composition.bootstrap.FilterConfigBuilder")
    @patch("bioetl.composition.bootstrap.load_pipeline_config")
    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition.bootstrap.bootstrap_tracer")
    @patch("bioetl.composition.bootstrap.bootstrap_logger")
    @patch("bioetl.composition.bootstrap.get_settings")
    def test_bootstrap_pipeline_metrics_server_failure_non_blocking(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_logger: MagicMock,
        mock_bootstrap_tracer: MagicMock,
        mock_start_metrics: MagicMock,
        mock_load_config: MagicMock,
        mock_filter_builder: MagicMock,
        mock_registry: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that metrics server failure doesn't block pipeline bootstrap."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        # Create proper mock settings with required attributes
        test_settings = MagicMock()
        test_settings.metrics_port = 8000
        test_settings.pipeline = MagicMock()
        test_settings.pipeline.heartbeat_interval = 30
        test_settings.pipeline.vacuum_retention_days = 7
        # Add observability settings for bootstrap_metrics()
        test_settings.observability = MagicMock()
        test_settings.observability.metrics_enabled = True
        test_settings.observability.metrics_server_enabled = True
        test_settings.observability.metrics_fail_fast = False
        test_settings.observability.metrics_retry_count = 3
        test_settings.observability.metrics_retry_delay = 1.0
        test_settings.observability.tracing_enabled = False
        test_settings.observability.dq_baseline_window = 7
        test_settings.observability.dq_z_score_threshold = 2.5
        test_settings.observability.dq_min_baseline_samples = 3
        test_settings.observability.dq_error_rate_max = 0.10
        test_settings.observability.dq_quality_score_min = 0.80

        mock_get_settings.return_value = test_settings
        mock_bootstrap_logger.return_value = mock_logger
        mock_bootstrap_tracer.return_value = MagicMock()
        mock_filter_builder.build.return_value = None

        # Simulate metrics server failure
        mock_start_metrics.side_effect = Exception("Port already in use")

        # Setup pipeline registry mock
        mock_config = MagicMock()
        mock_config.maintenance.vacuum_retention_days = 7
        mock_load_config.return_value = mock_config
        mock_factory = MagicMock()
        mock_runner = MagicMock()
        mock_factory.create_runner.return_value = mock_runner
        mock_registry.get.return_value.factory = mock_factory

        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            resume=False,
            limit=None,
        )

        # Should not raise, should return runner despite metrics failure
        # (error is suppressed via contextlib.suppress in bootstrap_metrics)
        result = bootstrap_pipeline(ctx)

        assert result is mock_runner
        mock_start_metrics.assert_called_once_with(
            port=test_settings.metrics_port,
            fail_fast=False,
            retry_count=3,
            retry_delay=1.0,
        )

    @pytest.mark.skip(
        reason="Requires full integration setup - covered by integration tests"
    )
    @patch("bioetl.composition.bootstrap.get_settings")
    @patch("bioetl.composition.bootstrap.PipelineRegistry")
    def test_bootstrap_pipeline_chembl_activity(
        self, mock_registry, mock_get_settings, mock_settings, mock_logger
    ):
        """Test bootstrap_pipeline creates chembl_activity pipeline."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        mock_get_settings.return_value = mock_settings
        mock_pipeline = MagicMock()
        mock_factory = MagicMock()
        mock_factory.create_with_services.return_value = mock_pipeline
        mock_registry.get.return_value.factory = mock_factory

        with patch(
            "bioetl.composition.bootstrap.bootstrap_logger", return_value=mock_logger
        ):
            ctx = PipelineRunContext(
                pipeline_name="chembl_activity",
                run_id=uuid4(),
                run_type=RunType.INCREMENTAL,
                resume=False,
                limit=100,
            )
            result = bootstrap_pipeline(ctx)

        assert isinstance(result, PipelineRunner)
        mock_factory.create_with_services.assert_called_once()


@pytest.mark.unit
class TestChemblActivityFactory:
    """Tests for chembl_activity_factory (GenericPipelineFactory instance)."""

    @patch("bioetl.composition.factories.runner_assembly.BaseServicesFactory")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
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
        chembl_activity_factory._create_data_source = MagicMock(return_value=mock_data_source)

        services = chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        assert services is not None
        chembl_activity_factory._create_data_source.assert_called_once()

    @patch("bioetl.composition.factories.runner_assembly.BaseServicesFactory")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
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
        chembl_activity_factory._create_data_source = MagicMock(return_value=mock_data_source)

        chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
        )

        mock_base_services.create_common_services.assert_called_once()

    @patch("bioetl.composition.factories.runner_assembly.BaseServicesFactory")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
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
        chembl_activity_factory._create_data_source = MagicMock(return_value=mock_data_source)

        chembl_activity_factory.build_services(
            settings=mock_settings,
            logger=mock_logger,
            config=mock_pipeline_config,
        )

        # Should NOT call load_pipeline_config when config is provided
        mock_load_config.assert_not_called()

    @patch("bioetl.composition.factories.runner_assembly.yaml_config_to_domain")
    @patch("bioetl.composition.factories.generic_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.runner_assembly.BaseServicesFactory")
    def test_create_with_services(
        self,
        mock_base_services,
        mock_load_config,
        mock_yaml_to_domain,
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

        # Mock the data source creator
        mock_data_source = MagicMock()
        chembl_activity_factory._create_data_source = MagicMock(return_value=mock_data_source)

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
    """Tests for bootstrap_metrics function with metrics configuration."""

    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition._bootstrap.observability.PrometheusMetrics")
    def test_bootstrap_metrics_passes_config_params(
        self,
        mock_prometheus: MagicMock,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that bootstrap_metrics passes config params to start_metrics_server."""
        from bioetl.composition.bootstrap import bootstrap_metrics

        # Create mock settings with metrics config
        settings = MagicMock()
        settings.metrics_port = 9090
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 5
        settings.observability.metrics_retry_delay = 2.0

        mock_metrics = MagicMock()
        mock_prometheus.return_value = mock_metrics

        result = bootstrap_metrics(settings)

        assert result is mock_metrics
        mock_start_server.assert_called_once_with(
            port=9090,
            fail_fast=False,
            retry_count=5,
            retry_delay=2.0,
        )

    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition._bootstrap.observability.PrometheusMetrics")
    def test_bootstrap_metrics_fail_fast_true_raises_error(
        self,
        mock_prometheus: MagicMock,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that fail_fast=True propagates MetricsServerError."""
        from bioetl.composition.bootstrap import bootstrap_metrics
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
            bootstrap_metrics(settings)

        assert exc_info.value.port == 8000
        assert exc_info.value.reason == "port_in_use"

    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition._bootstrap.observability.PrometheusMetrics")
    def test_bootstrap_metrics_fail_fast_false_suppresses_error(
        self,
        mock_prometheus: MagicMock,
        mock_start_server: MagicMock,
    ) -> None:
        """Test that fail_fast=False suppresses exceptions."""
        from bioetl.composition.bootstrap import bootstrap_metrics

        settings = MagicMock()
        settings.metrics_port = 8000
        settings.observability.metrics_enabled = True
        settings.observability.metrics_server_enabled = True
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0

        mock_metrics = MagicMock()
        mock_prometheus.return_value = mock_metrics

        # Simulate exception in lenient mode
        mock_start_server.side_effect = Exception("Random failure")

        # Should not raise, should return metrics
        result = bootstrap_metrics(settings)

        assert result is mock_metrics

    def test_bootstrap_metrics_disabled_returns_noop_metrics(self) -> None:
        """Test that disabled metrics returns NoOpMetrics (not None).

        Per Unified Observability Contract, bootstrap_metrics() always
        returns a valid MetricsPort implementation. When metrics are
        disabled, NoOpMetrics is used as a silent fallback.
        """
        from bioetl.composition.bootstrap import bootstrap_metrics
        from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics

        settings = MagicMock()
        settings.observability.metrics_enabled = False

        result = bootstrap_metrics(settings)

        assert result is not None
        assert isinstance(result, NoOpMetrics)


@pytest.mark.unit
class TestBootstrapVacuumConfig:
    """Tests for bootstrap_pipeline vacuum configuration merging."""

    @patch("bioetl.composition.bootstrap.PipelineRegistry")
    @patch("bioetl.composition.bootstrap.FilterConfigBuilder")
    @patch("bioetl.composition.bootstrap.load_pipeline_config")
    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition.bootstrap.bootstrap_tracer")
    @patch("bioetl.composition.bootstrap.bootstrap_logger")
    @patch("bioetl.composition.bootstrap.get_settings")
    def test_bootstrap_uses_yaml_vacuum_config_when_cli_not_set(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_logger: MagicMock,
        mock_bootstrap_tracer: MagicMock,
        mock_start_metrics: MagicMock,
        mock_load_config: MagicMock,
        mock_filter_builder: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """Test that YAML auto_vacuum config is used when CLI doesn't override."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        # Create settings with all required observability attributes
        settings = MagicMock()
        settings.metrics_port = 8000
        settings.pipeline.heartbeat_interval = 30
        settings.observability.metrics_enabled = False
        settings.observability.metrics_server_enabled = False
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0
        settings.observability.tracing_enabled = False
        settings.observability.dq_baseline_window = 7
        settings.observability.dq_z_score_threshold = 2.5
        settings.observability.dq_min_baseline_samples = 3
        settings.observability.dq_error_rate_max = 0.10
        settings.observability.dq_quality_score_min = 0.80
        mock_get_settings.return_value = settings

        # Create logger
        logger = MagicMock()
        logger.bind.return_value = logger
        mock_bootstrap_logger.return_value = logger
        mock_bootstrap_tracer.return_value = MagicMock()
        mock_filter_builder.build.return_value = None

        # Setup YAML config with auto_vacuum enabled
        yaml_config = MagicMock()
        yaml_config.maintenance.auto_vacuum = True
        yaml_config.maintenance.vacuum_retention_days = 14
        yaml_config.input_filter = MagicMock()
        mock_load_config.return_value = yaml_config

        # Setup pipeline registry
        mock_factory = MagicMock()
        mock_runner = MagicMock()
        mock_factory.create_runner.return_value = mock_runner
        mock_registry.get.return_value.factory = mock_factory

        # Context without CLI vacuum options (None)
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            vacuum_after_run=None,
            vacuum_retention_days=None,
        )

        bootstrap_pipeline(ctx)

        # Verify runtime config was passed with YAML values
        call_args = mock_factory.create_runner.call_args
        runtime = call_args.kwargs.get("runtime") or call_args[1].get("runtime")
        assert runtime.vacuum_after_run is True
        assert runtime.vacuum_retention_days == 14

    @patch("bioetl.composition.bootstrap.PipelineRegistry")
    @patch("bioetl.composition.bootstrap.FilterConfigBuilder")
    @patch("bioetl.composition.bootstrap.load_pipeline_config")
    @patch("bioetl.composition._bootstrap.observability.start_metrics_server")
    @patch("bioetl.composition.bootstrap.bootstrap_tracer")
    @patch("bioetl.composition.bootstrap.bootstrap_logger")
    @patch("bioetl.composition.bootstrap.get_settings")
    def test_bootstrap_cli_vacuum_overrides_yaml_config(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_logger: MagicMock,
        mock_bootstrap_tracer: MagicMock,
        mock_start_metrics: MagicMock,
        mock_load_config: MagicMock,
        mock_filter_builder: MagicMock,
        mock_registry: MagicMock,
    ) -> None:
        """Test that CLI vacuum options override YAML config."""
        from bioetl.composition.bootstrap import bootstrap_pipeline

        # Create settings with all required observability attributes
        settings = MagicMock()
        settings.metrics_port = 8000
        settings.pipeline.heartbeat_interval = 30
        settings.observability.metrics_enabled = False
        settings.observability.metrics_server_enabled = False
        settings.observability.metrics_fail_fast = False
        settings.observability.metrics_retry_count = 3
        settings.observability.metrics_retry_delay = 1.0
        settings.observability.tracing_enabled = False
        settings.observability.dq_baseline_window = 7
        settings.observability.dq_z_score_threshold = 2.5
        settings.observability.dq_min_baseline_samples = 3
        settings.observability.dq_error_rate_max = 0.10
        settings.observability.dq_quality_score_min = 0.80
        mock_get_settings.return_value = settings

        # Create logger
        logger = MagicMock()
        logger.bind.return_value = logger
        mock_bootstrap_logger.return_value = logger
        mock_bootstrap_tracer.return_value = MagicMock()
        mock_filter_builder.build.return_value = None

        # Setup YAML config with auto_vacuum enabled
        yaml_config = MagicMock()
        yaml_config.maintenance.auto_vacuum = True
        yaml_config.maintenance.vacuum_retention_days = 14
        yaml_config.input_filter = MagicMock()
        mock_load_config.return_value = yaml_config

        # Setup pipeline registry
        mock_factory = MagicMock()
        mock_runner = MagicMock()
        mock_factory.create_runner.return_value = mock_runner
        mock_registry.get.return_value.factory = mock_factory

        # Context with CLI overrides (explicit False and 30 days)
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            vacuum_after_run=False,  # CLI override
            vacuum_retention_days=30,  # CLI override
        )

        bootstrap_pipeline(ctx)

        # Verify runtime config was passed with CLI values (overriding YAML)
        call_args = mock_factory.create_runner.call_args
        runtime = call_args.kwargs.get("runtime") or call_args[1].get("runtime")
        assert runtime.vacuum_after_run is False
        assert runtime.vacuum_retention_days == 30
