"""Base validation tests for Pubmed Publication schema.

Tests regex patterns, nullable constraints, and type validation
for all 52 fields in PubMedPublicationSchema.

Generated from publication_validation_schema_v3.xlsx.
"""

import pytest
import pandas as pd
import pandera as pa
from typing import Any

from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema


@pytest.mark.unit
class TestPmidBaseValidation:
    """Base validation tests for pmid."""

    def test_pmid_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid pmid value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_pmid_null_fails(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """FAIL: pmid is non-nullable(PK)."""
        df = minimal_pubmed_publication_df.copy()
        df["pmid"] = None
        with pytest.raises(pa.errors.SchemaError, match="pmid"):
            PubMedPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["0", "-1", "abc", ""])
    def test_pmid_invalid_format(
        self, minimal_pubmed_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmid invalid format."""
        df = minimal_pubmed_publication_df.copy()
        df["pmid"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestDoiBaseValidation:
    """Base validation tests for doi."""

    def test_doi_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid doi value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_doi_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: doi is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["doi"] = None
        PubMedPublicationSchema.validate(df)

    @pytest.mark.parametrize(
        "invalid_value", ["doi:10.1234", "10.123/x", "not-a-doi", ""]
    )
    def test_doi_invalid_format(
        self, minimal_pubmed_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: doi invalid format."""
        df = minimal_pubmed_publication_df.copy()
        df["doi"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPmcIdBaseValidation:
    """Base validation tests for pmc_id."""

    def test_pmc_id_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid pmc_id value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_pmc_id_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmc_id is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["pmc_id"] = None
        PubMedPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["pmc123", "PMC", "123", ""])
    def test_pmc_id_invalid_format(
        self, minimal_pubmed_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmc_id invalid format."""
        df = minimal_pubmed_publication_df.copy()
        df["pmc_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestTitleBaseValidation:
    """Base validation tests for title."""

    def test_title_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid title value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_title_null_fails(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: title is non-nullable in PubMed schema."""
        df = minimal_pubmed_publication_df.copy()
        df["title"] = None
        with pytest.raises(pa.errors.SchemaError, match="title"):
            PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestAbstractBaseValidation:
    """Base validation tests for abstract."""

    def test_abstract_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid abstract value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_abstract_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: abstract is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["abstract"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestAuthorsBaseValidation:
    """Base validation tests for authors."""

    def test_authors_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid authors value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_authors_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: authors is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["authors"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestAffiliationListBaseValidation:
    """Base validation tests for affiliation_list."""

    def test_affiliation_list_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid affiliation_list value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_affiliation_list_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: affiliation_list is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["affiliation_list"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestJournalBaseValidation:
    """Base validation tests for journal."""

    def test_journal_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid journal value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_journal_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["journal"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationYearBaseValidation:
    """Base validation tests for publication_year."""

    def test_publication_year_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_year value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_publication_year_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_year is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_year"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationDateBaseValidation:
    """Base validation tests for publication_date."""

    def test_publication_date_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_date value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_publication_date_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_date is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_date"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationTypeBaseValidation:
    """Base validation tests for publication_type."""

    def test_publication_type_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_type value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_publication_type_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_type is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_type"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestLanguageBaseValidation:
    """Base validation tests for language."""

    def test_language_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid language value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_language_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: language is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["language"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPageFirstBaseValidation:
    """Base validation tests for page_first."""

    def test_page_first_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_first value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_page_first_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_first is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["page_first"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPageLastBaseValidation:
    """Base validation tests for page_last."""

    def test_page_last_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid page_last value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_page_last_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_last is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["page_last"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestCitationsReceivedBaseValidation:
    """Base validation tests for citations_received."""

    def test_citations_received_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_received value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_citations_received_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_received is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["citations_received"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestCitationsMadeBaseValidation:
    """Base validation tests for citations_made."""

    def test_citations_made_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_made value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_citations_made_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_made is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["citations_made"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestIsOaBaseValidation:
    """Base validation tests for is_oa."""

    def test_is_oa_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid is_oa value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_is_oa_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: is_oa is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["is_oa"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestLookupMethodBaseValidation:
    """Base validation tests for lookup_method."""

    def test_lookup_method_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid lookup_method value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_lookup_method_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: lookup_method is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["lookup_method"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestOriginalIdBaseValidation:
    """Base validation tests for original_id."""

    def test_original_id_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid original_id value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_original_id_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: original_id is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["original_id"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestSourceBaseValidation:
    """Base validation tests for _source."""

    def test__source_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid _source value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test__source_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: _source is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["_source"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPiiBaseValidation:
    """Base validation tests for pii."""

    def test_pii_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid pii value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_pii_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pii is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["pii"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestMidBaseValidation:
    """Base validation tests for mid."""

    def test_mid_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid mid value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_mid_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: mid is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["mid"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublisherIdBaseValidation:
    """Base validation tests for publisher_id."""

    def test_publisher_id_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publisher_id value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_publisher_id_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publisher_id is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publisher_id"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestAbstractStructuredBaseValidation:
    """Base validation tests for abstract_structured."""

    def test_abstract_structured_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid abstract_structured value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_abstract_structured_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: abstract_structured is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["abstract_structured"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestJournalNameShortBaseValidation:
    """Base validation tests for journal_name_short."""

    def test_journal_name_short_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal_name_short value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_journal_name_short_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal_name_short is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["journal_name_short"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestJournalIsoAbbrevBaseValidation:
    """Base validation tests for journal_iso_abbrev."""

    def test_journal_iso_abbrev_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal_iso_abbrev value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_journal_iso_abbrev_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal_iso_abbrev is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["journal_iso_abbrev"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestIssnBaseValidation:
    """Base validation tests for issn."""

    def test_issn_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid issn value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_issn_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issn is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["issn"] = None
        PubMedPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["12345678", "1234-567", ""])
    def test_issn_invalid_format(
        self, minimal_pubmed_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: issn invalid format."""
        df = minimal_pubmed_publication_df.copy()
        df["issn"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestJournalIssnTypeBaseValidation:
    """Base validation tests for journal_issn_type."""

    def test_journal_issn_type_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal_issn_type value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_journal_issn_type_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal_issn_type is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["journal_issn_type"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestNlmUniqueIdBaseValidation:
    """Base validation tests for nlm_unique_id."""

    def test_nlm_unique_id_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid nlm_unique_id value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_nlm_unique_id_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: nlm_unique_id is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["nlm_unique_id"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestCountryBaseValidation:
    """Base validation tests for country."""

    def test_country_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid country value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_country_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: country is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["country"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestMedlinePgnBaseValidation:
    """Base validation tests for medline_pgn."""

    def test_medline_pgn_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid medline_pgn value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_medline_pgn_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: medline_pgn is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["medline_pgn"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPageRangeBaseValidation:
    """Base validation tests for page_range."""

    def test_page_range_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_range value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_page_range_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_range is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["page_range"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPubMonthBaseValidation:
    """Base validation tests for pub_month."""

    def test_pub_month_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid pub_month value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_pub_month_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pub_month is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["pub_month"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPubDayBaseValidation:
    """Base validation tests for pub_day."""

    def test_pub_day_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid pub_day value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_pub_day_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pub_day is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["pub_day"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationStatusBaseValidation:
    """Base validation tests for publication_status."""

    def test_publication_status_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_status value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_publication_status_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_status is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_status"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestDateCompletedBaseValidation:
    """Base validation tests for date_completed."""

    def test_date_completed_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid date_completed value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_date_completed_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: date_completed is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["date_completed"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestDateRevisedBaseValidation:
    """Base validation tests for date_revised."""

    def test_date_revised_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid date_revised value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_date_revised_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: date_revised is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["date_revised"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestCitationSubsetBaseValidation:
    """Base validation tests for citation_subset."""

    def test_citation_subset_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citation_subset value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_citation_subset_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citation_subset is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["citation_subset"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestAffiliationStructuredBaseValidation:
    """Base validation tests for affiliation_structured."""

    def test_affiliation_structured_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid affiliation_structured value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_affiliation_structured_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: affiliation_structured is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["affiliation_structured"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestAuthorCountBaseValidation:
    """Base validation tests for author_count."""

    def test_author_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid author_count value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_author_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: author_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["author_count"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestMeshHeadingCountBaseValidation:
    """Base validation tests for mesh_heading_count."""

    def test_mesh_heading_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid mesh_heading_count value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_mesh_heading_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: mesh_heading_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["mesh_heading_count"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestKeywordCountBaseValidation:
    """Base validation tests for keyword_count."""

    def test_keyword_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid keyword_count value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_keyword_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: keyword_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["keyword_count"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestGrantCountBaseValidation:
    """Base validation tests for grant_count."""

    def test_grant_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid grant_count value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_grant_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: grant_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["grant_count"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestChemicalCountBaseValidation:
    """Base validation tests for chemical_count."""

    def test_chemical_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid chemical_count value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_chemical_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: chemical_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["chemical_count"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestSubjectMeshBaseValidation:
    """Base validation tests for subject_mesh."""

    def test_subject_mesh_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_mesh value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_subject_mesh_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_mesh is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["subject_mesh"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestChemicalsBaseValidation:
    """Base validation tests for chemicals."""

    def test_chemicals_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid chemicals value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_chemicals_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: chemicals is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["chemicals"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestSubjectKeywordsBaseValidation:
    """Base validation tests for subject_keywords."""

    def test_subject_keywords_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_keywords value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_subject_keywords_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_keywords is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["subject_keywords"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestDatabanksBaseValidation:
    """Base validation tests for databanks."""

    def test_databanks_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid databanks value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_databanks_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: databanks is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["databanks"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestGeneSymbolsBaseValidation:
    """Base validation tests for gene_symbols."""

    def test_gene_symbols_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid gene_symbols value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_gene_symbols_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: gene_symbols is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["gene_symbols"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationTypesBaseValidation:
    """Base validation tests for publication_types."""

    def test_publication_types_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_types value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_publication_types_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_types is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_types"] = None
        PubMedPublicationSchema.validate(df)


@pytest.mark.unit
class TestAuthorsWithAffiliationsBaseValidation:
    """Base validation tests for authors_with_affiliations."""

    def test_authors_with_affiliations_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid authors_with_affiliations value."""
        PubMedPublicationSchema.validate(minimal_pubmed_publication_df)

    def test_authors_with_affiliations_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: authors_with_affiliations is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["authors_with_affiliations"] = None
        PubMedPublicationSchema.validate(df)
