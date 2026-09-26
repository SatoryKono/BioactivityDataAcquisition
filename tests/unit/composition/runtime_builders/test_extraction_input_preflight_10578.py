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
"""Unit tests for extraction input preflight (#10578)."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.runtime_builders.inputs_resolution_orchestration import (
    ExtractionInputError,
    validate_resolved_extraction_input,
)
from bioetl.domain.filtering import InputFilterConfig

pytestmark = pytest.mark.unit


def test_chembl_full_scan_pipelines_skip_required_input_gate() -> None:
    assert (
        validate_resolved_extraction_input(
            pipeline_name="chembl_activity",
            provider="chembl",
            query=None,
            filter_config=None,
        )
        is None
    )


def test_query_mode_accepted_for_crossref() -> None:
    provenance = validate_resolved_extraction_input(
        pipeline_name="crossref_publication",
        provider="crossref",
        query=" aspirin ",
        filter_config=None,
    )
    assert provenance is not None
    assert provenance.input_kind == "query"


def test_missing_query_and_filter_rejected() -> None:
    with pytest.raises(ExtractionInputError, match="requires either filter IDs"):
        validate_resolved_extraction_input(
            pipeline_name="openalex_publication",
            provider="openalex",
            query="   ",
            filter_config=None,
        )


def test_direct_filter_ids_accepted() -> None:
    config = InputFilterConfig(
        enabled=True,
        filter_field="doi",
        direct_filter_ids=("10.1000/xyz",),
    )
    provenance = validate_resolved_extraction_input(
        pipeline_name="crossref_publication",
        provider="crossref",
        query=None,
        filter_config=config,
    )
    assert provenance is not None
    assert provenance.input_kind == "direct_filter_ids"
    assert provenance.id_count == 1


def test_absent_csv_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing-dois.csv"
    config = InputFilterConfig(
        enabled=True,
        source_path=str(missing),
        column_name="doi",
        filter_field="doi",
    )
    with pytest.raises(ExtractionInputError, match="CSV is absent"):
        validate_resolved_extraction_input(
            pipeline_name="crossref_publication",
            provider="crossref",
            query=None,
            filter_config=config,
        )


def test_missing_column_rejected(tmp_path: Path) -> None:
    csv_path = tmp_path / "dois.csv"
    csv_path.write_text("title\nhello\n", encoding="utf-8")
    config = InputFilterConfig(
        enabled=True,
        source_path=str(csv_path),
        column_name="doi",
        filter_field="doi",
    )
    with pytest.raises(ExtractionInputError, match="missing required column"):
        validate_resolved_extraction_input(
            pipeline_name="openalex_publication",
            provider="openalex",
            query=None,
            filter_config=config,
        )


def test_empty_id_column_rejected(tmp_path: Path) -> None:
    csv_path = tmp_path / "dois.csv"
    csv_path.write_text("doi\n\n  \n", encoding="utf-8")
    config = InputFilterConfig(
        enabled=True,
        source_path=str(csv_path),
        column_name="doi",
        filter_field="doi",
    )
    with pytest.raises(ExtractionInputError, match="no non-empty IDs"):
        validate_resolved_extraction_input(
            pipeline_name="crossref_publication",
            provider="crossref",
            query=None,
            filter_config=config,
        )


def test_valid_csv_accepted_and_counts_ids(tmp_path: Path) -> None:
    csv_path = tmp_path / "molecule.csv"
    csv_path.write_text(
        "canonical_smiles\nCCO\nCCN\n\n",
        encoding="utf-8",
    )
    config = InputFilterConfig(
        enabled=True,
        source_path=str(csv_path),
        column_name="canonical_smiles",
        filter_field="smiles",
    )
    provenance = validate_resolved_extraction_input(
        pipeline_name="pubchem_compound",
        provider="pubchem",
        query=None,
        filter_config=config,
    )
    assert provenance is not None
    assert provenance.input_kind == "csv_filter_ids"
    assert provenance.source_path == str(csv_path)
    assert provenance.column_name == "canonical_smiles"
    assert provenance.id_count == 2


def test_cli_csv_path_wins_over_default_yaml_path(tmp_path: Path) -> None:
    """Resolved filter_config already prefers CLI; preflight checks that path."""
    cli_csv = tmp_path / "cli-dois.csv"
    cli_csv.write_text("doi\n10.1000/cli\n", encoding="utf-8")
    # Simulates FilterConfigBuilder.build(cli_csv=...) winning over YAML default.
    config = InputFilterConfig(
        enabled=True,
        source_path=str(cli_csv),
        column_name="doi",
        filter_field="doi",
    )
    provenance = validate_resolved_extraction_input(
        pipeline_name="crossref_publication",
        provider="crossref",
        query=None,
        filter_config=config,
    )
    assert provenance is not None
    assert provenance.source_path == str(cli_csv)
    assert provenance.id_count == 1
