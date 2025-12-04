"""
Tests for the CLI entry point.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

# Avoid optional dependency import errors during tests
# Must be before importing bioetl modules that may use tqdm
sys.modules.setdefault("tqdm", MagicMock())

from bioetl.application.pipelines.base import PipelineBase  # noqa: E402
from bioetl.domain.transform.hash_service import HashService  # noqa: E402
from bioetl.interfaces.cli import app  # noqa: E402
from bioetl.infrastructure.config.models import PipelineConfig  # noqa: E402
from bioetl.schemas.provider_config_schema import ChemblSourceConfig  # noqa: E402

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
    assert "Config validation failed" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.load_pipeline_config_from_path")
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
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
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
@patch("bioetl.interfaces.cli.app.load_pipeline_config_from_path")
def test_run_command(mock_loader, mock_orchestrator_cls):
    """Test the run command."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_pipeline.return_value = MagicMock(
        success=True, row_count=10, duration_sec=1.0
    )
    mock_orchestrator_cls.return_value = mock_orchestrator

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
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
        ),
    )
    mock_loader.return_value = mock_config

    # We need to mock file existence for config
    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(
            app, ["run", "test_pipeline", "--config", "test.yaml"]
        )

    assert result.exit_code == 0
    assert "Pipeline finished successfully" in result.stdout
    mock_orchestrator.run_pipeline.assert_called_once()


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.run")
def test_smoke_run(mock_run):
    """Test smoke-run command."""
    result = runner.invoke(app, ["smoke-run", "test_pipeline"])
    assert result.exit_code == 0
    mock_run.assert_called_with(
        "test_pipeline", profile="development", dry_run=True, limit=10
    )


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.load_pipeline_config_from_path")
def test_run_config_not_found_explicit(mock_loader):
    """Test run command with explicit config that doesn't exist."""
    mock_loader.side_effect = FileNotFoundError("No such file or directory")

    result = runner.invoke(
        app, ["run", "test_pipeline", "--config", "nonexistent.yaml"]
    )

    assert result.exit_code == 1
    assert "Config file not found" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.PipelineOrchestrator")
@patch("bioetl.interfaces.cli.app.load_pipeline_config_from_path")
def test_run_with_limit_and_dry_run(
    mock_loader, mock_orchestrator_cls
):
    """Test run command with limit and dry-run options."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_pipeline.return_value = MagicMock(
        success=True, row_count=5, duration_sec=0.5
    )
    mock_orchestrator_cls.return_value = mock_orchestrator

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
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
        ),
    )
    mock_loader.return_value = mock_config

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(
            app, ["run", "test_pipeline", "--limit", "5", "--dry-run"]
        )

    assert result.exit_code == 0
    mock_orchestrator.run_pipeline.assert_called_once()
    _, kwargs = mock_orchestrator.run_pipeline.call_args
    assert kwargs["limit"] == 5
    assert kwargs["dry_run"] is True


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.PipelineOrchestrator")
@patch("bioetl.interfaces.cli.app.load_pipeline_config_from_path")
def test_run_pipeline_failure(mock_loader, mock_orchestrator_cls):
    """Test run command when pipeline fails."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.run_pipeline.return_value = MagicMock(success=False)
    mock_orchestrator_cls.return_value = mock_orchestrator

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
            timeout_sec=30,
            max_retries=3,
            rate_limit_per_sec=10.0,
        ),
    )

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["run", "test_pipeline"])

    assert result.exit_code == 1
    assert "Pipeline failed!" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.load_pipeline_config_from_path")
def test_run_exception(mock_loader):
    """Test run command unhandled exception."""
    mock_loader.side_effect = RuntimeError("Unexpected error")

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["run", "test_pipeline"])

    assert result.exit_code == 1
    assert "Unexpected error" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.PipelineOrchestrator")
@patch("bioetl.interfaces.cli.app.load_pipeline_config_from_path")
def test_run_dry_run_pipeline_metadata(
    mock_loader,
    mock_orchestrator_cls,
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
            output_writer,
            hash_service: HashService,
            extraction_service=None,
        ):
            super().__init__(
                config,
                logger,
                validation_service,
                output_writer,
                hash_service,
            )
            self._dataset = small_pipeline_df
            self.last_result = None
            created_instances.append(self)

        def extract(self, **_):
            return self._dataset.copy()

        def transform(self, df):
            return df.assign(cli_processed=True)

        def run(self, *args, **kwargs):  # type: ignore[override]
            result = super().run(*args, **kwargs)
            self.last_result = result
            return result

    logger = MagicMock()
    logger.bind.return_value = logger
    validation_service = MagicMock()
    validation_service.validate.side_effect = lambda df, **__: df
    output_writer = MagicMock()
    output_writer.write_result.return_value = MagicMock(
        row_count=len(small_pipeline_df), checksum="checksum", path=MagicMock(name="dummy.parquet")
    )

    # Mock orchestrator to build and run our pipeline
    hash_service = HashService()

    def build_pipeline_side_effect(*args, **kwargs):
        pipeline_instance = DryRunPipeline(
            config=pipeline_test_config,
            logger=logger,
            validation_service=validation_service,
            output_writer=output_writer,
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

    with runner.isolated_filesystem():
        Path("config.yaml").write_text("dummy", encoding="utf-8")
        result = runner.invoke(
            app,
            ["run", "test_pipeline", "--config", "config.yaml", "--dry-run"],
        )

    assert result.exit_code == 0
    assert "Pipeline finished successfully" in result.stdout

    created_pipeline = created_instances[0]
    assert created_pipeline.last_result is not None
    stage_names = [stage.stage_name for stage in created_pipeline.last_result.stages]
    assert stage_names == ["extract", "transform", "validate"]
    assert created_pipeline.last_result.meta["dry_run"] is True
    assert created_pipeline.last_result.errors == []
