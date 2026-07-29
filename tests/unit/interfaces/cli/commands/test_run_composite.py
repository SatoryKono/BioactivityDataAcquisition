# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for run_composite.py CLI command.

Tests the run-composite command for composite pipeline execution.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig
from tests.unit.interfaces.cli.commands.conftest import mock_asyncio_run
from bioetl.domain.composite.result import (
    CompositeResult,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.commands.run_composite import (
    _run_composite_async,
    _run_composite_inner,
    _validate_composite_name,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture(autouse=True)
def patch_observability_backend_ensure() -> None:
    """Prevent CLI tests from starting a real detached observability backend."""
    with patch(
        "bioetl.interfaces.cli.commands.run_composite.ensure_observability_backend_started",
        return_value=ObservabilityBackendEnsureResult(
            status="failed",
            health_url="http://127.0.0.1:8081/health",
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def patch_composite_metrics_gateway() -> None:
    """Keep run-composite unit tests from bootstrapping real observability."""
    with patch(
        "bioetl.interfaces.cli.commands.domains.composite.support.push_metrics_to_gateway",
        return_value=True,
    ):
        yield


@pytest.fixture
def mock_composite_result_success() -> CompositeResult:
    """Create a successful CompositeResult for testing."""
    return CompositeResult(
        composite_name="publication",
        composite_run_id="test-run-id",
        seed_result=SeedResult(
            pipeline_name="chembl_publication",
            records_extracted=100,
            records_silver=100,
            keys_generated=100,
        ),
        enrichment_results={
            "crossref": EnrichmentResult(
                enricher_name="crossref",
                status=EnrichmentStatus.SUCCESS,
                records_input=100,
                records_enriched=80,
            ),
        },
        merge_result=MergeResult(
            records_merged=100,
            records_from_seed=100,
            records_enriched=80,
        ),
    )


@pytest.fixture
def mock_composite_result_failed_enricher() -> CompositeResult:
    """Create a CompositeResult with failed enricher for testing."""
    return CompositeResult(
        composite_name="publication",
        composite_run_id="test-run-id",
        seed_result=SeedResult(
            pipeline_name="chembl_publication",
            records_extracted=100,
            records_silver=100,
            keys_generated=100,
        ),
        enrichment_results={
            "crossref": EnrichmentResult(
                enricher_name="crossref",
                status=EnrichmentStatus.FAILED,
                records_input=100,
                error_message="Connection timeout",
            ),
        },
        merge_result=None,
        _required_enrichers=frozenset(["crossref"]),
    )


class TestValidateCompositeName:
    """Test _validate_composite_name function."""

    def test_valid_name_returned(self) -> None:
        """Test valid composite name is returned unchanged."""
        ctx = MagicMock()
        param = MagicMock()
        result = _validate_composite_name(ctx, param, "publication")
        assert result == "publication"

    def test_empty_name_raises_bad_parameter(self) -> None:
        """Test empty name raises BadParameter."""
        import click

        ctx = MagicMock()
        param = MagicMock()

        with pytest.raises(click.BadParameter) as exc_info:
            _validate_composite_name(ctx, param, "")

        assert "Composite pipeline name is required" in str(exc_info.value)


class TestRunCompositeHelp:
    """Test run-composite command help."""

    def test_run_composite_help__displays_options__6849e7c9(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that run-composite --help displays available options."""
        result = cli_runner.invoke(cli, ["run-composite", "--help"])

        assert result.exit_code == 0
        assert "--composite" in result.output
        assert "--resume" in result.output
        assert "--dry-run" in result.output
        assert "--seed-limit" in result.output
        assert "--enrich-only" in result.output
        assert "--required-only" in result.output
        assert "--force-enricher" in result.output
        assert "--debug" in result.output
        assert "--health-server" in result.output
        assert "--health-port" in result.output
        assert "--cached-bronze-enrichers" in result.output
        assert "--cached-bronze-dependencies" in result.output


class TestRunCompositeInner:
    """Test _run_composite_inner function."""

    @pytest.mark.asyncio
    async def test_config_not_found(self) -> None:
        """Test handling of missing config file."""
        with patch(
            "bioetl.interfaces.cli.commands.run_composite.load_composite_config",
            side_effect=FileNotFoundError("Config not found: publication.yaml"),
        ):
            success, error = await _run_composite_inner(
                "publication",
                CompositeRuntimeConfig(),
            )

        assert success is False
        assert "Config not found" in error

    @pytest.mark.asyncio
    async def test_invalid_config(self) -> None:
        """Test handling of invalid config."""
        with patch(
            "bioetl.interfaces.cli.commands.run_composite.load_composite_config",
            side_effect=ValueError("Invalid seed pipeline configuration"),
        ):
            success, error = await _run_composite_inner(
                "publication",
                CompositeRuntimeConfig(),
            )

        assert success is False
        assert "Invalid configuration" in error

    @pytest.mark.asyncio
    async def test_successful_execution(
        self,
        mock_composite_result_success: CompositeResult,
    ) -> None:
        """Test successful composite pipeline execution."""
        mock_config = MagicMock()
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock(return_value=mock_composite_result_success)

        with (
            patch(
                "bioetl.interfaces.cli.commands.run_composite.load_composite_config",
                return_value=mock_config,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_composite.bootstrap_composite_runner",
                return_value=mock_runner,
            ),
        ):
            success, error = await _run_composite_inner(
                "publication",
                CompositeRuntimeConfig(),
            )

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_failed_execution_with_failed_enrichers(
        self,
        mock_composite_result_failed_enricher: CompositeResult,
    ) -> None:
        """Test failed execution with failed enrichers."""
        mock_config = MagicMock()
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock(return_value=mock_composite_result_failed_enricher)

        with (
            patch(
                "bioetl.interfaces.cli.commands.run_composite.load_composite_config",
                return_value=mock_config,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_composite.bootstrap_composite_runner",
                return_value=mock_runner,
            ),
        ):
            success, error = await _run_composite_inner(
                "publication",
                CompositeRuntimeConfig(),
            )

        assert success is False
        assert "Failed enrichers: crossref" in error

    @pytest.mark.asyncio
    async def test_failed_execution_no_enrichers(self) -> None:
        """Test failed execution without failed enrichers."""
        # Create a result that fails without failed_enrichers
        failed_result = CompositeResult(
            composite_name="publication",
            composite_run_id="test-run-id",
            seed_result=SeedResult(
                pipeline_name="chembl_publication",
                records_extracted=0,
                records_silver=0,
                keys_generated=0,
            ),
            enrichment_results={},
            merge_result=None,
        )
        mock_config = MagicMock()
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock(return_value=failed_result)

        with (
            patch(
                "bioetl.interfaces.cli.commands.run_composite.load_composite_config",
                return_value=mock_config,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_composite.bootstrap_composite_runner",
                return_value=mock_runner,
            ),
        ):
            success, error = await _run_composite_inner(
                "publication",
                CompositeRuntimeConfig(),
            )

        assert success is False
        assert "Composite pipeline failed" in error

    @pytest.mark.asyncio
    async def test_execution_exception(self) -> None:
        """Test handling of exception during execution."""
        mock_config = MagicMock()
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock(side_effect=RuntimeError("Connection failed"))

        with (
            patch(
                "bioetl.interfaces.cli.commands.run_composite.load_composite_config",
                return_value=mock_config,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_composite.bootstrap_composite_runner",
                return_value=mock_runner,
            ),
        ):
            success, error = await _run_composite_inner(
                "publication",
                CompositeRuntimeConfig(),
            )

        assert success is False
        assert "Connection failed" in error


class TestRunCompositeAsync:
    """Test _run_composite_async function."""

    @pytest.mark.asyncio
    async def test_with_health_server_enabled(self) -> None:
        """Test execution with health server enabled."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.run_composite._run_composite_inner",
                new_callable=AsyncMock,
                return_value=(True, None),
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_composite.health_server_context"
            ) as mock_context,
            patch(
                "bioetl.interfaces.cli.commands.run_composite.ensure_metrics_server_started",
                return_value=True,
            ) as mock_metrics_starter,
        ):
            # Make context manager work
            mock_context.return_value.__aenter__ = AsyncMock()
            mock_context.return_value.__aexit__ = AsyncMock()

            success, error = await _run_composite_async(
                "publication",
                CompositeRuntimeConfig(),
                health_server_enabled=True,
                health_port=8081,
            )

        assert success is True
        assert error is None
        mock_context.assert_called_once_with(enabled=True, port=8081)
        mock_metrics_starter.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_with_health_server_disabled(self) -> None:
        """Test execution with health server disabled."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.run_composite._run_composite_inner",
                new_callable=AsyncMock,
                return_value=(True, None),
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_composite.health_server_context"
            ) as mock_context,
            patch(
                "bioetl.interfaces.cli.commands.run_composite.ensure_metrics_server_started",
                return_value=True,
            ) as mock_metrics_starter,
        ):
            mock_context.return_value.__aenter__ = AsyncMock()
            mock_context.return_value.__aexit__ = AsyncMock()

            success, _ = await _run_composite_async(
                "publication",
                CompositeRuntimeConfig(),
                health_server_enabled=False,
                health_port=9090,
            )

        assert success is True
        mock_context.assert_called_once_with(enabled=False, port=9090)
        mock_metrics_starter.assert_called_once_with()


class TestRunCompositeCommand:
    """Test the run-composite CLI command."""

    def test_run_composite_ensures_observability_backend_with_catalog_probe(
        self, cli_runner: CliRunner
    ) -> None:
        backend_result = ObservabilityBackendEnsureResult(
            status="reused",
            health_url="http://127.0.0.1:8081/health",
        )
        with (
            patch(
                "bioetl.interfaces.cli.commands.run_composite.ensure_observability_backend_started",
                return_value=backend_result,
            ) as mock_ensure_backend,
            patch(
                "bioetl.interfaces.cli.commands.run_composite.should_disable_transient_health_server",
                return_value=False,
            ),
            mock_asyncio_run(return_value=(True, None)),
        ):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication"]
            )

        assert result.exit_code == ExitCode.OK.value
        mock_ensure_backend.assert_called_once_with(
            enabled=True,
            port=8081,
            required_probe_paths=("/ops/control-plane/ready",),
        )

    def test_run_composite_command__successful_execution__9a97129e(
        self, cli_runner: CliRunner
    ) -> None:
        """Test successful composite pipeline execution via CLI."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication"]
            )

        assert "Starting composite pipeline: publication" in result.output
        assert "Composite pipeline completed successfully" in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_failed_execution(self, cli_runner: CliRunner) -> None:
        """Test failed composite pipeline execution via CLI."""
        with mock_asyncio_run(return_value=(False, "Config not found")):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication"]
            )

        assert "Composite pipeline failed" in result.output
        assert "Config not found" in result.output
        assert result.exit_code == ExitCode.PIPELINE_ERROR.value

    def test_dry_run_mode(self, cli_runner: CliRunner) -> None:
        """Test dry-run mode displays warning."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication", "--dry-run"]
            )

        assert "Dry-run mode: no data will be written" in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_resume_mode(self, cli_runner: CliRunner) -> None:
        """Test resume mode displays info message."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication", "--resume"]
            )

        assert "Resume mode: continuing from last checkpoint" in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_cached_bronze_mode_displays_rebuild_resume_boundary_warning(
        self, cli_runner: CliRunner
    ) -> None:
        """Cached Bronze startup warns that composite remains rebuild/resume only."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                [
                    "run-composite",
                    "--composite",
                    "publication",
                    "--use-cached-bronze",
                ],
            )

        assert "outside the strict exact-replay boundary" in result.output
        assert "Cached Bronze is rebuild/resume evidence only" in result.output
        assert "strict exact replay remains source-run only" in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_cached_bronze_dependencies_displays_rebuild_resume_boundary_warning(
        self, cli_runner: CliRunner
    ) -> None:
        """Dependency-only cached Bronze still warns about rebuild/resume boundary."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                [
                    "run-composite",
                    "--composite",
                    "publication",
                    "--cached-bronze-dependencies",
                ],
            )

        assert "outside the strict exact-replay boundary" in result.output
        assert "Cached Bronze is rebuild/resume evidence only" in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_keyboard_interrupt(self, cli_runner: CliRunner) -> None:
        """Test handling of keyboard interrupt."""
        with mock_asyncio_run(side_effect=KeyboardInterrupt):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication"]
            )

        assert "interrupted by user" in result.output
        assert result.exit_code == ExitCode.SIGINT.value

    def test_unexpected_exception(self, cli_runner: CliRunner) -> None:
        """Test handling of unexpected exception."""
        with mock_asyncio_run(side_effect=RuntimeError("Unexpected error")):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication"]
            )

        assert "Unexpected error" in result.output
        assert result.exit_code == ExitCode.FAIL.value

    def test_health_server_disabled(self, cli_runner: CliRunner) -> None:
        """Test --no-health-server option."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                ["run-composite", "--composite", "publication", "--no-health-server"],
            )

        assert result.exit_code == ExitCode.OK.value

    def test_custom_health_port(self, cli_runner: CliRunner) -> None:
        """Test --health-port option."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                [
                    "run-composite",
                    "--composite",
                    "publication",
                    "--health-port",
                    "9090",
                ],
            )

        assert result.exit_code == ExitCode.OK.value


class TestRunCompositeRuntimeConfig:
    """Test CompositeRuntimeConfig creation from CLI options."""

    def test_default_config__test_run_composite_runtime_config_cli_commands_test_run_composite_494(
        self, cli_runner: CliRunner
    ) -> None:
        """Test default runtime config values."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication"]
            )

        assert result.exit_code == ExitCode.OK.value

    def test_seed_limit_option(self, cli_runner: CliRunner) -> None:
        """Test --seed-limit option."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                ["run-composite", "--composite", "publication", "--seed-limit", "100"],
            )

        assert result.exit_code == ExitCode.OK.value

    def test_enrich_only_option(self, cli_runner: CliRunner) -> None:
        """Test --enrich-only option parsing."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                [
                    "run-composite",
                    "--composite",
                    "publication",
                    "--enrich-only",
                    "crossref,pubmed",
                ],
            )

        assert result.exit_code == ExitCode.OK.value

    def test_required_only_option(self, cli_runner: CliRunner) -> None:
        """Test --required-only option."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                ["run-composite", "--composite", "publication", "--required-only"],
            )

        assert result.exit_code == ExitCode.OK.value

    def test_force_enricher_option(self, cli_runner: CliRunner) -> None:
        """Test --force-enricher option."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                [
                    "run-composite",
                    "--composite",
                    "publication",
                    "--force-enricher",
                    "crossref",
                ],
            )

        assert result.exit_code == ExitCode.OK.value

    def test_debug_option(self, cli_runner: CliRunner) -> None:
        """Test --debug option."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication", "--debug"]
            )

        assert result.exit_code == ExitCode.OK.value

    def test_no_cached_bronze_enrichers_option(self, cli_runner: CliRunner) -> None:
        """Test --no-cached-bronze-enrichers forces API for enrichers."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                [
                    "run-composite",
                    "--composite",
                    "publication",
                    "--no-cached-bronze-enrichers",
                ],
            )

        assert result.exit_code == ExitCode.OK.value

    def test_no_cached_bronze_dependencies_option(self, cli_runner: CliRunner) -> None:
        """Test --no-cached-bronze-dependencies forces API for dependencies."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                [
                    "run-composite",
                    "--composite",
                    "publication",
                    "--no-cached-bronze-dependencies",
                ],
            )

        assert result.exit_code == ExitCode.OK.value


class TestRunCompositeRequiredOption:
    """Test that --composite option is required."""

    def test_missing_composite_option(self, cli_runner: CliRunner) -> None:
        """Test error when --composite option is missing."""
        result = cli_runner.invoke(cli, ["run-composite"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestHealthServerInfoOutput:
    """Test health server info output."""

    def test_health_server_info_displayed(self, cli_runner: CliRunner) -> None:
        """Test health server info is displayed."""
        with (
            mock_asyncio_run(return_value=(True, None)),
            patch(
                "bioetl.interfaces.cli.commands.run_composite.echo_health_server_info"
            ) as mock_echo,
        ):
            cli_runner.invoke(cli, ["run-composite", "--composite", "publication"])

        # Verify echo_health_server_info was called
        mock_echo.assert_called_once()


class TestCompositeRuntimeConfigPostInit:
    """Test CompositeRuntimeConfig __post_init__ behavior."""

    def test_enrich_only_list_converted_to_tuple(self) -> None:
        """Test list enrich_only is converted to tuple."""
        # Directly creating with a list should convert it
        config = CompositeRuntimeConfig(
            enrich_only=["crossref", "pubmed"],  # type: ignore[arg-type]
        )
        assert isinstance(config.enrich_only, tuple)
        assert config.enrich_only == ("crossref", "pubmed")

    def test_enrich_only_none_stays_none(self) -> None:
        """Test None enrich_only stays None."""
        config = CompositeRuntimeConfig(enrich_only=None)
        assert config.enrich_only is None

    def test_enrich_only_tuple_stays_tuple(self) -> None:
        """Test tuple enrich_only stays tuple."""
        config = CompositeRuntimeConfig(enrich_only=("crossref", "pubmed"))
        assert config.enrich_only == ("crossref", "pubmed")

    def test_cached_bronze_enrichers_default_none(self) -> None:
        """Test cached_bronze_enrichers defaults to None (follow master)."""
        config = CompositeRuntimeConfig()
        assert config.cached_bronze_enrichers is None

    def test_cached_bronze_dependencies_default_false(self) -> None:
        """Test cached_bronze_dependencies defaults to False (always call APIs).

        Dependencies receive seed-derived keys, so their Bronze cache is
        typically stale or absent (e.g. uniprot_idmapping on first composite
        run). Default False ensures APIs are always called.
        """
        config = CompositeRuntimeConfig()
        assert config.cached_bronze_dependencies is False

    def test_cached_bronze_enrichers_explicit_false(self) -> None:
        """Test cached_bronze_enrichers can be set to False."""
        config = CompositeRuntimeConfig(cached_bronze_enrichers=False)
        assert config.cached_bronze_enrichers is False

    def test_cached_bronze_dependencies_explicit_true(self) -> None:
        """Test cached_bronze_dependencies can be set to True."""
        config = CompositeRuntimeConfig(cached_bronze_dependencies=True)
        assert config.cached_bronze_dependencies is True


class TestRunCompositeAllOptionsOutput:
    """Test run-composite command output with various options."""

    def test_combined_options_output(self, cli_runner: CliRunner) -> None:
        """Test output with multiple options combined."""
        with mock_asyncio_run(return_value=(True, None)):
            result = cli_runner.invoke(
                cli,
                [
                    "run-composite",
                    "--composite",
                    "publication",
                    "--dry-run",
                    "--resume",
                    "--seed-limit",
                    "50",
                    "--enrich-only",
                    "crossref",
                ],
            )

        assert "Starting composite pipeline: publication" in result.output
        assert "Dry-run mode" in result.output
        assert "Resume mode" in result.output
        assert result.exit_code == ExitCode.OK.value

    def test_all_options_output__with_unknown_error__3e674da9(
        self, cli_runner: CliRunner
    ) -> None:
        """Test failed execution with None error message."""
        with mock_asyncio_run(return_value=(False, None)):
            result = cli_runner.invoke(
                cli, ["run-composite", "--composite", "publication"]
            )

        assert "Composite pipeline failed" in result.output
        assert "Unknown error" in result.output
        assert result.exit_code == ExitCode.PIPELINE_ERROR.value
