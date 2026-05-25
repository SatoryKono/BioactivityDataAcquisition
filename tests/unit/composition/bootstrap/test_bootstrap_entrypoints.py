"""Unit tests for pipeline bootstrap entrypoints."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.runner import PipelineRunner
from bioetl.domain.context import PipelineRunContext, VacuumSettings
from bioetl.domain.types import RunType


def _create_bootstrap_settings(
    *,
    metrics_enabled: bool = False,
    metrics_server_enabled: bool = False,
    tracing_enabled: bool = False,
    dq_monitor_enabled: bool = False,
) -> MagicMock:
    """Create settings mock with the runtime attributes bootstrap expects."""
    settings = MagicMock()
    settings.metrics_port = 8000
    settings.env = "test"
    settings.debug = False
    settings.test_mode = False
    settings.data_dir = ""
    settings.strict_error_handling = False
    settings.strict_medallion = False
    settings.silver_dedup_timeout_seconds = None
    settings.pii_salt_rotation_active = False
    settings.json_encoder = None
    settings.default_email = None
    settings.bio_api_key = None
    settings.chembl_api_key = None
    settings.pubchem_api_key = None
    settings.crossref_email = None
    settings.crossref_mailto = None
    settings.crossref_plus_token = None
    settings.pubmed_api_key = None
    settings.uniprot_api_key = None
    settings.openalex_api_key = None
    settings.semanticscholar_api_key = None
    settings.pipeline = SimpleNamespace()
    settings.pipeline.heartbeat_interval = 30
    settings.pipeline.vacuum_retention_days = 7
    settings.pipeline.batch_size = None
    settings.pipeline.checkpoint_interval = None
    settings.pipeline.relaxed_dq = False
    settings.pipeline.max_concurrent_batches = None
    settings.pipeline.health_check_mode = None
    settings.pipeline.control_plane = SimpleNamespace(
        required_persistence_profile="degraded_observable",
        run_manifest_enabled=True,
        run_ledger_enabled=True,
        checkpoint_compatibility_policy=None,
    )
    settings.observability = SimpleNamespace()
    settings.observability.metrics_enabled = metrics_enabled
    settings.observability.metrics_server_enabled = metrics_server_enabled
    settings.observability.metrics_fail_fast = False
    settings.observability.metrics_retry_count = 3
    settings.observability.metrics_retry_delay = 1.0
    settings.observability.tracing_enabled = tracing_enabled
    settings.observability.dq_monitor_enabled = dq_monitor_enabled
    settings.observability.dq_baseline_window = 7
    settings.observability.dq_z_score_threshold = 2.5
    settings.observability.dq_min_baseline_samples = 3
    settings.observability.dq_error_rate_max = 0.10
    settings.observability.dq_quality_score_min = 0.80
    settings.observability.audit_enabled = False
    return settings


def _create_observability_bundle(logger: MagicMock | None = None) -> MagicMock:
    """Create observability bundle mock with a bind-capable logger."""
    effective_logger = logger or MagicMock()
    effective_logger.bind = MagicMock(return_value=effective_logger)
    effective_logger.info = MagicMock()
    effective_logger.warning = MagicMock()
    bundle = MagicMock()
    bundle.logger = effective_logger
    return bundle


def _create_pipeline_yaml_config(
    *,
    auto_vacuum: bool = False,
    retention_days: int = 7,
    input_filter_enabled: bool = False,
) -> MagicMock:
    """Create a minimal pipeline config mock for bootstrap tests."""
    config = MagicMock()
    config.business_primary_keys = ["activity_id"]
    config.primary_keys = None
    config.technical_primary_key = "entity_id"
    config.maintenance.auto_vacuum = auto_vacuum
    config.maintenance.vacuum_retention_days = retention_days
    config.input_filter = MagicMock()
    config.input_filter.enabled = input_filter_enabled
    config.input_filter.source_path = ""
    config.input_filter.column_name = ""
    config.input_filter.filter_field = ""
    return config


def _configure_registry_with_runner(
    mock_create_registry: MagicMock,
    *,
    runner: object | None = None,
) -> tuple[MagicMock, MagicMock, object]:
    """Wire registry.get(...).factory.create_runner(...) to a provided runner."""
    effective_runner = runner or MagicMock(spec=PipelineRunner)
    factory = MagicMock()
    factory.create_runner.return_value = effective_runner
    registry = MagicMock()
    registry.list_pipelines.return_value = []
    registry.get.return_value.factory = factory
    mock_create_registry.return_value = registry
    return registry, factory, effective_runner


def _create_pipeline_context(
    *,
    pipeline_name: str = "chembl_activity",
    limit: int | None = None,
    vacuum: VacuumSettings | None = None,
) -> PipelineRunContext:
    """Create a standard pipeline run context for bootstrap tests."""
    context_kwargs = {
        "pipeline_name": pipeline_name,
        "run_id": uuid4(),
        "run_type": RunType.INCREMENTAL,
        "resume": False,
        "limit": limit,
    }
    if vacuum is not None:
        context_kwargs["vacuum"] = vacuum
    return PipelineRunContext(
        **context_kwargs,
    )


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = _create_bootstrap_settings()
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
    return _create_observability_bundle().logger


@pytest.mark.unit
class TestBootstrapPipeline:
    """Tests for bootstrap_pipeline_runner function."""

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.bootstrap_observability_bundle"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.get_settings")
    def test_bootstrap_pipeline_unknown_pipeline_raises(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_observability_bundle: MagicMock,
        mock_settings: MagicMock,
        mock_logger: MagicMock,
    ):
        """Test that unknown pipeline name raises ValueError."""
        from bioetl.composition.bootstrap.runtime.pipeline import (
            bootstrap_pipeline_runner,
        )

        settings = _create_bootstrap_settings(
            metrics_enabled=True,
            metrics_server_enabled=True,
        )
        mock_get_settings.return_value = settings

        # Runner bootstrap now resolves the factory through the registry first.
        ctx = _create_pipeline_context(pipeline_name="unknown_pipeline")
        with pytest.raises(ValueError, match="Unknown pipeline name"):
            bootstrap_pipeline_runner(ctx)

    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.create_registry")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.assemble_filter_config"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.create_pipeline_config_loader"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.bootstrap_observability_bundle"
    )
    @patch(
        "bioetl.composition.runtime_builders.runner_builder.create_run_manifest_with_effective_config"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.get_settings")
    def test_bootstrap_pipeline_creates_runner_without_starting_server(
        self,
        mock_get_settings: MagicMock,
        mock_create_run_manifest: MagicMock,
        mock_bootstrap_observability_bundle: MagicMock,
        mock_create_pipeline_loader: MagicMock,
        mock_assemble_filter: MagicMock,
        mock_create_registry: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that bootstrap_pipeline_runner creates runner without starting metrics server.

        After refactoring, bootstrap_metrics() no longer starts the metrics server.
        Server startup is handled by entrypoints via maybe_start_metrics_server().
        This test verifies that bootstrap_pipeline_runner creates a runner successfully
        regardless of metrics server state.
        """
        from bioetl.composition.bootstrap.runtime.pipeline import (
            bootstrap_pipeline_runner,
        )

        mock_get_settings.return_value = _create_bootstrap_settings(
            metrics_enabled=True,
            metrics_server_enabled=True,
        )
        mock_bootstrap_observability_bundle.return_value = _create_observability_bundle(
            mock_logger
        )
        mock_create_run_manifest.return_value = (
            SimpleNamespace(
                manifest_id="manifest-bootstrap-test",
                execution_fingerprint="fp-bootstrap-test",
                config_hash="a" * 64,
                resolved_config_hash="b" * 64,
                effective_config_hash="c" * 64,
                dq_contract_compatibility_hash="d" * 64,
                effective_config_artifact_id="eca-bootstrap-test",
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                contract_schema_hash="e" * 64,
                dq_policy_ref="chembl.activity.dq",
                rule_bundle_version="dq-rules.v1",
                normalization_profile_ref=None,
                normalization_profile_version=None,
                normalization_profile_hash=None,
                required_persistence_profile="degraded_observable",
            ),
            None,
        )

        mock_assemble_filter.return_value = None

        mock_pipeline_loader = MagicMock()
        mock_pipeline_loader.return_value = _create_pipeline_yaml_config()
        mock_create_pipeline_loader.return_value = mock_pipeline_loader
        _, _, mock_runner = _configure_registry_with_runner(mock_create_registry)

        ctx = _create_pipeline_context()

        # Should return runner - bootstrap no longer starts metrics server
        result = bootstrap_pipeline_runner(ctx)

        assert result is mock_runner
        # Verify observability was bootstrapped (creates MetricsPort, but doesn't start server)
        mock_bootstrap_observability_bundle.assert_called_once()

    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.get_settings")
    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.create_registry")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.bootstrap_observability_bundle"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.ensure_providers_loaded"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.register_all_pipelines"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.create_pipeline_config_loader"
    )
    @patch(
        "bioetl.composition.runtime_builders.runner_builder.create_run_manifest_with_effective_config"
    )
    def test_bootstrap_pipeline_chembl_activity(
        self,
        mock_create_run_manifest,
        mock_create_pipeline_loader,
        mock_register_pipelines,
        mock_ensure_loaded,
        mock_observability_bundle,
        mock_create_registry,
        mock_get_settings,
        mock_settings,
        mock_logger,
    ):
        """Test bootstrap_pipeline_runner creates chembl_activity pipeline."""
        from bioetl.composition.bootstrap.runtime.pipeline import (
            bootstrap_pipeline_runner,
        )

        mock_get_settings.return_value = mock_settings

        mock_pipeline_loader = MagicMock()
        mock_pipeline_loader.return_value = _create_pipeline_yaml_config()
        mock_create_pipeline_loader.return_value = mock_pipeline_loader
        mock_observability_bundle.return_value = _create_observability_bundle(
            mock_logger
        )
        mock_create_run_manifest.return_value = (
            SimpleNamespace(
                manifest_id="manifest-bootstrap-chembl-activity",
                execution_fingerprint="fp-bootstrap-chembl-activity",
                config_hash="f" * 64,
                resolved_config_hash="e" * 64,
                effective_config_hash="d" * 64,
                dq_contract_compatibility_hash="c" * 64,
                effective_config_artifact_id="eca-bootstrap-chembl-activity",
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                contract_schema_hash="b" * 64,
                dq_policy_ref="chembl.activity.dq",
                rule_bundle_version="dq-rules.v1",
                normalization_profile_ref=None,
                normalization_profile_version=None,
                normalization_profile_hash=None,
                required_persistence_profile="degraded_observable",
            ),
            None,
        )
        _, mock_factory, mock_runner = _configure_registry_with_runner(
            mock_create_registry
        )

        ctx = _create_pipeline_context(limit=100)
        result = bootstrap_pipeline_runner(ctx)

        assert result is mock_runner
        mock_factory.create_runner.assert_called_once()
        mock_ensure_loaded.assert_called_once_with()
        mock_register_pipelines.assert_called_once_with(
            registry=mock_create_registry.return_value
        )


@pytest.mark.unit
class TestBootstrapVacuumConfig:
    """Tests for bootstrap_pipeline_runner vacuum configuration merging."""

    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.create_registry")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.assemble_filter_config"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.create_pipeline_config_loader"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.bootstrap_observability_bundle"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.get_settings")
    def test_bootstrap_uses_yaml_vacuum_config_when_cli_not_set(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_observability_bundle: MagicMock,
        mock_create_pipeline_loader: MagicMock,
        mock_assemble_filter: MagicMock,
        mock_create_registry: MagicMock,
    ) -> None:
        """Test that YAML auto_vacuum config is used when CLI doesn't override."""
        from bioetl.composition.bootstrap.runtime.pipeline import (
            bootstrap_pipeline_runner,
        )

        settings = _create_bootstrap_settings()
        settings.pipeline.control_plane.required_persistence_profile = (
            "degraded_observable"
        )
        mock_get_settings.return_value = settings

        mock_bootstrap_observability_bundle.return_value = (
            _create_observability_bundle()
        )
        mock_assemble_filter.return_value = None

        mock_pipeline_loader = MagicMock()
        mock_pipeline_loader.return_value = _create_pipeline_yaml_config(
            auto_vacuum=True,
            retention_days=14,
        )
        mock_create_pipeline_loader.return_value = mock_pipeline_loader

        _, mock_factory, _ = _configure_registry_with_runner(mock_create_registry)

        # Context without CLI vacuum options (disabled VacuumSettings)
        ctx = _create_pipeline_context()

        with patch(
            "bioetl.composition.runtime_builders.runner_builder.create_run_manifest_with_effective_config",
            return_value=(
                SimpleNamespace(
                    manifest_id="manifest-test-1",
                    execution_fingerprint="fp-test-1",
                    config_hash="a" * 64,
                    resolved_config_hash="b" * 64,
                    effective_config_hash="c" * 64,
                    source_fingerprint="d" * 64,
                    dq_contract_compatibility_hash="e" * 64,
                    effective_config_artifact_id="eca-1",
                    contract_ref="chembl.activity",
                    contract_version="1.0.0",
                    contract_schema_hash="f" * 64,
                    dq_policy_ref="chembl.activity.dq",
                    rule_bundle_version="dq-rules.v1",
                    normalization_profile_ref=None,
                    normalization_profile_version=None,
                    normalization_profile_hash=None,
                    required_persistence_profile="degraded_observable",
                ),
                None,
            ),
        ):
            bootstrap_pipeline_runner(ctx)

        # Verify runtime config was passed with YAML values
        call_args = mock_factory.create_runner.call_args
        request = call_args[0][0] if call_args[0] else call_args.kwargs.get("request")
        runtime = request.runtime if hasattr(request, "runtime") else None
        assert runtime is not None
        assert runtime.vacuum_after_run is True
        assert runtime.vacuum_retention_days == 14

    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.create_registry")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.assemble_filter_config"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.create_pipeline_config_loader"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.bootstrap_observability_bundle"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.get_settings")
    def test_bootstrap_cli_vacuum_overrides_yaml_config(
        self,
        mock_get_settings: MagicMock,
        mock_bootstrap_observability_bundle: MagicMock,
        mock_create_pipeline_loader: MagicMock,
        mock_assemble_filter: MagicMock,
        mock_create_registry: MagicMock,
    ) -> None:
        """Test that CLI vacuum options override YAML config."""
        from bioetl.composition.bootstrap.runtime.pipeline import (
            bootstrap_pipeline_runner,
        )

        settings = _create_bootstrap_settings()
        settings.pipeline.control_plane.required_persistence_profile = (
            "degraded_observable"
        )
        mock_get_settings.return_value = settings

        mock_bootstrap_observability_bundle.return_value = (
            _create_observability_bundle()
        )
        mock_assemble_filter.return_value = None

        mock_pipeline_loader = MagicMock()
        mock_pipeline_loader.return_value = _create_pipeline_yaml_config(
            auto_vacuum=True,
            retention_days=14,
        )
        mock_create_pipeline_loader.return_value = mock_pipeline_loader

        _, mock_factory, _ = _configure_registry_with_runner(mock_create_registry)

        # Context with CLI overrides (explicit enabled=True and 30 days)
        # Note: enabled=True means CLI is overriding, so its retention_days is used
        ctx = _create_pipeline_context(
            vacuum=VacuumSettings(enabled=True, retention_days=30)
        )

        with patch(
            "bioetl.composition.runtime_builders.runner_builder.create_run_manifest_with_effective_config",
            return_value=(
                SimpleNamespace(
                    manifest_id="manifest-test-2",
                    execution_fingerprint="fp-test-2",
                    config_hash="d" * 64,
                    resolved_config_hash="e" * 64,
                    effective_config_hash="f" * 64,
                    source_fingerprint="0" * 64,
                    dq_contract_compatibility_hash="1" * 64,
                    effective_config_artifact_id="eca-2",
                    contract_ref="chembl.activity",
                    contract_version="1.0.0",
                    contract_schema_hash="2" * 64,
                    dq_policy_ref="chembl.activity.dq",
                    rule_bundle_version="dq-rules.v1",
                    normalization_profile_ref=None,
                    normalization_profile_version=None,
                    normalization_profile_hash=None,
                    required_persistence_profile="degraded_observable",
                ),
                None,
            ),
        ):
            bootstrap_pipeline_runner(ctx)

        # Verify runtime config was passed with CLI values (overriding YAML)
        call_args = mock_factory.create_runner.call_args
        request = call_args[0][0] if call_args[0] else call_args.kwargs.get("request")
        runtime = request.runtime if hasattr(request, "runtime") else None
        assert runtime is not None
        assert runtime.vacuum_after_run is True  # CLI enabled=True
        assert runtime.vacuum_retention_days == 30
