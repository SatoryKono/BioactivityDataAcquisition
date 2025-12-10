"""
Tests for the CLI entry point.
"""

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
LoaderABC = importlib.import_module("bioetl.application.pipelines.contracts").LoaderABC
_configs = importlib.import_module("bioetl.domain.configs")
ChemblSourceConfig = _configs.ChemblSourceConfig
ClientConfig = _configs.ClientConfig
PipelineConfig = _configs.PipelineConfig
HashServiceABC = importlib.import_module(
    "bioetl.domain.transform.contracts"
).HashServiceABC
HashService = importlib.import_module(
    "bioetl.domain.transform.hash_service"
).HashService
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
@patch("bioetl.interfaces.cli.app.build_pipeline_config")
def test_validate_config_success(mock_loader):
    """Test validate-config success."""
    mock_loader.return_value = PipelineConfig(
        id="chembl.test",
        provider="chembl",
        entity="test",
        input_mode="auto_detect",
        input_path=None,
        output_path="./out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            client=ClientConfig(
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
@patch("bioetl.interfaces.cli.app.PipelineOrchestrator")
@patch("bioetl.interfaces.cli.app.build_pipeline_config")
@patch("bioetl.interfaces.cli.app.ConfigPathResolver")
def test_run_command(mock_resolver_cls, mock_loader, mock_orchestrator_cls):
    """Test the run command."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_pipeline.return_value = MagicMock(
        success=True, row_count=10, duration_sec=1.0
    )
    mock_orchestrator_cls.return_value = mock_orchestrator

    # Mock the resolver
    mock_resolver = MagicMock()
    mock_resolver.resolve_config_path.return_value = Path("test.yaml")
    mock_resolver_cls.return_value = mock_resolver

    mock_config = PipelineConfig(
        id="chembl.activity",
        provider="chembl",
        entity="activity",
        input_mode="auto_detect",
        input_path=None,
        output_path="out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )
    mock_loader.return_value = mock_config

    # We need to mock file existence for config
    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["run", "activity_chembl", "--config", "test.yaml"])

    assert result.exit_code == 0
    assert "Pipeline finished successfully" in result.stdout
    mock_orchestrator.run_pipeline.assert_called_once()


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
@patch("bioetl.interfaces.cli.app.ConfigPathResolver")
def test_run_config_not_found_explicit(mock_resolver_cls):
    """Test run command with explicit config that doesn't exist."""
    mock_resolver = MagicMock()
    mock_resolver.resolve_config_path.side_effect = FileNotFoundError(
        "Config file not found: nonexistent.yaml"
    )
    mock_resolver_cls.return_value = mock_resolver

    result = runner.invoke(
        app, ["run", "activity_chembl", "--config", "nonexistent.yaml"]
    )

    assert result.exit_code == 1
    assert "Config file not found" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.PipelineOrchestrator")
@patch("bioetl.interfaces.cli.app.build_pipeline_config")
@patch("bioetl.interfaces.cli.app.ConfigPathResolver")
def test_run_with_limit_and_dry_run(mock_resolver_cls, mock_loader, mock_orchestrator_cls):
    """Test run command with limit and dry-run options."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_pipeline.return_value = MagicMock(
        success=True, row_count=5, duration_sec=0.5
    )
    mock_orchestrator_cls.return_value = mock_orchestrator

    # Mock the resolver
    mock_resolver = MagicMock()
    mock_resolver.resolve_config_path.return_value = Path("inferred.yaml")
    mock_resolver_cls.return_value = mock_resolver

    mock_config = PipelineConfig(
        id="chembl.activity",
        provider="chembl",
        entity="activity",
        input_mode="auto_detect",
        input_path=None,
        output_path="out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )
    mock_loader.return_value = mock_config

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(
            app, ["run", "activity_chembl", "--limit", "5", "--dry-run"]
        )

    assert result.exit_code == 0
    mock_orchestrator.run_pipeline.assert_called_once()
    _, kwargs = mock_orchestrator.run_pipeline.call_args
    assert kwargs["limit"] == 5
    assert kwargs["dry_run"] is True


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.PipelineOrchestrator")
@patch("bioetl.interfaces.cli.app.build_pipeline_config")
@patch("bioetl.interfaces.cli.app.ConfigPathResolver")
def test_run_pipeline_failure(mock_resolver_cls, mock_loader, mock_orchestrator_cls):
    """Test run command when pipeline fails."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_pipeline.return_value = MagicMock(success=False)
    mock_orchestrator_cls.return_value = mock_orchestrator

    # Mock the resolver
    mock_resolver = MagicMock()
    mock_resolver.resolve_config_path.return_value = Path("inferred.yaml")
    mock_resolver_cls.return_value = mock_resolver

    mock_loader.return_value = PipelineConfig(
        id="chembl.activity",
        provider="chembl",
        entity="activity",
        input_mode="auto_detect",
        input_path=None,
        output_path="out",
        batch_size=10,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["run", "activity_chembl"])

    assert result.exit_code == 1
    assert "Pipeline failed" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.build_pipeline_config")
@patch("bioetl.interfaces.cli.app.ConfigPathResolver")
def test_run_exception(mock_resolver_cls, mock_loader):
    """Test run command unhandled exception."""
    # Mock the resolver
    mock_resolver = MagicMock()
    mock_resolver.resolve_config_path.return_value = Path("inferred.yaml")
    mock_resolver_cls.return_value = mock_resolver

    mock_loader.side_effect = RuntimeError("Unexpected error")

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["run", "activity_chembl"])

    assert result.exit_code == 1
    assert "Unexpected error" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.create_provider_loader")
@patch("bioetl.interfaces.cli.app.PipelineOrchestrator")
@patch("bioetl.interfaces.cli.app.build_pipeline_config")
@patch("bioetl.interfaces.cli.app.ConfigPathResolver")
def test_run_dry_run_pipeline_metadata(
    mock_resolver_cls,
    mock_loader,
    mock_orchestrator_cls,
    mock_create_provider_loader,
    pipeline_test_config,
    small_pipeline_df,
):
    """Dry-run via CLI preserves stage info and metadata."""

    created_instances: list[PipelineBase] = []

    class DryRunPipeline(PipelineBase):
        def __init__(
            self,
            config,
            logger,
            validation_service,
            loader,
            hash_service: HashServiceABC,
            extraction_service=None,
        ):
            super().__init__(
                config,
                logger,
                validation_service,
                loader,
                hash_service,
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

    def build_pipeline_side_effect(*args, **kwargs):
        pipeline_instance = DryRunPipeline(
            config=pipeline_test_config,
            logger=logger,
            validation_service=validation_service,
            loader=loader,
            hash_service=hash_service,
        )
        return pipeline_instance

    def run_pipeline_side_effect(*args, **kwargs):
        pipeline_instance = build_pipeline_side_effect()
        return pipeline_instance.run(
            output_path=Path(pipeline_test_config.output_path),
            dry_run=kwargs.get("dry_run", False),
        )

    mock_orchestrator = MagicMock()
    mock_orchestrator.build_pipeline.side_effect = build_pipeline_side_effect
    mock_orchestrator.run_pipeline.side_effect = run_pipeline_side_effect
    mock_orchestrator_cls.return_value = mock_orchestrator

    mock_loader.return_value = pipeline_test_config
    provider_loader = MagicMock()
    provider_loader.get_registry.return_value = MagicMock()
    mock_create_provider_loader.return_value = provider_loader

    # Mock the resolver
    mock_resolver = MagicMock()
    mock_resolver.resolve_config_path.return_value = Path("config.yaml")
    mock_resolver_cls.return_value = mock_resolver

    with runner.isolated_filesystem():
        Path("config.yaml").write_text("dummy", encoding="utf-8")
        result = runner.invoke(
            app,
            ["run", "activity_chembl", "--config", "config.yaml", "--dry-run"],
        )

    assert result.exit_code == 0
    assert "Pipeline finished successfully" in result.stdout

    created_pipeline = created_instances[0]
    assert created_pipeline.last_result is not None
    stage_names = [stage.stage_name for stage in created_pipeline.last_result.stages]
    assert stage_names == ["extract", "transform", "validate"]
    assert created_pipeline.last_result.meta["dry_run"] is True
    assert created_pipeline.last_result.errors == []
