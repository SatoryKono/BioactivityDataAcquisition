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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for quarantine.py CLI commands.

Tests quarantine management CLI commands including inspect, stats, replay, purge, and resolve.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.domain.types import QuarantineRecordStatus
from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.exit_codes import ExitCode

pytestmark = pytest.mark.unit


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_quarantine_runtime_service() -> MagicMock:
    """Create a mock quarantine runtime service."""
    runtime_service = MagicMock()
    runtime_service.inspect = AsyncMock(return_value=[])
    runtime_service.get_stats = AsyncMock(return_value={"total_count": 0})
    return runtime_service


@pytest.fixture
def mock_quarantine_service() -> MagicMock:
    """Create a mock quarantine service."""
    service = MagicMock()
    service.replay = MagicMock(return_value=[])
    service.purge = MagicMock(return_value=0)
    service.get_stats = AsyncMock(return_value={"total_count": 0})
    service.update_status = MagicMock(return_value=True)
    service.mark_as_reprocessed = MagicMock(return_value=0)
    return service


class TestQuarantineGroup:
    """Test the quarantine command group."""

    def test_quarantine_help_displays_subcommands(self, cli_runner: CliRunner) -> None:
        """Test that quarantine --help displays available subcommands."""
        result = cli_runner.invoke(cli, ["quarantine", "--help"])

        assert result.exit_code == 0
        assert "inspect" in result.output
        assert "stats" in result.output
        assert "replay" in result.output
        assert "purge" in result.output
        assert "resolve" in result.output
        assert "serve" in result.output
        assert "Manage quarantine" in result.output

    def test_quarantine_serve_help_displays_options(
        self, cli_runner: CliRunner
    ) -> None:
        """Quarantine serve should expose dedicated backend options."""
        result = cli_runner.invoke(cli, ["quarantine", "serve", "--help"])

        assert result.exit_code == 0
        assert "--host" in result.output
        assert "--port" in result.output
        assert "--data-root" in result.output
        assert "127.0.0.1" in result.output
        assert "8000" in result.output

    @patch(
        "bioetl.interfaces.cli.commands.quarantine.run_long_lived_quarantine_backend_command"
    )
    def test_quarantine_serve_delegates_to_long_lived_backend(
        self,
        mock_run_quarantine_backend_command: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Quarantine serve must reuse the long-lived health/quarantine backend."""
        result = cli_runner.invoke(
            cli,
            ["quarantine", "serve", "--host", "127.0.0.1", "--port", "18081"],
        )

        assert result.exit_code == ExitCode.OK.value
        mock_run_quarantine_backend_command.assert_called_once_with(
            host="127.0.0.1",
            port=18081,
        )

    @patch(
        "bioetl.interfaces.cli.commands.quarantine.run_long_lived_quarantine_backend_command"
    )
    def test_quarantine_serve_injects_explicit_absolute_data_root(
        self,
        mock_run_quarantine_backend_command: MagicMock,
        cli_runner: CliRunner,
        tmp_path: Path,
    ) -> None:
        result = cli_runner.invoke(
            cli,
            ["quarantine", "serve", "--data-root", str(tmp_path)],
        )

        assert result.exit_code == ExitCode.OK.value
        mock_run_quarantine_backend_command.assert_called_once_with(
            host="127.0.0.1",
            port=8000,
            data_root=tmp_path.resolve(),
        )

    def test_quarantine_serve_rejects_relative_data_root(
        self,
        cli_runner: CliRunner,
    ) -> None:
        result = cli_runner.invoke(
            cli,
            ["quarantine", "serve", "--data-root", "."],
        )

        assert result.exit_code != ExitCode.OK.value
        assert "must be an absolute directory path" in result.output


class TestQuarantineInspect:
    """Test the quarantine inspect subcommand."""

    def test_inspect_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine inspect --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect", "--help"])
        normalized_output = " ".join(result.output.split())

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--limit" in result.output
        assert "--error-code" in result.output
        assert "--run-id" in result.output
        assert "--silver-filter-only" in result.output
        assert "Deprecated legacy alias" in result.output
        assert "FILTERED_OUT_SILVER" in result.output
        assert "sunset 2026-09-30" in result.output
        assert "not Gold" in normalized_output
        assert "contract/semantic rejects" in normalized_output

    def test_inspect_requires_pipeline(self, cli_runner: CliRunner) -> None:
        """Test that quarantine inspect requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_inspect_empty_quarantine(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine inspect with no records."""
        mock_quarantine_runtime_service.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "No records found" in result.output

    def test_quarantine_inspect__inspect_with_records__67bf37fb(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine inspect with existing records."""
        sample_records = [
            {
                "error_code": "VALIDATION_ERROR",
                "payload": {"molecule_id": "CHEMBL123"},
            },
            {
                "error_code": "SCHEMA_MISMATCH",
                "payload": {"molecule_id": "CHEMBL456"},
            },
        ]
        mock_quarantine_runtime_service.inspect = AsyncMock(return_value=sample_records)

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "VALIDATION_ERROR" in result.output
        assert "SCHEMA_MISMATCH" in result.output

    def test_quarantine_inspect__error_code_filter__4dcda885(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine inspect with --error-code filter."""
        mock_quarantine_runtime_service.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--error-code",
                    "DQ_MISSING_FIELD",
                ],
            )

        # Verify inspect was called with correct error_code
        mock_quarantine_runtime_service.inspect.assert_called_once_with(
            limit=100,
            error_code="DQ_MISSING_FIELD",
        )
        assert result.exit_code == 0

    def test_inspect_with_custom_limit(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine inspect with custom --limit."""
        mock_quarantine_runtime_service.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--limit",
                    "50",
                ],
            )

        mock_quarantine_runtime_service.inspect.assert_called_once_with(
            limit=50,
            error_code=None,
        )
        assert result.exit_code == 0

    def test_inspect_with_silver_filter_shortcut(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine inspect with --silver-filter-only shortcut."""
        mock_quarantine_runtime_service.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--silver-filter-only",
                ],
            )

        mock_quarantine_runtime_service.inspect.assert_called_once_with(
            limit=100,
            error_code="FILTERED_OUT_SILVER",
        )
        assert result.exit_code == 0

    def test_quarantine_inspect__with_run_id_filter__461d1db2(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine inspect with explicit run-id scoping."""
        mock_quarantine_runtime_service.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    "00000000-0000-0000-0000-000000000123",
                ],
            )

        mock_quarantine_runtime_service.inspect.assert_called_once_with(
            limit=100,
            error_code=None,
            run_id="00000000-0000-0000-0000-000000000123",
        )
        assert result.exit_code == 0


class TestQuarantineStats:
    """Test the quarantine stats subcommand."""

    def test_stats_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine stats --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "stats", "--help"])
        normalized_output = " ".join(result.output.split())

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--json" in result.output
        assert "--error-code" in result.output
        assert "--run-id" in result.output
        assert "--silver-filter-only" in result.output
        assert "Deprecated legacy alias" in result.output
        assert "FILTERED_OUT_SILVER" in result.output
        assert "sunset 2026-09-30" in result.output
        assert "not Gold" in normalized_output
        assert "contract/semantic rejects" in normalized_output
        assert "--group-by" in result.output
        assert "--top" in result.output

    def test_stats_requires_pipeline(self, cli_runner: CliRunner) -> None:
        """Test that quarantine stats requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "stats"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_stats_empty_quarantine(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats with no records."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={"total_count": 0, "by_error_code": {}, "by_status": {}}
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "Total Records: 0" in result.output

    def test_stats_with_records(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats with records."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={
                "total_count": 100,
                "by_error_code": {"VALIDATION_ERROR": 60, "SCHEMA_ERROR": 40},
                "by_status": {"NEW": 80, "REVIEWED": 20},
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "Total Records: 100" in result.output
        assert "VALIDATION_ERROR" in result.output
        assert "60.0%" in result.output
        assert "By Error Code:" in result.output
        assert "By Status:" in result.output

    def test_stats_with_silver_filter_shortcut(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats with --silver-filter-only shortcut."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={
                "total_count": 3,
                "by_error_code": {"FILTERED_OUT_SILVER": 3},
                "by_status": {"NEW": 3},
                "silver_filter_rejects": {
                    "total_count": 3,
                    "by_reason_code": {"missing_required_field": 2},
                    "by_field": {"publication_year": 2},
                    "by_rule_type": {"required_fields": 2},
                    "by_operator": {"required": 2},
                    "by_reason_signature": {
                        "missing_required_field | required_fields | publication_year | required": 2
                    },
                },
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "stats",
                    "--pipeline",
                    "chembl_activity",
                    "--silver-filter-only",
                ],
            )

        mock_quarantine_runtime_service.get_stats.assert_called_once_with(
            error_code="FILTERED_OUT_SILVER",
            run_id=None,
        )
        assert result.exit_code == 0
        assert "Silver Filter Rejects: 3" in result.output
        assert "missing_required_field" in result.output

    def test_stats_with_run_id_and_bronze_ratio(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test run-scoped Silver reject summary includes Bronze denominator."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={
                "total_count": 4,
                "by_error_code": {"FILTERED_OUT_SILVER": 4},
                "by_status": {"NEW": 4},
                "silver_filter_rejects": {
                    "total_count": 4,
                    "by_reason_code": {"missing_required_field": 4},
                    "by_field": {"publication_year": 4},
                    "by_rule_type": {"required_fields": 4},
                    "by_operator": {"required": 4},
                    "by_reason_code_field": {
                        "missing_required_field | publication_year": 4
                    },
                    "by_reason_signature": {
                        "missing_required_field | required_fields | publication_year | required": 4
                    },
                },
            }
        )
        mock_run_manifest_service = MagicMock()
        mock_run_manifest_service.show.return_value = MagicMock(
            ledger_entries=(
                MagicMock(metrics_snapshot={"records_bronze": 10}),
                MagicMock(metrics_snapshot={"records_silver": 4}),
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            with patch(
                "bioetl.interfaces.cli.commands.quarantine.get_run_manifest_service",
                return_value=mock_run_manifest_service,
            ):
                result = cli_runner.invoke(
                    cli,
                    [
                        "quarantine",
                        "stats",
                        "--pipeline",
                        "chembl_activity",
                        "--silver-filter-only",
                        "--run-id",
                        "00000000-0000-0000-0000-000000000123",
                    ],
                )

        mock_quarantine_runtime_service.get_stats.assert_called_once_with(
            error_code="FILTERED_OUT_SILVER",
            run_id="00000000-0000-0000-0000-000000000123",
        )
        mock_run_manifest_service.show.assert_called_once_with(
            "00000000-0000-0000-0000-000000000123"
        )
        assert result.exit_code == 0
        assert "Run ID Scope: 00000000-0000-0000-0000-000000000123" in result.output
        assert "Silver Rejects vs Bronze: 4/10 (40.0%)" in result.output

    def test_stats_with_focused_group_by_reason_code_field(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats focused grouping for Silver reject causes."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={
                "total_count": 4,
                "by_error_code": {"FILTERED_OUT_SILVER": 4},
                "by_status": {"NEW": 4},
                "silver_filter_rejects": {
                    "total_count": 4,
                    "by_reason_code": {"missing_required_field": 3},
                    "by_field": {"publication_year": 3},
                    "by_rule_type": {"required_fields": 3},
                    "by_operator": {"required": 3},
                    "by_reason_code_field": {
                        "missing_required_field | publication_year": 3
                    },
                    "by_reason_signature": {
                        "missing_required_field | required_fields | publication_year | required": 3
                    },
                },
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "stats",
                    "--pipeline",
                    "chembl_activity",
                    "--silver-filter-only",
                    "--group-by",
                    "reason-code-field",
                    "--top",
                    "5",
                ],
            )

        assert result.exit_code == 0
        assert "Focused Silver Reject Grouping:" in result.output
        assert "Reason Code + Field" in result.output
        assert "missing_required_field | publication_year" in result.output

    def test_stats_with_focused_group_by_reason_signature(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats focused grouping for stable signatures."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={
                "total_count": 2,
                "by_error_code": {"FILTERED_OUT_SILVER": 2},
                "by_status": {"NEW": 2},
                "silver_filter_rejects": {
                    "total_count": 2,
                    "by_reason_code": {"missing_required_field": 2},
                    "by_field": {"publication_year": 2},
                    "by_rule_type": {"required_fields": 2},
                    "by_operator": {"required": 2},
                    "by_reason_code_field": {
                        "missing_required_field | publication_year": 2
                    },
                    "by_reason_signature": {
                        "missing_required_field | required_fields | publication_year | required": 2
                    },
                },
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "stats",
                    "--pipeline",
                    "chembl_activity",
                    "--silver-filter-only",
                    "--group-by",
                    "reason-signature",
                ],
            )

        assert result.exit_code == 0
        assert "Focused Silver Reject Grouping:" in result.output
        assert "Stable Signature" in result.output
        assert (
            "missing_required_field | required_fields | publication_year | required"
            in result.output
        )

    def test_stats_with_top_limits_group_output(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats honors --top for focused Silver grouping."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={
                "total_count": 6,
                "by_error_code": {"FILTERED_OUT_SILVER": 6},
                "by_status": {"NEW": 6},
                "silver_filter_rejects": {
                    "total_count": 6,
                    "by_reason_code": {
                        "missing_required_field": 3,
                        "column_filter_mismatch": 2,
                        "range_filter_mismatch": 1,
                    },
                    "by_field": {},
                    "by_rule_type": {},
                    "by_operator": {},
                    "by_reason_code_field": {},
                    "by_reason_signature": {},
                },
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "stats",
                    "--pipeline",
                    "chembl_activity",
                    "--silver-filter-only",
                    "--group-by",
                    "reason-code",
                    "--top",
                    "2",
                ],
            )

        assert result.exit_code == 0
        assert "missing_required_field" in result.output
        assert "column_filter_mismatch" in result.output
        assert "range_filter_mismatch" not in result.output

    def test_stats_with_focused_group_by_zero_state(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test focused grouping zero-state message when values are unavailable."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={
                "total_count": 1,
                "by_error_code": {"FILTERED_OUT_SILVER": 1},
                "by_status": {"NEW": 1},
                "silver_filter_rejects": {
                    "total_count": 1,
                    "by_reason_code": {},
                    "by_field": {},
                    "by_rule_type": {},
                    "by_operator": {},
                    "by_reason_code_field": {},
                    "by_reason_signature": {},
                },
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "stats",
                    "--pipeline",
                    "chembl_activity",
                    "--silver-filter-only",
                    "--group-by",
                    "reason-signature",
                ],
            )

        assert result.exit_code == 0
        assert "Focused Silver Reject Grouping: no structured values available." in (
            result.output
        )

    def test_stats_json_output(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats with JSON output."""
        stats_data = {
            "total_count": 50,
            "by_error_code": {"DQ_MISSING": 30, "DQ_INVALID": 20},
            "by_status": {"NEW": 40, "RESOLVED": 10},
        }
        mock_quarantine_runtime_service.get_stats = AsyncMock(return_value=stats_data)

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity", "--json"],
            )

        assert result.exit_code == 0
        # Parse JSON output
        output_json = json.loads(result.output)
        assert output_json["total_count"] == 50
        assert output_json["by_error_code"]["DQ_MISSING"] == 30

    def test_stats_exception_handling(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats handles exceptions."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == ExitCode.FAIL.value
        assert "Failed to get stats" in result.output

    def test_stats_dashboard_header(
        self,
        cli_runner: CliRunner,
        mock_quarantine_runtime_service: MagicMock,
    ) -> None:
        """Test quarantine stats displays dashboard header."""
        mock_quarantine_runtime_service.get_stats = AsyncMock(
            return_value={"total_count": 0, "by_error_code": {}, "by_status": {}}
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service",
            return_value=mock_quarantine_runtime_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity"],
            )

        assert "Quarantine Dashboard: chembl_activity" in result.output
        assert "=" * 50 in result.output


class TestQuarantineReplay:
    """Test the quarantine replay subcommand."""

    def test_replay_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine replay --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "replay", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--error-code" in result.output
        assert "--max-age-days" in result.output
        assert "--dry-run" in result.output

    def test_replay_requires_pipeline(self, cli_runner: CliRunner) -> None:
        """Test that quarantine replay requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "replay"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_replay_no_records(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine replay with no records."""
        mock_quarantine_service.replay.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "replay", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "No records found for replay" in result.output

    def test_replay_dry_run(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine replay in dry-run mode."""
        mock_records = [
            {"error_code": "DQ_ERROR", "payload_hash": "abc123def456"},
            {"error_code": "DQ_ERROR", "payload_hash": "xyz789uvw012"},
        ]
        mock_quarantine_service.replay.return_value = mock_records

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "replay", "--pipeline", "chembl_activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Would replay 2 record(s)" in result.output
        assert "abc123def456" in result.output

    def test_replay_dry_run_many_records(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine replay dry-run with many records shows truncation."""
        # Create 15 records to test truncation (shows first 10 + "... and N more")
        mock_records = [
            {"error_code": f"DQ_ERROR_{i}", "payload_hash": f"hash{i:03d}"}
            for i in range(15)
        ]
        mock_quarantine_service.replay.return_value = mock_records

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "replay", "--pipeline", "chembl_activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Would replay 15 record(s)" in result.output
        assert "... and 5 more" in result.output

    def test_replay_actual_replay(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine replay actually marks records as reprocessed."""
        mock_records = [
            {"error_code": "DQ_ERROR", "payload_hash": "abc123"},
            {"error_code": "DQ_ERROR", "payload_hash": "def456"},
        ]
        mock_quarantine_service.replay.return_value = mock_records
        mock_quarantine_service.mark_as_reprocessed.return_value = 2

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "replay", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "Replaying 2 record(s)" in result.output
        assert "Marked 2 record(s) as REPROCESSED" in result.output
        mock_quarantine_service.mark_as_reprocessed.assert_called_once_with(
            mock_records
        )

    def test_quarantine_replay__error_code_filter__cc3d9929(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine replay with error code filter."""
        mock_quarantine_service.replay.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "replay",
                    "--pipeline",
                    "chembl_activity",
                    "--error-code",
                    "DQ_NETWORK_ERROR",
                ],
            )

        # Command should execute without error
        assert result.exit_code == 0
        mock_quarantine_service.replay.assert_called_once_with(
            pipeline="chembl_activity",
            error_code="DQ_NETWORK_ERROR",
            max_age_days=7,
        )

    def test_replay_with_max_age_days(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine replay with custom max-age-days."""
        mock_quarantine_service.replay.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "replay",
                    "--pipeline",
                    "chembl_activity",
                    "--max-age-days",
                    "14",
                ],
            )

        # Command should execute without error
        assert result.exit_code == 0
        mock_quarantine_service.replay.assert_called_once_with(
            pipeline="chembl_activity",
            error_code=None,
            max_age_days=14,
        )


class TestQuarantinePurge:
    """Test the quarantine purge subcommand."""

    def test_purge_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine purge --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "purge", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--older-than-days" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output

    def test_purge_requires_pipeline(self, cli_runner: CliRunner) -> None:
        """Test that quarantine purge requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "purge"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_purge_dry_run(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine purge in dry-run mode."""
        mock_quarantine_service.get_stats = AsyncMock(return_value={"total_count": 50})

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "purge", "--pipeline", "chembl_activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Would purge records older than 30 days" in result.output
        assert "Current total in quarantine: 50" in result.output
        assert "Use without --dry-run" in result.output

    def test_purge_with_confirmation(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine purge with confirmation prompt."""
        mock_quarantine_service.purge.return_value = 25

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            # Simulate user confirming with 'y'
            result = cli_runner.invoke(
                cli,
                ["quarantine", "purge", "--pipeline", "chembl_activity"],
                input="y\n",
            )

        assert result.exit_code == 0
        assert "Purged 25 record(s)" in result.output

    def test_purge_confirmation_abort(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine purge aborts on negative confirmation."""
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            # Simulate user aborting with 'n'
            result = cli_runner.invoke(
                cli,
                ["quarantine", "purge", "--pipeline", "chembl_activity"],
                input="n\n",
            )

        # Should abort
        assert result.exit_code == 1
        assert "Aborted" in result.output

    def test_purge_with_force(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine purge with --force skips confirmation."""
        mock_quarantine_service.purge.return_value = 30

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "purge", "--pipeline", "chembl_activity", "--force"],
            )

        assert result.exit_code == 0
        assert "Purged 30 record(s)" in result.output
        mock_quarantine_service.purge.assert_called_once_with(
            pipeline="chembl_activity",
            older_than_days=30,
        )

    def test_purge_custom_older_than_days(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine purge with custom --older-than-days."""
        mock_quarantine_service.purge.return_value = 10

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "purge",
                    "--pipeline",
                    "chembl_activity",
                    "--older-than-days",
                    "60",
                    "--force",
                ],
            )

        assert result.exit_code == 0
        mock_quarantine_service.purge.assert_called_once_with(
            pipeline="chembl_activity",
            older_than_days=60,
        )


class TestQuarantineResolve:
    """Test the quarantine resolve subcommand."""

    def test_resolve_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine resolve --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "resolve", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--payload-hash" in result.output
        assert "--status" in result.output
        assert "IGNORED" in result.output
        assert "REPROCESSED" in result.output

    def test_resolve_requires_pipeline_and_hash(self, cli_runner: CliRunner) -> None:
        """Test that quarantine resolve requires --pipeline and --payload-hash."""
        result = cli_runner.invoke(cli, ["quarantine", "resolve"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_resolve_requires_payload_hash(self, cli_runner: CliRunner) -> None:
        """Test that quarantine resolve requires --payload-hash."""
        result = cli_runner.invoke(cli, ["quarantine", "resolve", "--pipeline", "test"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_resolve_success_default_status(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine resolve with default IGNORED status."""
        mock_quarantine_service.update_status.return_value = True

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "resolve",
                    "--pipeline",
                    "chembl_activity",
                    "--payload-hash",
                    "abc123def456",
                ],
            )

        assert result.exit_code == 0
        assert "Record abc123def456 marked as IGNORED" in result.output
        mock_quarantine_service.update_status.assert_called_once_with(
            "abc123def456", QuarantineRecordStatus.IGNORED
        )

    def test_resolve_with_reprocessed_status(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine resolve with REPROCESSED status."""
        mock_quarantine_service.update_status.return_value = True

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "resolve",
                    "--pipeline",
                    "chembl_activity",
                    "--payload-hash",
                    "xyz789",
                    "--status",
                    "REPROCESSED",
                ],
            )

        assert result.exit_code == 0
        assert "Record xyz789 marked as REPROCESSED" in result.output
        mock_quarantine_service.update_status.assert_called_once_with(
            "xyz789", QuarantineRecordStatus.REPROCESSED
        )

    def test_resolve_record_not_found(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test quarantine resolve when record not found."""
        mock_quarantine_service.update_status.return_value = False

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "resolve",
                    "--pipeline",
                    "chembl_activity",
                    "--payload-hash",
                    "nonexistent",
                ],
            )

        assert result.exit_code == ExitCode.FAIL.value
        assert "Record not found: nonexistent" in result.output

    def test_resolve_invalid_status(self, cli_runner: CliRunner) -> None:
        """Test quarantine resolve with invalid status."""
        result = cli_runner.invoke(
            cli,
            [
                "quarantine",
                "resolve",
                "--pipeline",
                "chembl_activity",
                "--payload-hash",
                "abc123",
                "--status",
                "INVALID_STATUS",
            ],
        )

        assert result.exit_code != 0
        # Click should reject invalid choice
        assert (
            "Invalid value" in result.output
            or "invalid choice" in result.output.lower()
        )


class TestQuarantineEdgeCases:
    """Test edge cases and error handling for quarantine commands."""

    @patch("bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service")
    def test_inspect_displays_info_message(
        self,
        mock_get_runtime_service: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that inspect displays informational message."""
        mock_runtime_service = MagicMock()
        mock_runtime_service.inspect = AsyncMock(return_value=[])
        mock_get_runtime_service.return_value = mock_runtime_service

        result = cli_runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline", "--limit", "50"],
        )

        assert "Inspecting quarantine for test_pipeline (limit 50)" in result.output

    def test_replay_record_without_payload_hash(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test replay handles records without payload_hash."""
        # Record without payload_hash
        mock_records = [{"error_code": "DQ_ERROR"}]
        mock_quarantine_service.replay.return_value = mock_records
        mock_quarantine_service.mark_as_reprocessed.return_value = 0

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "replay", "--pipeline", "chembl_activity"],
            )

        # Should not crash
        assert result.exit_code == 0

    def test_replay_dry_run_shows_hash_truncated(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test replay dry-run truncates long payload hashes."""
        long_hash = "a" * 64  # SHA256 hash length
        mock_records = [{"error_code": "DQ_ERROR", "payload_hash": long_hash}]
        mock_quarantine_service.replay.return_value = mock_records

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "replay", "--pipeline", "chembl_activity", "--dry-run"],
            )

        # Hash should be truncated to first 16 chars + "..."
        assert "aaaaaaaaaaaaaaaa..." in result.output

    def test_purge_dry_run_custom_days(
        self,
        cli_runner: CliRunner,
        mock_quarantine_service: MagicMock,
    ) -> None:
        """Test purge dry-run shows custom older-than-days."""
        mock_quarantine_service.get_stats = AsyncMock(return_value={"total_count": 100})

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_service",
            return_value=mock_quarantine_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "purge",
                    "--pipeline",
                    "chembl_activity",
                    "--older-than-days",
                    "90",
                    "--dry-run",
                ],
            )

        assert "Would purge records older than 90 days" in result.output
