from __future__ import annotations

from typing import Any

import pytest
from click.testing import CliRunner

from bioetl.domain.ports.adr import AdrInfo, AdrServicePort, AdrValidationReport
from bioetl.interfaces.cli.main import cli


@pytest.fixture()
def cli_runner() -> CliRunner:
    return CliRunner()


class _FakeAdrService(AdrServicePort):
    def list_adrs(self) -> list[AdrInfo]:  # type: ignore[override]
        return [AdrInfo(number=1, title="Test ADR", path="/tmp/ADR-001-test.md")]

    def get_adr(self, number: int):  # type: ignore[override]
        raise FileNotFoundError("not implemented in fake")

    def validate(self) -> AdrValidationReport:  # type: ignore[override]
        return AdrValidationReport(valid=True, total=1, errors=0, warnings=0, issues=[])


def test_adr_help_displays_subcommands(cli_runner: CliRunner) -> None:
    result = cli_runner.invoke(cli, ["adr", "--help"])  # type: ignore[arg-type]
    assert result.exit_code == 0
    assert "list" in result.output
    assert "show" in result.output
    assert "validate" in result.output


def test_adr_list_json_uses_service(monkeypatch: Any, cli_runner: CliRunner) -> None:
    # Monkeypatch the symbol imported by the CLI command module
    import bioetl.interfaces.cli.commands.adr as adr_cmd

    monkeypatch.setattr(
        adr_cmd,
        "get_adr_service",
        lambda: _FakeAdrService(),
        raising=True,
    )

    result = cli_runner.invoke(cli, ["adr", "list", "--json"])  # type: ignore[arg-type]
    assert result.exit_code == 0
    assert '"number": 1' in result.output
    assert "Test ADR" in result.output
