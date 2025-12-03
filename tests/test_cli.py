"""
Tests for the CLI entry point.
"""
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bioetl.interfaces.cli import app

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
@patch("bioetl.interfaces.cli.app.ConfigResolver")
def test_validate_config_success(mock_resolver):
    """Test validate-config success."""
    mock_config = MagicMock()
    mock_config.entity_name = "test"
    mock_config.provider = "chembl"
    mock_resolver.return_value.resolve.return_value = mock_config

    # Create a dummy file so Path exists check passes if any
    with runner.isolated_filesystem():
        with open("config.yaml", "w", encoding="utf-8") as f:
            f.write("dummy")

        result = runner.invoke(app, ["validate-config", "config.yaml"])
        assert result.exit_code == 0
        assert "valid" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_pipeline_class")
@patch("bioetl.interfaces.cli.app.ConfigResolver")
@patch("bioetl.interfaces.cli.app.build_pipeline_dependencies")
def test_run_command(mock_build_deps, mock_resolver, mock_get_cls):
    """Test the run command."""
    mock_pipeline_cls = MagicMock()
    mock_pipeline_instance = mock_pipeline_cls.return_value
    mock_pipeline_instance.run.return_value = MagicMock(
        success=True, row_count=10, duration_sec=1.0
    )
    mock_get_cls.return_value = mock_pipeline_cls

    mock_config = MagicMock()
    mock_config.provider = "chembl"
    mock_config.storage.output_path = "out"
    mock_resolver.return_value.resolve.return_value = mock_config

    # Mock container
    mock_container = MagicMock()
    mock_build_deps.return_value = mock_container

    # We need to mock file existence for config
    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(
            app, ["run", "test_pipeline", "--config", "test.yaml"]
        )

    assert result.exit_code == 0
    assert "Pipeline finished successfully" in result.stdout
    mock_pipeline_instance.run.assert_called_once()
    # Verify container was used
    mock_container.get_logger.assert_called_once()


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
@patch("bioetl.interfaces.cli.app.get_pipeline_class")
@patch("bioetl.interfaces.cli.app.ConfigResolver")
def test_run_config_not_found_explicit(mock_resolver, mock_get_cls):
    """Test run command with explicit config that doesn't exist."""
    mock_get_cls.return_value = MagicMock()
    mock_resolver.return_value.resolve.side_effect = FileNotFoundError(
        "No such file or directory"
    )

    result = runner.invoke(
        app, ["run", "test_pipeline", "--config", "nonexistent.yaml"]
    )

    assert result.exit_code == 1
    # The app catches exception and prints "Error: ..."
    assert "Error:" in result.stdout
    assert "No such file or directory" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_pipeline_class")
@patch("bioetl.interfaces.cli.app.ConfigResolver")
@patch("bioetl.interfaces.cli.app.build_pipeline_dependencies")
def test_run_with_limit_and_dry_run(
    mock_build_deps, mock_resolver, mock_get_cls
):
    """Test run command with limit and dry-run options."""
    mock_pipeline_cls = MagicMock()
    mock_pipeline_instance = mock_pipeline_cls.return_value
    mock_pipeline_instance.run.return_value = MagicMock(
        success=True, row_count=5, duration_sec=0.5
    )
    mock_get_cls.return_value = mock_pipeline_cls

    mock_config = MagicMock()
    mock_config.provider = "chembl"
    mock_config.storage.output_path = "out"
    mock_resolver.return_value.resolve.return_value = mock_config
    mock_build_deps.return_value = MagicMock()

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(
            app, ["run", "test_pipeline", "--limit", "5", "--dry-run"]
        )

    assert result.exit_code == 0
    mock_pipeline_instance.run.assert_called_once()
    _, kwargs = mock_pipeline_instance.run.call_args
    assert kwargs["limit"] == 5
    assert kwargs["dry_run"] is True


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_pipeline_class")
@patch("bioetl.interfaces.cli.app.ConfigResolver")
@patch("bioetl.interfaces.cli.app.build_pipeline_dependencies")
def test_run_pipeline_failure(mock_build_deps, mock_resolver, mock_get_cls):
    """Test run command when pipeline fails."""
    mock_pipeline_cls = MagicMock()
    mock_pipeline_instance = mock_pipeline_cls.return_value
    mock_pipeline_instance.run.return_value = MagicMock(success=False)
    mock_get_cls.return_value = mock_pipeline_cls

    mock_resolver.return_value.resolve.return_value = MagicMock()
    mock_build_deps.return_value = MagicMock()

    with patch("pathlib.Path.exists", return_value=True):
        result = runner.invoke(app, ["run", "test_pipeline"])

    assert result.exit_code == 1
    assert "Pipeline failed!" in result.stdout


@pytest.mark.unit
@patch("bioetl.interfaces.cli.app.get_pipeline_class")
def test_run_exception(mock_get_cls):
    """Test run command unhandled exception."""
    mock_get_cls.side_effect = RuntimeError("Unexpected error")

    result = runner.invoke(app, ["run", "test_pipeline"])

    assert result.exit_code == 1
    assert "Error:" in result.stdout
    assert "Unexpected error" in result.stdout
