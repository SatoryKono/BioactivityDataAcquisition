"""Unit tests for the PreflightService class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.preflight_service import PreflightService
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions import InfrastructureError
from bioetl.domain.types import (
    ConfigValidationError,
    HealthReport,
    HealthStatus,
    PreflightReport,
    RunType,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port."""
    metrics = MagicMock()
    metrics.set_gauge = MagicMock()
    metrics.observe_histogram = MagicMock()
    return metrics


@pytest.fixture
def pipeline_config():
    """Create a pipeline config."""
    return PipelineConfig(
        pipeline_name="test_preflight_pipeline",
        provider="chembl",
        entity_type="activity",
        primary_keys=["activity_id"],
        silver_table="test_silver",
        gold_write_mode="scd2",  # Use valid gold write mode per medallion policy
    )


@pytest.fixture
def mock_context(mock_logger):
    """Create a mock pipeline context."""
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    services = MagicMock()
    services.storage = MagicMock()
    services.storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    services.data_source = MagicMock()
    services.data_source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    services.logger = MagicMock()
    services.logger.info = MagicMock()
    services.logger.warning = MagicMock()
    services.logger.error = MagicMock()
    return services


@pytest.fixture
def preflight_service(pipeline_config, mock_context, mock_logger, mock_metrics):
    """Create a PreflightService instance."""
    return PreflightService(
        config=pipeline_config,
        context=mock_context,
        logger=mock_logger,
        metrics=mock_metrics,
    )


@pytest.mark.unit
class TestPreflightServiceInit:
    """Tests for PreflightService initialization."""

    def test_initialization(
        self, pipeline_config, mock_context, mock_logger, mock_metrics
    ):
        """Test preflight service initializes correctly."""
        service = PreflightService(
            config=pipeline_config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )

        assert service._config == pipeline_config
        assert service._context == mock_context
        assert service._logger == mock_logger
        assert service._metrics == mock_metrics


@pytest.mark.unit
class TestPreflightServiceValidation:
    """Tests for PreflightService.validate_infrastructure method."""

    @pytest.mark.asyncio
    async def test_validate_infrastructure_success(
        self, preflight_service, mock_services
    ):
        """Test validate_infrastructure with healthy components."""
        report = await preflight_service.validate_infrastructure(mock_services)

        assert report.is_healthy
        assert len(report.results) == 2  # storage + data_source

    @pytest.mark.asyncio
    async def test_validate_infrastructure_logs_start(
        self, preflight_service, mock_services, mock_logger
    ):
        """Test validate_infrastructure logs start message."""
        await preflight_service.validate_infrastructure(mock_services)

        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Validating infrastructure health" in call for call in calls)

    @pytest.mark.asyncio
    async def test_validate_infrastructure_logs_completion(
        self, preflight_service, mock_services, mock_logger
    ):
        """Test validate_infrastructure logs completion message."""
        await preflight_service.validate_infrastructure(mock_services)

        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("health check completed" in call for call in calls)

    @pytest.mark.asyncio
    async def test_validate_infrastructure_records_per_component_metrics(
        self, preflight_service, mock_services, mock_metrics
    ):
        """Test validate_infrastructure records per-component metrics."""
        await preflight_service.validate_infrastructure(mock_services)

        # Should have set_gauge calls for each component
        gauge_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call[0][0] == "pipeline_health_check_passed"
        ]
        assert len(gauge_calls) == 2  # storage + data_source

    @pytest.mark.asyncio
    async def test_validate_infrastructure_records_overall_validation_metric(
        self, preflight_service, mock_services, mock_metrics
    ):
        """Test validate_infrastructure records overall validation metric."""
        await preflight_service.validate_infrastructure(mock_services)

        gauge_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call[0][0] == "infrastructure_validated"
        ]
        assert len(gauge_calls) == 1
        # Should be 1.0 for healthy
        assert gauge_calls[0][0][1] == 1.0

    @pytest.mark.asyncio
    async def test_validate_infrastructure_records_duration_metric(
        self, preflight_service, mock_services, mock_metrics
    ):
        """Test validate_infrastructure records duration histogram."""
        await preflight_service.validate_infrastructure(mock_services)

        # Look for the overall duration metric (with pipeline label)
        histogram_calls = [
            call
            for call in mock_metrics.observe_histogram.call_args_list
            if call[0][0] == "health_check_duration_seconds"
            and "pipeline" in call[0][2]  # Overall duration has pipeline label
        ]
        assert len(histogram_calls) == 1

    @pytest.mark.asyncio
    async def test_validate_infrastructure_raises_on_unhealthy(self, preflight_service):
        """Test validate_infrastructure raises InfrastructureError on unhealthy."""
        unhealthy_services = MagicMock()
        unhealthy_services.storage = MagicMock()
        unhealthy_services.storage.health_check = AsyncMock(
            return_value=HealthStatus.UNHEALTHY
        )
        unhealthy_services.data_source = MagicMock()
        unhealthy_services.data_source.health_check = AsyncMock(
            return_value=HealthStatus.HEALTHY
        )
        unhealthy_services.logger = MagicMock()

        with pytest.raises(InfrastructureError, match="Health check failed"):
            await preflight_service.validate_infrastructure(unhealthy_services)

    @pytest.mark.asyncio
    async def test_validate_infrastructure_passes_with_degraded(
        self, preflight_service
    ):
        """Test validate_infrastructure passes with degraded status."""
        degraded_services = MagicMock()
        degraded_services.storage = MagicMock()
        degraded_services.storage.health_check = AsyncMock(
            return_value=HealthStatus.DEGRADED
        )
        degraded_services.data_source = MagicMock()
        degraded_services.data_source.health_check = AsyncMock(
            return_value=HealthStatus.HEALTHY
        )
        degraded_services.logger = MagicMock()

        # Should not raise - degraded is acceptable
        report = await preflight_service.validate_infrastructure(degraded_services)
        assert report.is_healthy


@pytest.mark.unit
class TestPreflightServiceMetrics:
    """Tests for PreflightService metric recording."""

    @pytest.mark.asyncio
    async def test_records_failed_validation_metric(
        self, pipeline_config, mock_context, mock_logger, mock_metrics
    ):
        """Test records 0.0 for failed validation."""
        service = PreflightService(
            config=pipeline_config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )

        unhealthy_services = MagicMock()
        unhealthy_services.storage = MagicMock()
        unhealthy_services.storage.health_check = AsyncMock(
            return_value=HealthStatus.UNHEALTHY
        )
        unhealthy_services.data_source = MagicMock()
        unhealthy_services.data_source.health_check = AsyncMock(
            return_value=HealthStatus.HEALTHY
        )
        unhealthy_services.logger = MagicMock()

        with pytest.raises(InfrastructureError):
            await service.validate_infrastructure(unhealthy_services)

        # Check that infrastructure_validated was set to 0.0
        gauge_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call[0][0] == "infrastructure_validated"
        ]
        assert len(gauge_calls) == 1
        assert gauge_calls[0][0][1] == 0.0


@pytest.fixture
def incremental_runtime():
    """Create an incremental runtime config."""
    return RuntimeConfig(run_type=RunType.INCREMENTAL)


@pytest.fixture
def rebuild_runtime():
    """Create a rebuild runtime config."""
    return RuntimeConfig(run_type=RunType.REBUILD)


@pytest.fixture
def backfill_runtime():
    """Create a backfill runtime config."""
    return RuntimeConfig(run_type=RunType.BACKFILL)


@pytest.fixture
def strict_runtime():
    """Create a strict validation runtime config."""
    return RuntimeConfig(run_type=RunType.INCREMENTAL, strict_validation=True)


@pytest.mark.unit
class TestValidateMedallionConfig:
    """Tests for PreflightService.validate_medallion_config method."""

    def test_valid_config_returns_empty_errors(
        self, preflight_service, incremental_runtime
    ):
        """Test that valid configuration returns no errors."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )
        assert errors == []

    def test_silver_format_must_be_delta(self, preflight_service, incremental_runtime):
        """Test that Silver format must be 'delta'."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="parquet",  # Invalid!
            gold_format="delta",
        )

        assert len(errors) == 1
        assert errors[0].field == "sink.silver.format"
        assert errors[0].expected == "delta"
        assert errors[0].actual == "parquet"
        assert "RULES §4.1" in errors[0].rule

    def test_gold_format_allows_delta(self, preflight_service, incremental_runtime):
        """Test that Gold format 'delta' is valid."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )
        assert errors == []

    def test_gold_format_allows_parquet(self, preflight_service, incremental_runtime):
        """Test that Gold format 'parquet' is valid."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="parquet",
        )
        assert errors == []

    def test_gold_format_rejects_jsonl(self, preflight_service, incremental_runtime):
        """Test that Gold format 'jsonl' is invalid."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="jsonl",  # Invalid!
        )

        assert len(errors) == 1
        assert errors[0].field == "sink.gold.format"
        assert errors[0].expected == "delta or parquet"
        assert errors[0].actual == "jsonl"
        assert "RULES §4.1" in errors[0].rule

    def test_paths_must_be_unique_bronze_silver(
        self, preflight_service, incremental_runtime
    ):
        """Test that Bronze and Silver paths must be different."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/shared",
            silver_path="/data/shared",  # Duplicate!
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )

        assert len(errors) == 1
        assert errors[0].field == "storage.paths"
        assert "bronze_path == silver_path" in errors[0].actual

    def test_paths_must_be_unique_silver_gold(
        self, preflight_service, incremental_runtime
    ):
        """Test that Silver and Gold paths must be different."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/shared",
            gold_path="/data/shared",  # Duplicate!
            silver_format="delta",
            gold_format="delta",
        )

        assert len(errors) == 1
        assert errors[0].field == "storage.paths"
        assert "silver_path == gold_path" in errors[0].actual

    def test_paths_must_be_unique_bronze_gold(
        self, preflight_service, incremental_runtime
    ):
        """Test that Bronze and Gold paths must be different."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/shared",
            silver_path="/data/silver",
            gold_path="/data/shared",  # Duplicate!
            silver_format="delta",
            gold_format="delta",
        )

        assert len(errors) == 1
        assert errors[0].field == "storage.paths"
        assert "bronze_path == gold_path" in errors[0].actual

    def test_all_paths_same_reports_multiple_errors(
        self, preflight_service, incremental_runtime
    ):
        """Test that all paths being the same reports multiple errors."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/shared",
            silver_path="/data/shared",
            gold_path="/data/shared",
            silver_format="delta",
            gold_format="delta",
        )

        # Should report 3 duplicate path errors
        path_errors = [e for e in errors if e.field == "storage.paths"]
        assert len(path_errors) == 3

    def test_incremental_policy_no_clear(self, preflight_service, incremental_runtime):
        """Test INCREMENTAL run type does not clear layers (policy consistency)."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )

        # MedallionPolicy for INCREMENTAL should NOT clear - this is consistent
        policy_errors = [e for e in errors if "medallion_policy" in e.field]
        assert len(policy_errors) == 0

    def test_rebuild_policy_clears_both_layers(
        self, preflight_service, rebuild_runtime
    ):
        """Test REBUILD run type clears both layers (policy consistency)."""
        errors = preflight_service.validate_medallion_config(
            runtime=rebuild_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )

        # MedallionPolicy for REBUILD should clear both - this is consistent
        policy_errors = [e for e in errors if "medallion_policy" in e.field]
        assert len(policy_errors) == 0

    def test_backfill_policy_clears_both_layers(
        self, preflight_service, backfill_runtime
    ):
        """Test BACKFILL run type clears both layers (policy consistency)."""
        errors = preflight_service.validate_medallion_config(
            runtime=backfill_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )

        # MedallionPolicy for BACKFILL should clear both - this is consistent
        policy_errors = [e for e in errors if "medallion_policy" in e.field]
        assert len(policy_errors) == 0

    def test_logs_warning_on_errors(
        self, preflight_service, mock_logger, incremental_runtime
    ):
        """Test that validation errors are logged as warnings."""
        preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="parquet",  # Invalid!
            gold_format="delta",
        )

        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert "Medallion config validation found issues" in str(call_args)

    def test_logs_debug_on_success(
        self, preflight_service, mock_logger, incremental_runtime
    ):
        """Test that successful validation is logged as debug."""
        preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )

        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args
        assert "Medallion config validation passed" in str(call_args)

    def test_multiple_errors_accumulated(self, preflight_service, incremental_runtime):
        """Test that multiple validation errors are accumulated."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="parquet",  # Invalid!
            gold_format="jsonl",  # Invalid!
        )

        # Should have at least 2 errors: silver format and gold format
        assert len(errors) >= 2
        fields = [e.field for e in errors]
        assert "sink.silver.format" in fields
        assert "sink.gold.format" in fields

    def test_missing_format_no_error(self, preflight_service, incremental_runtime):
        """Test that missing format does not cause errors."""
        errors = preflight_service.validate_medallion_config(
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            # No format specified
        )

        # No format errors if format is not specified
        format_errors = [e for e in errors if "format" in e.field]
        assert len(format_errors) == 0

    def test_strict_validation_flag_included_in_log(
        self, preflight_service, mock_logger, strict_runtime
    ):
        """Test that strict_validation flag is included in log output."""
        preflight_service.validate_medallion_config(
            runtime=strict_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="parquet",  # Invalid!
            gold_format="delta",
        )

        # Check that strict_mode is logged
        call_kwargs = mock_logger.warning.call_args
        assert "extra" in call_kwargs.kwargs or len(call_kwargs.args) > 1


@pytest.mark.unit
class TestConfigValidationErrorDataclass:
    """Tests for ConfigValidationError dataclass."""

    def test_config_validation_error_creation(self):
        """Test ConfigValidationError can be created with all fields."""
        error = ConfigValidationError(
            field="sink.silver.format",
            expected="delta",
            actual="parquet",
            rule="RULES §4.1: Silver MUST use Delta Lake",
        )

        assert error.field == "sink.silver.format"
        assert error.expected == "delta"
        assert error.actual == "parquet"
        assert error.rule == "RULES §4.1: Silver MUST use Delta Lake"

    def test_config_validation_error_is_frozen(self):
        """Test ConfigValidationError is immutable (frozen)."""
        error = ConfigValidationError(
            field="test",
            expected="a",
            actual="b",
            rule="test rule",
        )

        with pytest.raises(AttributeError):
            error.field = "new_field"  # type: ignore[misc]

    def test_config_validation_error_equality(self):
        """Test ConfigValidationError equality comparison."""
        error1 = ConfigValidationError(
            field="test",
            expected="a",
            actual="b",
            rule="test rule",
        )
        error2 = ConfigValidationError(
            field="test",
            expected="a",
            actual="b",
            rule="test rule",
        )

        assert error1 == error2


@pytest.mark.unit
class TestRuntimeConfigStrictValidation:
    """Tests for RuntimeConfig.strict_validation flag."""

    def test_strict_validation_default_false(self):
        """Test strict_validation defaults to False."""
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
        assert runtime.strict_validation is False

    def test_strict_validation_can_be_enabled(self):
        """Test strict_validation can be set to True."""
        runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            strict_validation=True,
        )
        assert runtime.strict_validation is True

    def test_strict_validation_with_other_flags(self):
        """Test strict_validation works with other runtime flags."""
        runtime = RuntimeConfig(
            run_type=RunType.REBUILD,
            strict_validation=True,
            dry_run=True,
            limit=100,
        )
        assert runtime.strict_validation is True
        assert runtime.dry_run is True
        assert runtime.limit == 100


@pytest.mark.unit
class TestValidateWriteModes:
    """Tests for PreflightService.validate_write_modes method."""

    def test_valid_write_modes_returns_empty_errors(self, preflight_service):
        """Test that valid write modes return no errors."""
        errors = preflight_service.validate_write_modes()
        assert errors == []

    def test_silver_merge_mode_is_valid(self, mock_context, mock_logger, mock_metrics):
        """Test that Silver 'merge' mode is valid."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            write_mode="merge",
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        errors = service.validate_write_modes()
        assert len([e for e in errors if e.field == "write_mode"]) == 0

    def test_silver_append_mode_is_valid(self, mock_context, mock_logger, mock_metrics):
        """Test that Silver 'append' mode is valid."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            write_mode="append",
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        errors = service.validate_write_modes()
        assert len([e for e in errors if e.field == "write_mode"]) == 0

    def test_silver_overwrite_mode_is_invalid(
        self, mock_context, mock_logger, mock_metrics
    ):
        """Test that Silver 'overwrite' mode is invalid."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            write_mode="overwrite",
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        errors = service.validate_write_modes()
        silver_errors = [e for e in errors if e.field == "write_mode"]
        assert len(silver_errors) == 1
        assert "RULES §2.1" in silver_errors[0].rule

    def test_gold_merge_mode_is_valid(self, mock_context, mock_logger, mock_metrics):
        """Test that Gold 'merge' mode is valid."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            gold_write_mode="scd2",
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        errors = service.validate_write_modes()
        assert len([e for e in errors if e.field == "gold_write_mode"]) == 0

    def test_gold_overwrite_mode_is_valid(
        self, mock_context, mock_logger, mock_metrics
    ):
        """Test that Gold 'overwrite' mode is valid."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            gold_write_mode="overwrite",
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        errors = service.validate_write_modes()
        assert len([e for e in errors if e.field == "gold_write_mode"]) == 0

    def test_gold_scd2_mode_is_valid(self, mock_context, mock_logger, mock_metrics):
        """Test that Gold 'scd2' mode is valid (maps to merge)."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            gold_write_mode="scd2",
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        errors = service.validate_write_modes()
        assert len([e for e in errors if e.field == "gold_write_mode"]) == 0

    def test_gold_append_mode_is_invalid(self, mock_context, mock_logger, mock_metrics):
        """Test that Gold 'append' mode is invalid."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            gold_write_mode="append",
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        errors = service.validate_write_modes()
        gold_errors = [e for e in errors if e.field == "gold_write_mode"]
        assert len(gold_errors) == 1
        assert "RULES §2.1" in gold_errors[0].rule

    def test_logs_warning_on_invalid_modes(
        self, mock_context, mock_logger, mock_metrics
    ):
        """Test that invalid write modes are logged as warnings."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            write_mode="overwrite",  # Invalid
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )
        service.validate_write_modes()
        mock_logger.warning.assert_called()

    def test_logs_debug_on_valid_modes(self, preflight_service, mock_logger):
        """Test that valid write modes are logged as debug."""
        preflight_service.validate_write_modes()
        mock_logger.debug.assert_called()


@pytest.mark.unit
class TestValidatePreflight:
    """Tests for PreflightService.validate_preflight method."""

    @pytest.mark.asyncio
    async def test_validate_preflight_returns_report(
        self, preflight_service, mock_services, incremental_runtime
    ):
        """Test validate_preflight returns a PreflightReport."""
        report = await preflight_service.validate_preflight(
            services=mock_services,
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )

        assert isinstance(report, PreflightReport)
        assert report.medallion_policy_valid is True
        assert report.health_report is not None
        assert len(report.config_errors) == 0

    @pytest.mark.asyncio
    async def test_validate_preflight_with_config_errors(
        self, preflight_service, mock_services, incremental_runtime
    ):
        """Test validate_preflight with configuration errors."""
        report = await preflight_service.validate_preflight(
            services=mock_services,
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="parquet",  # Invalid!
            gold_format="delta",
        )

        assert report.medallion_policy_valid is False
        assert len(report.config_errors) > 0
        assert report.should_block_startup is True

    @pytest.mark.asyncio
    async def test_validate_preflight_strict_mode_raises(
        self, preflight_service, mock_services
    ):
        """Test validate_preflight raises in strict mode on errors."""
        strict_runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            strict_validation=True,
        )

        with pytest.raises(ValueError, match="Preflight validation failed"):
            await preflight_service.validate_preflight(
                services=mock_services,
                runtime=strict_runtime,
                bronze_path="/data/bronze",
                silver_path="/data/silver",
                gold_path="/data/gold",
                silver_format="parquet",  # Invalid!
                gold_format="delta",
            )

    @pytest.mark.asyncio
    async def test_validate_preflight_non_strict_mode_returns_report(
        self, preflight_service, mock_services, incremental_runtime
    ):
        """Test validate_preflight returns report in non-strict mode with errors."""
        report = await preflight_service.validate_preflight(
            services=mock_services,
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="parquet",  # Invalid!
            gold_format="delta",
        )

        # Should not raise, should return report
        assert report.medallion_policy_valid is False

    @pytest.mark.asyncio
    async def test_validate_preflight_records_metrics(
        self, preflight_service, mock_services, incremental_runtime, mock_metrics
    ):
        """Test validate_preflight records metrics."""
        await preflight_service.validate_preflight(
            services=mock_services,
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )

        # Check metrics were recorded
        gauge_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call[0][0] == "preflight_medallion_policy_valid"
        ]
        assert len(gauge_calls) == 1
        assert gauge_calls[0][0][1] == 1.0  # Valid

    @pytest.mark.asyncio
    async def test_validate_preflight_includes_write_mode_errors(
        self,
        mock_context,
        mock_logger,
        mock_metrics,
        mock_services,
        incremental_runtime,
    ):
        """Test validate_preflight includes write mode validation errors."""
        config = PipelineConfig(
            pipeline_name="test",
            provider="chembl",
            entity_type="activity",
            primary_keys=["id"],
            silver_table="silver",
            write_mode="overwrite",  # Invalid for Silver
        )
        service = PreflightService(
            config=config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )

        report = await service.validate_preflight(
            services=mock_services,
            runtime=incremental_runtime,
            bronze_path="/data/bronze",
            silver_path="/data/silver",
            gold_path="/data/gold",
            silver_format="delta",
            gold_format="delta",
        )

        assert report.medallion_policy_valid is False
        write_mode_errors = [e for e in report.config_errors if e.field == "write_mode"]
        assert len(write_mode_errors) == 1


@pytest.mark.unit
class TestPreflightReportDataclass:
    """Tests for PreflightReport dataclass."""

    def test_preflight_report_creation(self):
        """Test PreflightReport can be created with required fields."""
        health_report = HealthReport(results=[])
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=True,
        )

        assert report.health_report == health_report
        assert report.medallion_policy_valid is True
        assert report.config_errors == []

    def test_preflight_report_with_errors(self):
        """Test PreflightReport with config errors."""
        health_report = HealthReport(results=[])
        error = ConfigValidationError(
            field="test", expected="a", actual="b", rule="test rule"
        )
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=False,
            config_errors=[error],
        )

        assert report.medallion_policy_valid is False
        assert len(report.config_errors) == 1

    def test_preflight_report_is_valid_when_all_pass(self):
        """Test is_valid returns True when all validations pass."""
        health_report = HealthReport(results=[])
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=True,
        )

        assert report.is_valid is True

    def test_preflight_report_is_valid_false_on_policy_error(self):
        """Test is_valid returns False on policy errors."""
        health_report = HealthReport(results=[])
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=False,
        )

        assert report.is_valid is False

    def test_preflight_report_should_block_startup(self):
        """Test should_block_startup returns True on policy errors."""
        health_report = HealthReport(results=[])
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=False,
        )

        assert report.should_block_startup is True

    def test_preflight_report_should_not_block_when_valid(self):
        """Test should_block_startup returns False when valid."""
        health_report = HealthReport(results=[])
        report = PreflightReport(
            health_report=health_report,
            medallion_policy_valid=True,
        )

        assert report.should_block_startup is False
