"""Base validation tests for Chembl Publication schema.

Tests regex patterns, nullable constraints, and type validation
for all 28 fields in ChemblPublicationSchema.

Generated from publication_validation_schema_v3.xlsx.
"""

import pytest
import pandas as pd
import pandera as pa
from typing import Any

from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from tests.unit.domain.schemas._schema_validation_assertions import (
    assert_schema_validates_frame,
)


@pytest.mark.unit
class TestPmidBaseValidation:
    """Base validation tests for pmid."""

    def test_pmid_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid pmid value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_pmid_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmid is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["pmid"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)

    @pytest.mark.parametrize("invalid_value", ["-1", "abc", ""])
    def test_pmid_invalid_format(
        self, minimal_chembl_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmid invalid format."""
        df = minimal_chembl_publication_df.copy()
        df["pmid"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            ChemblPublicationSchema.validate(df)


@pytest.mark.unit
class TestDoiBaseValidation:
    """Base validation tests for doi."""

    def test_doi_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid doi value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_doi_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: doi is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["doi"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)

    @pytest.mark.parametrize(
        "invalid_value", ["doi:10.1234", "10.123/x", "not-a-doi", ""]
    )
    def test_doi_invalid_format(
        self, minimal_chembl_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: doi invalid format."""
        df = minimal_chembl_publication_df.copy()
        df["doi"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            ChemblPublicationSchema.validate(df)


@pytest.mark.unit
class TestPmcIdBaseValidation:
    """Base validation tests for pmc_id."""

    def test_pmc_id_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid pmc_id value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_pmc_id_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmc_id is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["pmc_id"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)

    @pytest.mark.parametrize("invalid_value", ["pmc123", "PMC", "123", ""])
    def test_pmc_id_invalid_format(
        self, minimal_chembl_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmc_id invalid format."""
        df = minimal_chembl_publication_df.copy()
        df["pmc_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            ChemblPublicationSchema.validate(df)


@pytest.mark.unit
class TestTitleBaseValidation:
    """Base validation tests for title."""

    def test_title_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid title value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_title_null_fails(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: title is non-nullable for ChemblPublicationSchema."""
        df = minimal_chembl_publication_df.copy()
        df["title"] = None
        with pytest.raises(pa.errors.SchemaError, match="title"):
            ChemblPublicationSchema.validate(df)


@pytest.mark.unit
class TestAbstractBaseValidation:
    """Base validation tests for abstract."""

    def test_abstract_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid abstract value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_abstract_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: abstract is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["abstract"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestAuthorsBaseValidation:
    """Base validation tests for authors."""

    def test_authors_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid authors value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_authors_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: authors is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["authors"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestAffiliationListBaseValidation:
    """Base validation tests for affiliation_list."""

    def test_affiliation_list_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid affiliation_list value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_affiliation_list_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: affiliation_list is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["affiliation_list"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestJournalBaseValidation:
    """Base validation tests for journal."""

    def test_journal_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid journal value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_journal_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["journal"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestPublicationYearBaseValidation:
    """Base validation tests for publication_year."""

    def test_publication_year_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_year value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_publication_year_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_year is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["publication_year"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestPublicationDateBaseValidation:
    """Base validation tests for publication_date."""

    def test_publication_date_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_date value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_publication_date_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_date is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["publication_date"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestPublicationTypeBaseValidation:
    """Base validation tests for publication_type."""

    def test_publication_type_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_type value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_publication_type_null_fails(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: publication_type is non-nullable for ChemblPublicationSchema."""
        df = minimal_chembl_publication_df.copy()
        df["publication_type"] = None
        with pytest.raises(pa.errors.SchemaError, match="publication_type"):
            ChemblPublicationSchema.validate(df)


@pytest.mark.unit
class TestLanguageBaseValidation:
    """Base validation tests for language."""

    def test_language_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid language value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_language_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: language is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["language"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestPageFirstBaseValidation:
    """Base validation tests for page_first."""

    def test_page_first_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_first value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_page_first_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_first is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["page_first"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestPageLastBaseValidation:
    """Base validation tests for page_last."""

    def test_page_last_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid page_last value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_page_last_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_last is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["page_last"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestCitationsReceivedBaseValidation:
    """Base validation tests for citations_received."""

    def test_citations_received_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_received value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_citations_received_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_received is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["citations_received"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestCitationsMadeBaseValidation:
    """Base validation tests for citations_made."""

    def test_citations_made_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_made value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_citations_made_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_made is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["citations_made"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestIsOaBaseValidation:
    """Base validation tests for is_oa."""

    def test_is_oa_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid is_oa value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_is_oa_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: is_oa is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["is_oa"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestLookupMethodBaseValidation:
    """Base validation tests for lookup_method."""

    def test_lookup_method_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid lookup_method value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_lookup_method_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: lookup_method is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["lookup_method"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestOriginalIdBaseValidation:
    """Base validation tests for original_id."""

    def test_original_id_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid original_id value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_original_id_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: original_id is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["original_id"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestSourceBaseValidation:
    """Base validation tests for _source."""

    def test__source_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid _source value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test__source_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: _source is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["_source"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestDocumentChemblIdBaseValidation:
    """Base validation tests for publication_id."""

    def test_publication_id_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_id value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_publication_id_null_fails(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: publication_id is non-nullable(PK)."""
        df = minimal_chembl_publication_df.copy()
        df["publication_id"] = None
        with pytest.raises(pa.errors.SchemaError, match="publication_id"):
            ChemblPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["chembl25", "CHEMBL", ""])
    def test_publication_id_invalid_format(
        self, minimal_chembl_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: publication_id invalid format."""
        df = minimal_chembl_publication_df.copy()
        df["publication_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            ChemblPublicationSchema.validate(df)


@pytest.mark.unit
class TestSrcIdBaseValidation:
    """Base validation tests for src_id."""

    def test_src_id_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid src_id value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_src_id_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: src_id is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["src_id"] = pd.array([pd.NA], dtype=pd.Int64Dtype())
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestChemblReleaseBaseValidation:
    """Base validation tests for chembl_release."""

    def test_chembl_release_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid chembl_release value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_chembl_release_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: chembl_release is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["chembl_release"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestCreationDateBaseValidation:
    """Base validation tests for creation_date."""

    def test_creation_date_valid(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid creation_date value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_creation_date_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: creation_date is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["creation_date"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestVolumeBaseValidation:
    """Base validation tests for volume."""

    def test_volume_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid volume value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_volume_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: volume is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["volume"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestIssueBaseValidation:
    """Base validation tests for issue."""

    def test_issue_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid issue value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test_issue_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issue is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["issue"] = None
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestDqWarnBaseValidation:
    """Base validation tests for _dq_warn."""

    def test__dq_warn_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid _dq_warn value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test__dq_warn_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: _dq_warn is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["_dq_warn"] = pd.array([pd.NA], dtype=pd.BooleanDtype())
        assert_schema_validates_frame(ChemblPublicationSchema, df)


@pytest.mark.unit
class TestDqErrorBaseValidation:
    """Base validation tests for _dq_error."""

    def test__dq_error_valid(self, minimal_chembl_publication_df: pd.DataFrame) -> None:
        """PASS: valid _dq_error value."""
        assert_schema_validates_frame(
            ChemblPublicationSchema, minimal_chembl_publication_df
        )

    def test__dq_error_null_allowed(
        self, minimal_chembl_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: _dq_error is nullable."""
        df = minimal_chembl_publication_df.copy()
        df["_dq_error"] = pd.array([pd.NA], dtype=pd.BooleanDtype())
        assert_schema_validates_frame(ChemblPublicationSchema, df)
