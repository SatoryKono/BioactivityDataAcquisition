"""Tests for ColumnRenamer service."""

import polars as pl
import pytest
from unittest.mock import MagicMock

from bioetl.application.composite.column_renamer import ColumnRenamer


pytestmark = pytest.mark.unit

@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def renamer(mock_logger: MagicMock) -> ColumnRenamer:
    """Create ColumnRenamer instance."""
    return ColumnRenamer(mock_logger)


class TestColumnRenamer:
    """Tests for ColumnRenamer."""

    def test_rename_all_business_columns(self, renamer: ColumnRenamer) -> None:
        """All business columns get qualified names."""
        df = pl.DataFrame(
            {
                "title": ["T1"],
                "abstract": ["A1"],
                "journal": ["J1"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert "chembl.publication.title" in result.columns
        assert "chembl.publication.abstract" in result.columns
        assert "chembl.publication.journal" in result.columns

    def test_exclude_join_keys_by_default(self, renamer: ColumnRenamer) -> None:
        """Join keys are not renamed by default."""
        df = pl.DataFrame(
            {
                "doi": ["10.1/a"],
                "pmid": ["123"],
                "pmc_id": ["PMC456"],
                "title": ["T1"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert "doi" in result.columns
        assert "pmid" in result.columns
        assert "pmc_id" in result.columns
        assert "chembl.publication.title" in result.columns

    def test_include_join_keys_when_disabled(self, renamer: ColumnRenamer) -> None:
        """Join keys are renamed when exclude_join_keys=False."""
        df = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"]})
        result = renamer.rename_dataframe(
            df, "chembl_publication", exclude_join_keys=False
        )

        assert "chembl.publication.doi" in result.columns
        assert "chembl.publication.title" in result.columns

    def test_skip_system_columns(self, renamer: ColumnRenamer) -> None:
        """System columns (starting with _) are not renamed."""
        df = pl.DataFrame(
            {
                "_run_id": ["r1"],
                "_ingestion_ts": ["2025-01-01"],
                "title": ["T1"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert "_run_id" in result.columns
        assert "_ingestion_ts" in result.columns
        assert "chembl.publication.title" in result.columns

    def test_skip_already_qualified(self, renamer: ColumnRenamer) -> None:
        """Already qualified columns are not renamed."""
        df = pl.DataFrame(
            {
                "crossref.publication.title": ["T1"],
                "abstract": ["A1"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert "crossref.publication.title" in result.columns
        assert "chembl.publication.abstract" in result.columns

    def test_renamer_column_renamer__empty_dataframe__aa0ada54(self, renamer: ColumnRenamer) -> None:
        """Empty DataFrame returns empty DataFrame."""
        df = pl.DataFrame()
        result = renamer.rename_dataframe(df, "chembl_publication")
        assert len(result.columns) == 0

    def test_build_rename_map(self, renamer: ColumnRenamer) -> None:
        """Build correct rename mapping."""
        columns = ["title", "doi", "_run_id", "chembl.activity.name"]
        mapping = renamer.build_rename_map(columns, "chembl_publication")

        assert mapping == {"title": "chembl.publication.title"}

    def test_parse_pipeline_valid(self, renamer: ColumnRenamer) -> None:
        """Parse valid pipeline name."""
        provider, entity = renamer._parse_pipeline("chembl_publication")
        assert provider == "chembl"
        assert entity == "publication"

    def test_parse_pipeline_invalid(self, renamer: ColumnRenamer) -> None:
        """Reject pipeline without underscore."""
        with pytest.raises(ValueError, match="must be in format"):
            renamer._parse_pipeline("chemblpublication")

    def test_case_insensitive_join_keys(self, renamer: ColumnRenamer) -> None:
        """Join key detection is case-insensitive."""
        df = pl.DataFrame({"DOI": ["10.1/a"], "PMID": ["123"]})
        result = renamer.rename_dataframe(df, "chembl_publication")

        # Original case preserved but not renamed
        assert "DOI" in result.columns
        assert "PMID" in result.columns

    def test_data_preserved_after_rename(self, renamer: ColumnRenamer) -> None:
        """Data values are preserved after renaming."""
        df = pl.DataFrame(
            {
                "title": ["Title 1", "Title 2"],
                "doi": ["10.1/a", "10.1/b"],
            }
        )
        result = renamer.rename_dataframe(df, "chembl_publication")

        assert result["chembl.publication.title"].to_list() == ["Title 1", "Title 2"]
        assert result["doi"].to_list() == ["10.1/a", "10.1/b"]

    def test_normalization_to_lowercase(self, renamer: ColumnRenamer) -> None:
        """Provider and entity are normalized to lowercase."""
        df = pl.DataFrame({"title": ["T1"]})
        result = renamer.rename_dataframe(df, "ChEMBL_Publication")

        assert "chembl.publication.title" in result.columns


class TestColumnRenamerFieldAliases:
    """Tests for ColumnRenamer with field alias support."""

    def test_alias_normalizes_field_name(self, renamer: ColumnRenamer) -> None:
        """Field aliases should normalize provider-specific names to canonical."""
        df = pl.DataFrame(
            {
                "h_bond_acceptor_count": [5],
                "molecular_weight": [180.0],
            }
        )
        aliases = {"h_bond_acceptor_count": "hba_count"}
        result = renamer.rename_dataframe(df, "pubchem_compound", field_aliases=aliases)

        assert "pubchem.compound.hba_count" in result.columns
        assert "pubchem.compound.molecular_weight" in result.columns
        assert "pubchem.compound.h_bond_acceptor_count" not in result.columns

    def test_alias_preserves_data_values(self, renamer: ColumnRenamer) -> None:
        """Data should be preserved after alias-based renaming."""
        df = pl.DataFrame(
            {
                "h_bond_acceptor_count": [5, 3],
                "h_bond_donor_count": [2, 1],
            }
        )
        aliases = {
            "h_bond_acceptor_count": "hba_count",
            "h_bond_donor_count": "hbd_count",
        }
        result = renamer.rename_dataframe(df, "pubchem_compound", field_aliases=aliases)

        assert result["pubchem.compound.hba_count"].to_list() == [5, 3]
        assert result["pubchem.compound.hbd_count"].to_list() == [2, 1]

    def test_alias_multiple_fields(self, renamer: ColumnRenamer) -> None:
        """Multiple field aliases should all be applied."""
        df = pl.DataFrame(
            {
                "h_bond_acceptor_count": [5],
                "h_bond_donor_count": [2],
                "tpsa": [75.0],
                "xlogp": [1.5],
                "inchi": ["InChI=1S/C6H12O6/..."],
            }
        )
        aliases = {
            "h_bond_acceptor_count": "hba_count",
            "h_bond_donor_count": "hbd_count",
            "tpsa": "polar_surface_area",
            "xlogp": "logp",
            "inchi": "standard_inchi",
        }
        result = renamer.rename_dataframe(df, "pubchem_compound", field_aliases=aliases)

        assert "pubchem.compound.hba_count" in result.columns
        assert "pubchem.compound.hbd_count" in result.columns
        assert "pubchem.compound.polar_surface_area" in result.columns
        assert "pubchem.compound.logp" in result.columns
        assert "pubchem.compound.standard_inchi" in result.columns

    def test_no_alias_passthrough(self, renamer: ColumnRenamer) -> None:
        """Fields not in alias map should pass through unchanged."""
        df = pl.DataFrame({"molecular_weight": [180.0]})
        aliases = {"h_bond_acceptor_count": "hba_count"}  # No mapping for MW
        result = renamer.rename_dataframe(df, "pubchem_compound", field_aliases=aliases)

        assert "pubchem.compound.molecular_weight" in result.columns

    def test_none_aliases_no_effect(self, renamer: ColumnRenamer) -> None:
        """None field_aliases should behave like no aliases (backward compat)."""
        df = pl.DataFrame({"h_bond_acceptor_count": [5]})
        result = renamer.rename_dataframe(df, "pubchem_compound", field_aliases=None)

        assert "pubchem.compound.h_bond_acceptor_count" in result.columns

    def test_empty_aliases_no_effect(self, renamer: ColumnRenamer) -> None:
        """Empty alias dict should behave like no aliases."""
        df = pl.DataFrame({"h_bond_acceptor_count": [5]})
        result = renamer.rename_dataframe(df, "pubchem_compound", field_aliases={})

        assert "pubchem.compound.h_bond_acceptor_count" in result.columns

    def test_build_rename_map_with_aliases(self, renamer: ColumnRenamer) -> None:
        """build_rename_map should apply aliases in the mapping."""
        columns = ["h_bond_acceptor_count", "molecular_weight", "_run_id"]
        aliases = {"h_bond_acceptor_count": "hba_count"}
        mapping = renamer.build_rename_map(
            columns,
            "pubchem_compound",
            exclude_join_keys=True,
            field_aliases=aliases,
        )

        assert mapping["h_bond_acceptor_count"] == "pubchem.compound.hba_count"
        assert mapping["molecular_weight"] == "pubchem.compound.molecular_weight"
        assert "_run_id" not in mapping
