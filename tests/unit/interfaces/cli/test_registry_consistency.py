"""CLI regression tests for the list-pipelines command."""

from __future__ import annotations

import re

from click.testing import CliRunner
import pytest


pytestmark = pytest.mark.unit

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
    """Regression tests for list-pipelines CLI output."""

    def test_list_pipelines_command_output(
        self,
        cli_runner: CliRunner,
    ) -> None:
        """CLI output should match the expected pipeline list."""
        from bioetl.interfaces.cli.main import cli

        result = cli_runner.invoke(
            cli,
            ["config", "list-pipelines"],
            color=False,
            env={"NO_COLOR": "1", "CLICOLOR": "0", "CLICOLOR_FORCE": "0"},
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert _normalize_cli_output(result.output) == (
            "Available pipelines:\n"
            "  - chembl_activity\n"
            "  - chembl_assay\n"
            "  - chembl_assay_parameters\n"
            "  - chembl_cell_line\n"
            "  - chembl_compound_record\n"
            "  - chembl_molecule\n"
            "  - chembl_protein_class\n"
            "  - chembl_publication\n"
            "  - chembl_publication_similarity\n"
            "  - chembl_publication_term\n"
            "  - chembl_subcellular_fraction\n"
            "  - chembl_target\n"
            "  - chembl_target_component\n"
            "  - chembl_target_protein_classification\n"
            "  - chembl_tissue\n"
            "  - crossref_publication\n"
            "  - openalex_publication\n"
            "  - pubchem_compound\n"
            "  - pubmed_publication\n"
            "  - semanticscholar_publication\n"
            "  - uniprot_idmapping\n"
            "  - uniprot_protein\n"
        )

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
