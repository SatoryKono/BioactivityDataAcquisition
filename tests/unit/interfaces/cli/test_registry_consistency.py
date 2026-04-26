"""CLI regression tests for the list-pipelines command."""

from __future__ import annotations

import re

import pytest
from click.testing import CliRunner


_ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _normalize_cli_output(raw: str) -> str:
    """Normalize CLI text for stable snapshot comparisons across environments."""
    without_ansi = _ANSI_ESCAPE_RE.sub("", raw)
    normalized_newlines = without_ansi.replace("\r\n", "\n")
    trimmed_lines = "\n".join(line.rstrip() for line in normalized_newlines.split("\n"))
    return trimmed_lines.rstrip("\n") + "\n"


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


class TestListPipelinesCommandSnapshot:
    """Snapshot tests for list-pipelines CLI output."""

    def test_list_pipelines_command_output(
        self,
        cli_runner: CliRunner,
        request: pytest.FixtureRequest,
    ) -> None:
        """CLI output should match the stored list-pipelines snapshot.

        If the pipeline list changes intentionally, update the snapshot with:
            pytest tests/unit/interfaces/cli/test_registry_consistency.py --snapshot-update
        """
        pytest.importorskip("syrupy", reason="syrupy required for snapshot tests")
        snapshot = request.getfixturevalue("snapshot")

        from bioetl.interfaces.cli.main import cli

        result = cli_runner.invoke(
            cli,
            ["config", "list-pipelines"],
            color=False,
            env={"NO_COLOR": "1", "CLICOLOR": "0", "CLICOLOR_FORCE": "0"},
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
    assert _normalize_cli_output(result.output) == snapshot.lstrip()

    def test_list_pipelines_output_format(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """CLI output should retain the expected human-readable format."""
        from bioetl.interfaces.cli.main import cli

        result = cli_runner.invoke(
            cli,
            ["config", "list-pipelines"],
            color=False,
            env={"NO_COLOR": "1", "CLICOLOR": "0", "CLICOLOR_FORCE": "0"},
        )

        assert result.exit_code == 0
        assert "Available pipelines:" in result.output
        for pipeline in ("chembl_activity", "pubchem_compound", "uniprot_protein"):
            assert pipeline in result.output, f"Missing pipeline: {pipeline}"
