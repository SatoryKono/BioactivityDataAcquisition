"""Unit tests for run-all CLI command.

Tests for the universal run-all command that runs all pipelines for a provider.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.services import RunResult, RunStatus
from bioetl.interfaces.cli.commands.run_all import (
    BatchRunResult,
    _filter_pipelines_by_provider,
    _get_available_providers,
    _validate_provider,
)
from bioetl.interfaces.cli.main import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_registry():
    """Mock default registry for validation tests."""
    mock = MagicMock()
    mock.list_pipelines.return_value = [
        "chembl_activity",
        "chembl_assay",
        "chembl_molecule",
        "chembl_target",
        "pubchem_compound",
        "uniprot_protein",
    ]
    with patch(
        "bioetl.interfaces.cli.commands.run_all.get_default_registry",
        return_value=mock,
    ):
        yield mock


@pytest.fixture
def mock_registry_main():
    """Mock default registry for main.py imports."""
    mock = MagicMock()
    mock.list_pipelines.return_value = [
        "chembl_activity",
        "chembl_assay",
        "chembl_molecule",
        "chembl_target",
        "pubchem_compound",
        "uniprot_protein",
    ]
    with patch(
        "bioetl.interfaces.cli.commands.run_helpers.get_default_registry",
        return_value=mock,
    ):
        yield mock


# =============================================================================
# BatchRunResult tests
# =============================================================================


@pytest.mark.unit
class TestBatchRunResult:
    """Tests for BatchRunResult dataclass."""

    def test_all_succeeded_true_when_no_failures(self):
        """Test all_succeeded is True when no failures."""
        result = BatchRunResult(total=3, succeeded=3, failed=0)
        assert result.all_succeeded is True

    def test_all_succeeded_false_when_failures(self):
        """Test all_succeeded is False when there are failures."""
        result = BatchRunResult(total=3, succeeded=2, failed=1)
        assert result.all_succeeded is False

    def test_all_succeeded_false_when_zero_total(self):
        """Test all_succeeded is False when no pipelines processed."""
        result = BatchRunResult(total=0, succeeded=0, failed=0)
        assert result.all_succeeded is False

    def test_default_values(self):
        """Test default values are initialized correctly."""
        result = BatchRunResult()
        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.results == []
        assert result.failed_pipelines == []


# =============================================================================
# Helper function tests
# =============================================================================


@pytest.mark.unit
class TestGetAvailableProviders:
    """Tests for _get_available_providers function."""

    def test_returns_unique_providers(self, mock_registry):
        """Test that unique providers are extracted from pipeline names."""
        providers = _get_available_providers()
        assert sorted(providers) == ["chembl", "pubchem", "uniprot"]

    def test_empty_when_no_pipelines(self):
        """Test that empty list returned when no pipelines registered."""
        mock = MagicMock()
        mock.list_pipelines.return_value = []
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock,
        ):
            providers = _get_available_providers()
            assert providers == []


@pytest.mark.unit
class TestFilterPipelinesByProvider:
    """Tests for _filter_pipelines_by_provider function."""

    def test_filters_chembl_pipelines(self, mock_registry):
        """Test that ChEMBL pipelines are correctly filtered."""
        pipelines = _filter_pipelines_by_provider("chembl")
        assert pipelines == [
            "chembl_activity",
            "chembl_assay",
            "chembl_molecule",
            "chembl_target",
        ]

    def test_filters_pubchem_pipelines(self, mock_registry):
        """Test that PubChem pipelines are correctly filtered."""
        pipelines = _filter_pipelines_by_provider("pubchem")
        assert pipelines == ["pubchem_compound"]

    def test_returns_empty_for_unknown_provider(self, mock_registry):
        """Test that empty list returned for unknown provider."""
        pipelines = _filter_pipelines_by_provider("unknown")
        assert pipelines == []


@pytest.mark.unit
class TestValidateProvider:
    """Tests for _validate_provider function."""

    def test_valid_provider_returns_true(self, mock_registry):
        """Test that valid provider returns (True, None)."""
        is_valid, error = _validate_provider("chembl")
        assert is_valid is True
        assert error is None

    def test_invalid_provider_returns_false(self, mock_registry):
        """Test that invalid provider returns (False, error_message)."""
        is_valid, error = _validate_provider("invalid")
        assert is_valid is False
        assert "No pipelines found for provider 'invalid'" in error
        assert "Available providers:" in error

    def test_empty_registry_returns_error(self):
        """Test that empty registry returns appropriate error."""
        mock = MagicMock()
        mock.list_pipelines.return_value = []
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock,
        ):
            is_valid, error = _validate_provider("chembl")
            assert is_valid is False
            assert "No pipelines are registered" in error


# =============================================================================
# CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllCommand:
    """Tests for run-all Click command."""

    def test_run_all_help(self, cli_runner):
        """Test that run-all --help works."""
        result = cli_runner.invoke(cli, ["run-all", "--help"])
        assert result.exit_code == 0
        assert "--source" in result.output
        assert "--run-type" in result.output
        assert "--list-only" in result.output
        assert "--dry-run" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_all_requires_source(self, mock_register, cli_runner):
        """Test that --source is required."""
        result = cli_runner.invoke(cli, ["run-all"])
        assert result.exit_code != 0
        assert "Missing option '--source'" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_all_list_only_shows_pipelines(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that --list-only shows pipelines without executing."""
        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--list-only"]
        )
        assert result.exit_code == 0
        assert "Pipelines for provider 'chembl':" in result.output
        assert "chembl_activity" in result.output
        assert "chembl_assay" in result.output
        assert "Total: 4 pipeline(s)" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_all_invalid_source_fails(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that invalid source shows error and exits with code 1."""
        result = cli_runner.invoke(cli, ["run-all", "--source", "invalid"])
        assert result.exit_code == 1
        assert "No pipelines found for provider 'invalid'" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_executes_all_pipelines(
        self, mock_asyncio, mock_get_service, mock_register, cli_runner, mock_registry
    ):
        """Test that all pipelines for source are executed."""
        # Setup mock service
        mock_service = MagicMock()

        async def mock_run(pipeline, options=None):
            return RunResult(
                status=RunStatus.SUCCESS,
                pipeline_name=pipeline,
                run_id="test-run-id",
                run_type="incremental",
            )

        mock_service.run = AsyncMock(side_effect=mock_run)
        mock_get_service.return_value = mock_service

        # Make asyncio.run execute the coroutine
        def run_coro(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_asyncio.side_effect = run_coro

        result = cli_runner.invoke(cli, ["run-all", "--source", "chembl"])

        # Should have called the service for each chembl pipeline
        assert mock_service.run.call_count == 4
        assert "Running 4 pipeline(s)" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_dry_run_mode(
        self, mock_asyncio, mock_get_service, mock_register, cli_runner, mock_registry
    ):
        """Test that --dry-run mode shows pipelines without executing."""
        # Setup mock service
        mock_service = MagicMock()

        async def mock_run(pipeline, options=None):
            return RunResult(
                status=RunStatus.DRY_RUN,
                pipeline_name=pipeline,
                run_id="test-run-id",
                run_type="incremental",
            )

        mock_service.run = AsyncMock(side_effect=mock_run)
        mock_get_service.return_value = mock_service

        # Make asyncio.run execute the coroutine
        def run_coro(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_asyncio.side_effect = run_coro

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--dry-run"]
        )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_all_rebuild_requires_confirmation(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that rebuild requires confirmation without --yes."""
        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--run-type", "rebuild"],
            input="n\n",  # Say no to confirmation
        )

        assert "Operation cancelled" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_rebuild_with_yes_skips_confirmation(
        self, mock_asyncio, mock_get_service, mock_register, cli_runner, mock_registry
    ):
        """Test that --yes skips confirmation for rebuild."""
        mock_service = MagicMock()

        async def mock_run(pipeline, options=None):
            return RunResult(
                status=RunStatus.SUCCESS,
                pipeline_name=pipeline,
                run_id="test-run-id",
                run_type="rebuild",
            )

        mock_service.run = AsyncMock(side_effect=mock_run)
        mock_get_service.return_value = mock_service

        def run_coro(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_asyncio.side_effect = run_coro

        cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--run-type", "rebuild", "--yes"]
        )

        # Should have called the service (no confirmation prompt)
        assert mock_service.run.call_count == 4


# =============================================================================
# Deprecated run-chembl-all Command Tests
# =============================================================================


@pytest.mark.unit
class TestRunChemblAllCommand:
    """Tests for deprecated run-chembl-all command."""

    def test_run_chembl_all_help(self, cli_runner):
        """Test that run-chembl-all --help works."""
        result = cli_runner.invoke(cli, ["run-chembl-all", "--help"])
        assert result.exit_code == 0
        assert "DEPRECATED" in result.output
        assert "run-all --source chembl" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_chembl_all_shows_deprecation_warning(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that run-chembl-all shows deprecation warning."""
        result = cli_runner.invoke(cli, ["run-chembl-all", "--list-only"])

        assert "DEPRECATION" in result.output
        assert "run-all --source chembl" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_chembl_all_list_only_works(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that run-chembl-all --list-only shows chembl pipelines."""
        result = cli_runner.invoke(cli, ["run-chembl-all", "--list-only"])

        assert result.exit_code == 0
        assert "chembl_activity" in result.output
        assert "Total: 4 pipeline(s)" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_chembl_all_delegates_to_run_all(
        self, mock_asyncio, mock_get_service, mock_register, cli_runner, mock_registry
    ):
        """Test that run-chembl-all delegates to run-all with source=chembl."""
        mock_service = MagicMock()

        async def mock_run(pipeline, options=None):
            return RunResult(
                status=RunStatus.SUCCESS,
                pipeline_name=pipeline,
                run_id="test-run-id",
                run_type="incremental",
            )

        mock_service.run = AsyncMock(side_effect=mock_run)
        mock_get_service.return_value = mock_service

        def run_coro(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_asyncio.side_effect = run_coro

        cli_runner.invoke(cli, ["run-chembl-all"])

        # Should have called all chembl pipelines
        assert mock_service.run.call_count == 4


# =============================================================================
# Exit Code Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllExitCodes:
    """Tests for run-all exit codes."""

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_exit_code_0_for_list_only(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test exit code 0 for successful --list-only."""
        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--list-only"]
        )
        assert result.exit_code == 0

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_exit_code_1_for_invalid_source(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test exit code 1 for invalid source."""
        result = cli_runner.invoke(cli, ["run-all", "--source", "invalid"])
        assert result.exit_code == 1

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_exit_code_0_for_all_success(
        self, mock_asyncio, mock_get_service, mock_register, cli_runner, mock_registry
    ):
        """Test exit code 0 when all pipelines succeed."""
        mock_service = MagicMock()

        async def mock_run(pipeline, options=None):
            return RunResult(
                status=RunStatus.SUCCESS,
                pipeline_name=pipeline,
                run_id="test-run-id",
                run_type="incremental",
            )

        mock_service.run = AsyncMock(side_effect=mock_run)
        mock_get_service.return_value = mock_service

        def run_coro(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_asyncio.side_effect = run_coro

        result = cli_runner.invoke(cli, ["run-all", "--source", "chembl"])
        assert result.exit_code == 0

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_exit_code_82_for_failures(
        self, mock_asyncio, mock_get_service, mock_register, cli_runner, mock_registry
    ):
        """Test exit code 82 (PIPELINE_ERROR) when some pipelines fail."""
        mock_service = MagicMock()
        call_count = 0

        async def mock_run(pipeline, options=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                # Second pipeline fails
                return RunResult(
                    status=RunStatus.FAILED,
                    pipeline_name=pipeline,
                    run_id="test-run-id",
                    run_type="incremental",
                    error_message="Test error",
                )
            return RunResult(
                status=RunStatus.SUCCESS,
                pipeline_name=pipeline,
                run_id="test-run-id",
                run_type="incremental",
            )

        mock_service.run = AsyncMock(side_effect=mock_run)
        mock_get_service.return_value = mock_service

        def run_coro(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_asyncio.side_effect = run_coro

        result = cli_runner.invoke(cli, ["run-all", "--source", "chembl"])
        assert result.exit_code == 82  # ExitCode.PIPELINE_ERROR
