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
"""Unit tests for interfaces/cli/commands/adr.py.

Covers list, show, and validate commands with mocked AdrServicePort.
Uses Click's CliRunner to test command output without real filesystem access.
"""

from __future__ import annotations

from typing import Any

import pytest
from click.testing import CliRunner

from bioetl.domain.ports.adr import (
    AdrDocument,
    AdrInfo,
    AdrServicePort,
    AdrValidationIssue,
    AdrValidationReport,
)
from bioetl.interfaces.cli.main import cli


# =============================================================================
# Fake AdrServicePort implementations
# =============================================================================


class _FakeAdrServiceWithItems(AdrServicePort):
    """Fake AdrServicePort returning a list of ADRs."""

    def list_adrs(self) -> list[AdrInfo]:  # type: ignore[override]
        return [
            AdrInfo(
                number=1, title="Use Hexagonal Architecture", path="/docs/ADR-001.md"
            ),
            AdrInfo(
                number=2, title="Use Delta Lake for Silver", path="/docs/ADR-002.md"
            ),
            AdrInfo(number=26, title="Composite Pipelines", path="/docs/ADR-026.md"),
        ]

    def get_adr(self, number: int) -> AdrDocument:  # type: ignore[override]
        docs = {
            1: AdrDocument(
                number=1,
                title="Use Hexagonal Architecture",
                content="# ADR-001\n\n## Status\n\nAccepted\n\n## Context\n\nWe need an architecture.\n",
                path="/docs/ADR-001.md",
                status="Accepted",
                date="2024-01-01",
            ),
            2: AdrDocument(
                number=2,
                title="Use Delta Lake for Silver",
                content="# ADR-002\n\nContent line 2\n",
                path="/docs/ADR-002.md",
                status="Accepted",
                date=None,
            ),
        }
        if number not in docs:
            raise FileNotFoundError(f"ADR-{number:03d} not found")
        return docs[number]

    def validate(self) -> AdrValidationReport:  # type: ignore[override]
        return AdrValidationReport(
            valid=True,
            total=3,
            errors=0,
            warnings=0,
            issues=[],
        )


class _FakeAdrServiceEmpty(AdrServicePort):
    """Fake AdrServicePort returning no ADRs."""

    def list_adrs(self) -> list[AdrInfo]:  # type: ignore[override]
        return []

    def get_adr(self, number: int) -> AdrDocument:  # type: ignore[override]
        raise FileNotFoundError(f"ADR-{number:03d} not found")

    def validate(self) -> AdrValidationReport:  # type: ignore[override]
        return AdrValidationReport(
            valid=False,
            total=0,
            errors=2,
            warnings=1,
            issues=[
                AdrValidationIssue(
                    number=5,
                    path="/docs/ADR-005.md",
                    message="Missing status field",
                    severity="error",
                ),
                AdrValidationIssue(
                    number=None,
                    path="/docs/unknown.md",
                    message="Malformed header",
                    severity="warning",
                ),
            ],
        )


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


def _patch_adr_service(monkeypatch: Any, fake_service: AdrServicePort) -> None:
    """Monkeypatch get_adr_service in the adr command module."""
    import bioetl.interfaces.cli.commands.adr as adr_cmd

    monkeypatch.setattr(adr_cmd, "get_adr_service", lambda: fake_service, raising=True)


# =============================================================================
# Tests for `adr list`
# =============================================================================


@pytest.mark.unit
class TestAdrListCommand:
    """Tests for `adr list` command."""

    def test_list_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that adr list --help shows options."""
        result = cli_runner.invoke(cli, ["adr", "list", "--help"])

        assert result.exit_code == 0
        assert "--json" in result.output

    def test_list_plain_shows_all_adrs(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test plain list output contains all ADR titles."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceWithItems())

        result = cli_runner.invoke(cli, ["adr", "list"])

        assert result.exit_code == 0
        assert "ADR-001" in result.output
        assert "Use Hexagonal Architecture" in result.output
        assert "ADR-002" in result.output
        assert "Use Delta Lake for Silver" in result.output
        assert "ADR-026" in result.output

    def test_list_plain_empty_shows_no_documents_message(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that empty ADR list shows appropriate message."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceEmpty())

        result = cli_runner.invoke(cli, ["adr", "list"])

        assert result.exit_code == 0
        assert "No ADR documents found" in result.output

    def test_list_json_output_contains_number_and_title(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that --json flag produces valid JSON with number and title fields."""
        import json

        _patch_adr_service(monkeypatch, _FakeAdrServiceWithItems())

        result = cli_runner.invoke(cli, ["adr", "list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3
        assert data[0]["number"] == 1
        assert data[0]["title"] == "Use Hexagonal Architecture"
        assert "path" in data[0]

    def test_list_json_empty_returns_empty_array(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that --json flag with empty list returns empty JSON array."""
        import json

        _patch_adr_service(monkeypatch, _FakeAdrServiceEmpty())

        result = cli_runner.invoke(cli, ["adr", "list", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data == []


# =============================================================================
# Tests for `adr show`
# =============================================================================


@pytest.mark.unit
class TestAdrShowCommand:
    """Tests for `adr show` command."""

    def test_show_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that adr show --help shows options."""
        result = cli_runner.invoke(cli, ["adr", "show", "--help"])

        assert result.exit_code == 0
        assert "--raw" in result.output

    def test_show_existing_adr_displays_title_and_status(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that showing an existing ADR displays title, status, and preview."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceWithItems())

        result = cli_runner.invoke(cli, ["adr", "show", "1"])

        assert result.exit_code == 0
        assert "ADR-001" in result.output
        assert "Use Hexagonal Architecture" in result.output
        assert "Accepted" in result.output
        assert "2024-01-01" in result.output

    def test_show_existing_adr_without_date(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that showing an ADR without date field still works."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceWithItems())

        result = cli_runner.invoke(cli, ["adr", "show", "2"])

        assert result.exit_code == 0
        assert "ADR-002" in result.output
        assert "Use Delta Lake for Silver" in result.output

    def test_show_raw_flag_outputs_content_only(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that --raw flag outputs raw markdown content."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceWithItems())

        result = cli_runner.invoke(cli, ["adr", "show", "--raw", "1"])

        assert result.exit_code == 0
        assert "# ADR-001" in result.output

    def test_show_nonexistent_adr_shows_error_message(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that showing non-existent ADR shows an error message."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceWithItems())

        result = cli_runner.invoke(cli, ["adr", "show", "999"])

        assert result.exit_code == 0  # echo_error does not set exit code
        assert "ADR not found" in result.output or "not found" in result.output.lower()

    def test_show_content_preview_first_40_lines(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that show displays first 40 lines of content as preview."""
        # Build content with more than 40 lines to verify truncation
        long_content = "# ADR-001\n\n" + "\n".join(f"Line {i}" for i in range(60))

        class _ServiceWithLongContent(AdrServicePort):
            def list_adrs(self) -> list[AdrInfo]:  # type: ignore[override]
                return []

            def get_adr(self, number: int) -> AdrDocument:  # type: ignore[override]
                return AdrDocument(
                    number=1,
                    title="Long ADR",
                    content=long_content,
                    path="/docs/ADR-001.md",
                    status="Accepted",
                    date="2024-01-01",
                )

            def validate(self) -> AdrValidationReport:  # type: ignore[override]
                return AdrValidationReport(
                    valid=True, total=1, errors=0, warnings=0, issues=[]
                )

        _patch_adr_service(monkeypatch, _ServiceWithLongContent())

        result = cli_runner.invoke(cli, ["adr", "show", "1"])

        assert result.exit_code == 0
        # Line 59 is beyond the 40-line preview window - should not appear
        assert "Line 59" not in result.output


# =============================================================================
# Tests for `adr validate`
# =============================================================================


@pytest.mark.unit
class TestAdrValidateCommand:
    """Tests for `adr validate` command."""

    def test_validate_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that adr validate --help shows options."""
        result = cli_runner.invoke(cli, ["adr", "validate", "--help"])

        assert result.exit_code == 0
        assert "--json" in result.output

    def test_validate_ok_shows_success_status(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that valid ADR repo shows OK status."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceWithItems())

        result = cli_runner.invoke(cli, ["adr", "validate"])

        assert result.exit_code == 0
        assert "OK" in result.output
        assert "Total: 3" in result.output
        assert "Errors: 0" in result.output
        assert "Warnings: 0" in result.output

    def test_validate_failed_shows_failed_status_and_issues(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that invalid ADR repo shows FAILED status with issues."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceEmpty())

        result = cli_runner.invoke(cli, ["adr", "validate"])

        assert result.exit_code == 0
        assert "FAILED" in result.output
        assert "Errors: 2" in result.output
        assert "Warnings: 1" in result.output
        assert "Missing status field" in result.output
        assert "Malformed header" in result.output

    def test_validate_failed_formats_adr_number(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that issue with ADR number is formatted as ADR-005."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceEmpty())

        result = cli_runner.invoke(cli, ["adr", "validate"])

        assert result.exit_code == 0
        assert "ADR-005" in result.output

    def test_validate_failed_formats_unknown_adr_number(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that issue without ADR number is formatted as ADR-???."""
        _patch_adr_service(monkeypatch, _FakeAdrServiceEmpty())

        result = cli_runner.invoke(cli, ["adr", "validate"])

        assert result.exit_code == 0
        assert "ADR-???" in result.output

    def test_validate_json_valid_output_structure(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that --json flag produces valid JSON with expected structure."""
        import json

        _patch_adr_service(monkeypatch, _FakeAdrServiceWithItems())

        result = cli_runner.invoke(cli, ["adr", "validate", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is True
        assert data["total"] == 3
        assert data["errors"] == 0
        assert data["warnings"] == 0
        assert data["issues"] == []

    def test_validate_json_failed_output_contains_issues(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that --json flag with failures includes issues list."""
        import json

        _patch_adr_service(monkeypatch, _FakeAdrServiceEmpty())

        result = cli_runner.invoke(cli, ["adr", "validate", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["valid"] is False
        assert data["errors"] == 2
        assert data["warnings"] == 1
        assert len(data["issues"]) == 2
        # Check issue structure
        issue = data["issues"][0]
        assert "number" in issue
        assert "path" in issue
        assert "message" in issue
        assert "severity" in issue

    def test_validate_json_issue_with_none_number(
        self, cli_runner: CliRunner, monkeypatch: Any
    ) -> None:
        """Test that issue with number=None serializes to null in JSON."""
        import json

        _patch_adr_service(monkeypatch, _FakeAdrServiceEmpty())

        result = cli_runner.invoke(cli, ["adr", "validate", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        issues_with_none = [i for i in data["issues"] if i["number"] is None]
        assert len(issues_with_none) == 1
        assert issues_with_none[0]["message"] == "Malformed header"


# =============================================================================
# Tests for `adr` group help
# =============================================================================


@pytest.mark.unit
class TestAdrGroupHelp:
    """Tests for the adr group command."""

    def test_adr_help_shows_all_subcommands(self, cli_runner: CliRunner) -> None:
        """Test that adr --help shows list, show, and validate subcommands."""
        result = cli_runner.invoke(cli, ["adr", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output
        assert "show" in result.output
        assert "validate" in result.output
