"""
Tests for the CLI entry point.
"""

from datetime import datetime, timezone
import importlib
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from typer.testing import CliRunner

# Avoid optional dependency import errors during tests.
# Must be executed before loading modules importing tqdm.
sys.modules.setdefault("tqdm", MagicMock())

PipelineBase = importlib.import_module("bioetl.application.pipelines.base").PipelineBase
LoaderABC = importlib.import_module("bioetl.domain.pipelines.contracts").LoaderABC
_configs = importlib.import_module("bioetl.domain.configs")
ChemblSourceConfig = _configs.ChemblSourceConfig
HttpClientConfig = _configs.HttpClientConfig
PipelineConfig = _configs.PipelineConfig
DataFlowConfig = _configs.DataFlowConfig
DataSinkConfig = _configs.DataSinkConfig
DataSourceConfig = _configs.DataSourceConfig
PipelineIdentityConfig = _configs.PipelineIdentityConfig
ProviderHttpConfig = _configs.ProviderHttpConfig
HashServiceABC = importlib.import_module(
    "bioetl.domain.transform.contracts"
).HashServiceABC
HashService = importlib.import_module(
    "bioetl.infrastructure.transform.impl.hash_service"
).Blake2bHashService
try:
    app = importlib.import_module("bioetl.interfaces.cli").app
except ModuleNotFoundError:
    import pytest

    pytest.skip("CLI module not available", allow_module_level=True)

runner = CliRunner()


@pytest.mark.unit
def test_list_pipelines():
    """Test listing pipelines."""
    result = runner.invoke(app, ["list-pipelines"])
    assert result.exit_code == 0
    assert "Available Pipelines" in result.stdout


@pytest.mark.unit
def test_validate_config_missing():
    """Test validate-config with missing file."""
    result = runner.invoke(app, ["validate-config", "nonexistent.yaml"])
    assert result.exit_code == 1
    assert "Config file not found" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.build_runtime_config")
def test_validate_config_success(mock_loader):
    """Test validate-config success."""
    from bioetl.domain.configs import (
        DataFlowConfig,
        DataSinkConfig,
        DataSourceConfig,
        PipelineIdentityConfig,
    )
    from bioetl.domain.configs.pipeline import ProviderHttpConfig

    mock_loader.return_value = PipelineConfig(
        identity=PipelineIdentityConfig(
            pipeline_id="chembl.test",
            provider="chembl",
            entity="test",
        ),
        data_flow=DataFlowConfig(
            source=DataSourceConfig(
                input_mode="auto_detect",
                input_path=None,
                batch_size=10,
            ),
            sink=DataSinkConfig(output_path="./out"),
        ),
        provider_config=ChemblSourceConfig(
            http=ProviderHttpConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )

    # Create a dummy file so Path exists check passes if any
    with runner.isolated_filesystem():
        with open("config.yaml", "w", encoding="utf-8") as f:
            f.write("dummy")

        result = runner.invoke(app, ["validate-config", "config.yaml"])
        assert result.exit_code == 0
        assert "valid" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_application_context")
@patch("bioetl.interfaces.cli.app._resolve_config_path")
def test_run_command(mock_resolve, mock_get_factory):
    """Test the run command."""
    mock_resolve.return_value = Path("test.yaml")
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = MagicMock(
        success=True, row_count=10, duration_sec=1.0, output_path="out", errors=[]
    )
    mock_context = mock_get_factory.return_value
    mock_context.use_case_factory.create_run_pipeline_use_case.return_value = (
        mock_use_case
    )

    result = runner.invoke(app, ["run", "activity_chembl", "--config", "test.yaml"])

    assert result.exit_code == 0
    assert "Pipeline finished successfully" in result.stdout
    mock_use_case.execute.assert_called_once()

    args = mock_use_case.execute.call_args[0]
    request = args[0]
    assert request.pipeline_name == "activity_chembl"
    assert request.config_path == Path("test.yaml")


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.run")
def test_smoke_run(mock_run):
    """Test smoke-run command."""
    result = runner.invoke(app, ["smoke-run", "activity_chembl"])
    assert result.exit_code == 0
    mock_run.assert_called_with(
        pipeline_name="activity_chembl",
        config=None,
        limit=10,
        dry_run=True,
        profile="development",
    )


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_application_context")
def test_run_config_not_found_explicit(mock_get_factory):
    """Test run command with explicit config that doesn't exist.

    Simulated via UseCase.
    """
    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = FileNotFoundError("Config file not found")
    mock_context = mock_get_factory.return_value
    mock_context.use_case_factory.create_run_pipeline_use_case.return_value = (
        mock_use_case
    )

    result = runner.invoke(
        app, ["run", "activity_chembl", "--config", "nonexistent.yaml"]
    )

    assert result.exit_code == 1
    assert "Config file not found" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_application_context")
def test_run_with_limit_and_dry_run(mock_get_factory):
    """Test run command with limit and dry-run options."""
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = MagicMock(
        success=True, row_count=5, duration_sec=0.5, output_path="out", errors=[]
    )
    mock_context = mock_get_factory.return_value
    mock_context.use_case_factory.create_run_pipeline_use_case.return_value = (
        mock_use_case
    )

    result = runner.invoke(app, ["run", "activity_chembl", "--limit", "5", "--dry-run"])

    assert result.exit_code == 0
    mock_use_case.execute.assert_called_once()

    args = mock_use_case.execute.call_args[0]
    request = args[0]
    assert request.limit == 5
    assert request.dry_run is True


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_application_context")
def test_run_pipeline_failure(mock_get_factory):
    """Test run command when pipeline fails."""
    mock_use_case = MagicMock()
    mock_use_case.execute.return_value = MagicMock(success=False, errors=["Error 1"])
    mock_context = mock_get_factory.return_value
    mock_context.use_case_factory.create_run_pipeline_use_case.return_value = (
        mock_use_case
    )

    result = runner.invoke(app, ["run", "activity_chembl"])

    assert result.exit_code == 1
    assert "Pipeline failed" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_application_context")
def test_run_exception(mock_get_factory):
    """Test run command unhandled exception."""
    mock_use_case = MagicMock()
    mock_use_case.execute.side_effect = RuntimeError("Unexpected error")
    mock_context = mock_get_factory.return_value
    mock_context.use_case_factory.create_run_pipeline_use_case.return_value = (
        mock_use_case
    )

    result = runner.invoke(app, ["run", "activity_chembl"])

    assert result.exit_code == 1
    assert "Unexpected error" in result.stdout


@pytest.mark.unit
@patch("bioetl.infrastructure.config.provider_registry.create_provider_loader")
@patch("bioetl.application.use_cases.run_pipeline.PipelineOrchestrator")
@patch("bioetl.application.use_cases.run_pipeline.RunPipelineUseCase._load_config")
def test_run_dry_run_pipeline_metadata(
    mock_load_config,
    mock_orchestrator_cls,
    mock_create_provider_loader,
    pipeline_test_config,
    small_pipeline_df,
):
    """Dry-run via CLI preserves stage info and metadata."""

    # We patch UseCase internals to facilitate this integration-like test
    # without full context
    mock_load_config.return_value = pipeline_test_config

    created_instances: list[PipelineBase] = []

    IndexGeneratorABC = importlib.import_module(
        "bioetl.domain.transform.contracts"
    ).IndexGeneratorABC
    TimestampProviderABC = importlib.import_module(
        "bioetl.domain.transform.contracts"
    ).TimestampProviderABC

    class DryRunPipeline(PipelineBase):
        def __init__(
            self,
            config,
            logger,
            validation_service,
            loader,
            hash_service: HashServiceABC,
            index_generator: IndexGeneratorABC,
            timestamp_provider: TimestampProviderABC,
            extraction_service=None,
        ):
            super().__init__(
                config,
                logger,
                validation_service,
                loader,
                hash_service,
                index_generator,
                timestamp_provider,
            )
            self._dataset = small_pipeline_df
            self.last_result = None
            self._loader = loader
            created_instances.append(self)

        def extract(self, **_):
            return self._dataset.copy()

        def transform(self, df):
            return df.assign(cli_processed=True)

        def write(self, df, output_path, context):
            return self._loader.load(df, output_path, context)

        def run(self, *args, **kwargs):  # type: ignore[override]
            result = super().run(*args, **kwargs)
            self.last_result = result
            return result

    logger = MagicMock()
    logger.apply_bind.return_value = logger
    validation_service = MagicMock()
    validation_service.validate.side_effect = lambda df, **__: df

    # Mock schema to have columns
    mock_schema = MagicMock()
    mock_schema.columns = {"col1": MagicMock()}
    validation_service.get_schema.return_value = mock_schema

    loader = MagicMock(spec=LoaderABC)
    loader.load.return_value = MagicMock(
        row_count=len(small_pipeline_df),
        checksum="checksum",
        path=MagicMock(name="dummy.parquet"),
    )

    class _DummyHasher:
        def compute_hash_row(self, _row):
            return "hash_row"

        def compute_hash_columns(self, df, _columns):
            return pd.Series(["hash_business_key"] * len(df))

    # Mock orchestrator to build and run our pipeline
    hash_service = HashService(hasher=_DummyHasher())
    index_generator = MagicMock(spec=IndexGeneratorABC)
    index_generator.next_index.side_effect = range(1000)
    timestamp_provider = MagicMock(spec=TimestampProviderABC)
    timestamp_provider.get_extraction_timestamp.return_value = datetime(
        2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc
    )

    def build_pipeline_side_effect(*args, **kwargs):
        pipeline_instance = DryRunPipeline(
            config=pipeline_test_config,
            logger=logger,
            validation_service=validation_service,
            loader=loader,
            hash_service=hash_service,
            index_generator=index_generator,
            timestamp_provider=timestamp_provider,
        )
        return pipeline_instance

    def run_pipeline_side_effect(*args, **kwargs):
        pipeline_instance = build_pipeline_side_effect()
        return pipeline_instance.run(
            output_path=Path(pipeline_test_config.sink.output_path),
            dry_run=kwargs.get("dry_run", False),
        )

    mock_orchestrator = MagicMock()
    mock_orchestrator.build_pipeline.side_effect = build_pipeline_side_effect
    mock_orchestrator.run_pipeline.side_effect = run_pipeline_side_effect
    mock_orchestrator_cls.return_value = mock_orchestrator

    provider_loader = MagicMock()
    provider_loader.get_registry.return_value = MagicMock()
    mock_create_provider_loader.return_value = provider_loader

    # Mock the resolver - no longer needed as we mock _load_config
    # mock_resolve_path.return_value = Path("config.yaml")

    with runner.isolated_filesystem():
        Path("config.yaml").write_text("dummy", encoding="utf-8")
        result = runner.invoke(
            app,
            ["run", "activity_chembl", "--config", "config.yaml", "--dry-run"],
        )

    if result.exit_code != 0:
        print(result.stdout)
        print(result.exc_info)

    assert result.exit_code == 0
    assert "Pipeline finished successfully" in result.stdout

    created_pipeline = created_instances[0]
    assert created_pipeline.last_result is not None
    stage_names = [
        str(stage.stage_name) for stage in created_pipeline.last_result.stages
    ]
    assert stage_names == ["extract", "transform", "validate"]
    assert created_pipeline.last_result.meta["dry_run"] is True
    assert created_pipeline.last_result.errors == []
