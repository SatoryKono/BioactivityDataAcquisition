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
"""Integration matrix for CLI exit-code mapping across orchestration commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.services.export_service import (
    ExportResult,
)
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunResult,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
)
from bioetl.interfaces.cli.exit_codes import ExitCode


def _get_cli():
    from bioetl.interfaces.cli import cli

    return cli


def _get_batch_run_result_type():
    from bioetl.interfaces.cli.commands.run_all import BatchRunResult

    return BatchRunResult


@pytest.mark.integration
class TestCliExitCodeMatrix:
    """Validate consistent exit-code policy for run/run-all/run-composite."""

    @pytest.fixture(autouse=True)
    def _mock_registry(self):
        registry = MagicMock()
        registry.list_pipelines.return_value = [
            "chembl_activity",
            "chembl_assay",
            "pubchem_compound",
        ]
        backend_result = ObservabilityBackendEnsureResult(
            status="disabled",
            health_url="http://127.0.0.1:8000/health",
            message="CLI exit-code matrix disables detached backend startup.",
        )
        with (
            patch("bioetl.interfaces.cli.main.register_all_pipelines"),
            patch(
                "bioetl.interfaces.cli.commands.domains.run.support.build_cli_registry",
                return_value=registry,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
                return_value=registry,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run.ensure_observability_backend_started",
                return_value=backend_result,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_all.ensure_observability_backend_started",
                return_value=backend_result,
            ),
        ):
            yield registry

    def test_run_exit_code_matrix(self, cli_runner) -> None:
        with patch("bioetl.interfaces.cli.commands.run.execute_run") as mock_execute:
            mock_execute.return_value = RunResult(
                status=PipelineRunResult.SUCCESS,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )
            result = cli_runner.invoke(
                _get_cli(),
                ["run", "--pipeline", "chembl_activity"],
            )
            assert result.exit_code == ExitCode.OK

            mock_execute.return_value = RunResult(
                status=PipelineRunResult.SHUTDOWN,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )
            result = cli_runner.invoke(
                _get_cli(),
                ["run", "--pipeline", "chembl_activity"],
            )
            assert result.exit_code == ExitCode.SIGINT

            mock_execute.return_value = RunResult(
                status=PipelineRunResult.FAILED,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
                error_type="DataQualityError",
            )
            result = cli_runner.invoke(
                _get_cli(),
                ["run", "--pipeline", "chembl_activity"],
            )
            assert result.exit_code == ExitCode.DATA_QUALITY_ERROR

            mock_execute.side_effect = PipelineNotFoundError(
                "chembl_activity",
                ["chembl_assay"],
            )
            result = cli_runner.invoke(
                _get_cli(),
                ["run", "--pipeline", "chembl_activity"],
            )
            assert result.exit_code == ExitCode.CONFIG_ERROR

            mock_execute.side_effect = RuntimeError("boom")
            result = cli_runner.invoke(
                _get_cli(),
                ["run", "--pipeline", "chembl_activity"],
            )
            assert result.exit_code == ExitCode.FAIL

    def test_run_all_exit_code_matrix(self, cli_runner, _mock_registry) -> None:
        batch_run_result = _get_batch_run_result_type()
        with (
            patch(
                "bioetl.interfaces.cli.commands.run_all.resolve_context_registry",
                return_value=_mock_registry,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_all._run_batch_with_policy"
            ) as mock_execute_batch,
        ):
            mock_execute_batch.return_value = batch_run_result(
                total=2,
                succeeded=2,
                failed=0,
                skipped=0,
                results=[
                    RunResult(
                        status=PipelineRunResult.SUCCESS,
                        pipeline_name="chembl_activity",
                        run_id="test-run-id",
                        run_type="incremental",
                    ),
                    RunResult(
                        status=PipelineRunResult.SUCCESS,
                        pipeline_name="chembl_assay",
                        run_id="test-run-id",
                        run_type="incremental",
                    ),
                ],
            )
            result = cli_runner.invoke(
                _get_cli(),
                ["run-all", "--source", "chembl", "--yes"],
            )
            assert result.exit_code == ExitCode.OK

            mock_execute_batch.return_value = batch_run_result(
                total=2,
                succeeded=1,
                failed=1,
                skipped=0,
                failed_pipelines=["chembl_assay"],
                results=[
                    RunResult(
                        status=PipelineRunResult.SUCCESS,
                        pipeline_name="chembl_activity",
                        run_id="test-run-id",
                        run_type="incremental",
                    ),
                    RunResult(
                        status=PipelineRunResult.FAILED,
                        pipeline_name="chembl_assay",
                        run_id="test-run-id",
                        run_type="incremental",
                    ),
                ],
            )
            result = cli_runner.invoke(
                _get_cli(),
                ["run-all", "--source", "chembl", "--yes"],
            )
            assert result.exit_code == ExitCode.PIPELINE_ERROR

            mock_execute_batch.return_value = batch_run_result(
                total=1,
                succeeded=0,
                failed=0,
                skipped=1,
                results=[
                    RunResult(
                        status=PipelineRunResult.SHUTDOWN,
                        pipeline_name="chembl_activity",
                        run_id="test-run-id",
                        run_type="incremental",
                    )
                ],
            )
            result = cli_runner.invoke(
                _get_cli(),
                ["run-all", "--source", "chembl", "--yes"],
            )
            assert result.exit_code == ExitCode.SIGINT

    def test_run_composite_exit_code_matrix(self, cli_runner) -> None:
        backend_result = ObservabilityBackendEnsureResult(
            status="disabled",
            health_url="http://127.0.0.1:8000/health",
            message="CLI exit-code matrix disables detached backend startup.",
        )
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.composite.support.asyncio.run"
            ) as mock_run,
            patch(
                "bioetl.interfaces.cli.commands.domains.composite.support.push_metrics_to_gateway",
                return_value=True,
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_composite.ensure_observability_backend_started",
                return_value=backend_result,
            ),
        ):
            mock_run.return_value = (True, None)
            result = cli_runner.invoke(
                _get_cli(),
                ["run-composite", "--composite", "publication"],
            )
            assert result.exit_code == ExitCode.OK

            mock_run.return_value = (False, "failed")
            result = cli_runner.invoke(
                _get_cli(),
                ["run-composite", "--composite", "publication"],
            )
            assert result.exit_code == ExitCode.PIPELINE_ERROR

            mock_run.side_effect = KeyboardInterrupt()
            result = cli_runner.invoke(
                _get_cli(),
                ["run-composite", "--composite", "publication"],
            )
            assert result.exit_code == ExitCode.SIGINT

            mock_run.side_effect = RuntimeError("boom")
            result = cli_runner.invoke(
                _get_cli(),
                ["run-composite", "--composite", "publication"],
            )
            assert result.exit_code == ExitCode.FAIL

    def test_export_exit_code_matrix(self, cli_runner) -> None:
        service = MagicMock()
        service.list_tables.return_value = []
        service.export = AsyncMock(
            return_value=ExportResult(
                table_name="chembl.activity",
                layer="silver",
                format="csv",
                output_path=None,
                row_count=10,
                error=None,
            )
        )
        service.preview = AsyncMock(return_value=MagicMock())

        with patch(
            "bioetl.interfaces.cli.commands.export.get_export_service",
            return_value=service,
        ):
            result = cli_runner.invoke(_get_cli(), ["export", "--list"])
            assert result.exit_code == ExitCode.OK

            service.export.return_value = ExportResult(
                table_name="chembl.activity",
                layer="silver",
                format="csv",
                output_path=None,
                row_count=0,
                error="write failed",
            )
            result = cli_runner.invoke(_get_cli(), ["export", "chembl.activity"])
            assert result.exit_code == ExitCode.FAIL

            service.list_tables.side_effect = RuntimeError("boom")
            result = cli_runner.invoke(_get_cli(), ["export", "--list"])
            assert result.exit_code == ExitCode.FAIL

    def test_health_check_exit_code_matrix(self, cli_runner) -> None:
        with patch("bioetl.interfaces.cli.commands.health.asyncio.run") as mock_run:
            mock_run.return_value = {
                "chembl": {"status": "healthy", "latency_ms": "10.0"},
                "pubchem": {"status": "healthy", "latency_ms": "20.0"},
            }
            result = cli_runner.invoke(_get_cli(), ["health", "check"])
            assert result.exit_code == ExitCode.OK

            mock_run.return_value = {
                "chembl": {"status": "healthy", "latency_ms": "10.0"},
                "pubchem": {"status": "unhealthy", "error": "timeout"},
            }
            result = cli_runner.invoke(_get_cli(), ["health", "check", "--json"])
            assert result.exit_code == ExitCode.FAIL

            mock_run.side_effect = RuntimeError("boom")
            result = cli_runner.invoke(_get_cli(), ["health", "check"])
            assert result.exit_code == ExitCode.FAIL

    def test_quarantine_stats_exit_code_matrix(self, cli_runner) -> None:
        manager = MagicMock()
        manager.get_stats = AsyncMock(
            return_value={
                "total_count": 1,
                "by_error_code": {"DQ_MISSING": 1},
                "by_status": {"NEW": 1},
            }
        )
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=manager,
        ):
            result = cli_runner.invoke(
                _get_cli(), ["quarantine", "stats", "--pipeline", "chembl_activity"]
            )
            assert result.exit_code == ExitCode.OK

            manager.get_stats.side_effect = RuntimeError("boom")
            result = cli_runner.invoke(
                _get_cli(), ["quarantine", "stats", "--pipeline", "chembl_activity"]
            )
            assert result.exit_code == ExitCode.FAIL

    def test_maintenance_vacuum_exit_code_matrix(self, cli_runner) -> None:
        lifecycle = MagicMock()
        lifecycle.vacuum = AsyncMock(return_value=5)
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=lifecycle,
        ):
            result = cli_runner.invoke(
                _get_cli(), ["maintenance", "vacuum", "chembl.activity"]
            )
            assert result.exit_code == ExitCode.OK

            lifecycle.vacuum.side_effect = RuntimeError("boom")
            result = cli_runner.invoke(
                _get_cli(), ["maintenance", "vacuum", "chembl.activity"]
            )
            assert result.exit_code == ExitCode.FAIL
