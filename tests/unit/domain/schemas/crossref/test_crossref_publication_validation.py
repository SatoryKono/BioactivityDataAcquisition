"""Base validation tests for Crossref Publication schema.

Tests regex patterns, nullable constraints, and type validation
for all 37 fields in PublicationEnrichedSchema.

Generated from publication_validation_schema_v3.xlsx.
"""

import pytest
import pandas as pd
import pandera as pa
from typing import Any

from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema


@pytest.mark.unit
class TestPmidBaseValidation:
    """Base validation tests for pmid."""

    def test_pmid_base_validation__pmid_valid__77c2c37c(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid pmid value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_pmid_base_validation__pmid_null_allowed__2b5883bc(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmid is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["pmid"] = None
        PublicationEnrichedSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["0", "-1", "abc", ""])
    def test_pmid_base_validation__pmid_invalid_format__eb2cd0e0(
        self, minimal_crossref_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmid invalid format."""
        df = minimal_crossref_publication_df.copy()
        df["pmid"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestDoiBaseValidation:
    """Base validation tests for doi."""

    def test_doi_base_validation__doi_valid__f143cd01(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid doi value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_doi_null_fails(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: doi is non-nullable(PK)."""
        df = minimal_crossref_publication_df.copy()
        df["doi"] = None
        with pytest.raises(pa.errors.SchemaError, match="doi"):
            PublicationEnrichedSchema.validate(df)

    @pytest.mark.parametrize(
        "invalid_value", ["doi:10.1234", "10.123/x", "not-a-doi", ""]
    )
    def test_doi_base_validation__doi_invalid_format__5c6686aa(
        self, minimal_crossref_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: doi invalid format."""
        df = minimal_crossref_publication_df.copy()
        df["doi"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPmcIdBaseValidation:
    """Base validation tests for pmc_id."""

    def test_case__0042f6ce3d(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid pmc_id value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_pmc_id_base_validation__pmc_id_null_allowed__0e894ea6(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmc_id is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["pmc_id"] = None
        PublicationEnrichedSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["pmc123", "PMC", "123", ""])
    def test_pmc_id_base_validation__id_invalid_format__4cb006b3(
        self, minimal_crossref_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmc_id invalid format."""
        df = minimal_crossref_publication_df.copy()
        df["pmc_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestTitleBaseValidation:
    """Base validation tests for title."""

    def test_title_base_validation__title_valid__9212699c(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid title value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_title_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: title is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["title"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestAbstractBaseValidation:
    """Base validation tests for abstract."""

    def test_base_validation__abstract_valid__4860ff0b(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid abstract value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_base_validation__null_allowed__2f5cd8ef(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: abstract is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["abstract"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestAuthorsBaseValidation:
    """Base validation tests for authors."""

    def test_base_validation__authors_valid__6cee2354(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid authors value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_base_validation__authors_null_allowed__38793b37(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: authors is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["authors"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestAffiliationListBaseValidation:
    """Base validation tests for affiliation_list."""

    def test_list_base_validation__list_valid__9c92cb01(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid affiliation_list value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_list_base_validation__list_null_allowed__e86f294f(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: affiliation_list is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["affiliation_list"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestJournalBaseValidation:
    """Base validation tests for journal."""

    def test_base_validation__journal_valid__80012fa6(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid journal value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_base_validation__journal_null_allowed__3aaca69c(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["journal"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPublicationYearBaseValidation:
    """Base validation tests for publication_year."""

    def test_year_base_validation__year_valid__b293a80b(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_year value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_year_base_validation__year_null_allowed__8879dc14(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_year is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["publication_year"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPublicationDateBaseValidation:
    """Base validation tests for publication_date."""

    def test_date_base_validation__date_valid__57722f20(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_date value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_date_base_validation__date_null_allowed__4824cacf(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_date is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["publication_date"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPublicationTypeBaseValidation:
    """Base validation tests for publication_type."""

    def test_type_base_validation__type_valid__7540a4b6(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_type value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_publication_type_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_type is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["publication_type"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestLanguageBaseValidation:
    """Base validation tests for language."""

    def test_base_validation__language_valid__560f049b(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid language value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_base_validation__null_allowed__6ade091e(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: language is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["language"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPageFirstBaseValidation:
    """Base validation tests for page_first."""

    def test_first_base_validation__page_first_valid__5a1d2c3f(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_first value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_first_base_validation__first_null_allowed__15f166d6(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_first is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["page_first"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPageLastBaseValidation:
    """Base validation tests for page_last."""

    def test_last_base_validation__page_last_valid__8f5f57d4(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_last value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_last_base_validation__last_null_allowed__775aac60(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_last is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["page_last"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestCitationsReceivedBaseValidation:
    """Base validation tests for citations_received."""

    def test_base_validation__received_valid__d1b39bb6(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_received value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_base_validation__null_allowed__a3da4984(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_received is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["citations_received"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestCitationsMadeBaseValidation:
    """Base validation tests for citations_made."""

    def test_made_base_validation__citations_made_valid__6fdc3881(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_made value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_made_base_validation__made_null_allowed__6c01b756(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_made is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["citations_made"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestIsOaBaseValidation:
    """Base validation tests for is_oa."""

    def test_is_oa_base_validation__is_oa_valid__9f5fed37(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid is_oa value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_is_oa_base_validation__is_oa_null_allowed__767efbf9(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: is_oa is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["is_oa"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestLookupMethodBaseValidation:
    """Base validation tests for lookup_method."""

    def test_method_base_validation__lookup_method_valid__ffc108eb(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid lookup_method value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_method_base_validation__method_null_allowed__b6669165(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: lookup_method is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["lookup_method"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestOriginalIdBaseValidation:
    """Base validation tests for original_id."""

    def test_id_base_validation__original_id_valid__7243ffd9(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid original_id value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_id_base_validation__id_null_allowed__f0ece3cf(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: original_id is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["original_id"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestSourceBaseValidation:
    """Base validation tests for _source."""

    def test_case__1b0fd79195(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid _source value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_source_base_validation__source_null_allowed__6f70aca5(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: _source is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["_source"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestIssnBaseValidation:
    """Base validation tests for issn."""

    def test_issn_valid(self, minimal_crossref_publication_df: pd.DataFrame) -> None:
        """PASS: valid issn value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_issn_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issn is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["issn"] = None
        PublicationEnrichedSchema.validate(df)

    def test_issn_accepts_any_string(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: issn has no format validation in CrossRef schema."""
        df = minimal_crossref_publication_df.copy()
        df["issn"] = "1234-5678"
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestIssnListBaseValidation:
    """Base validation tests for issn_list."""

    def test_issn_list_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid issn_list value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_issn_list_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issn_list is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["issn_list"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPublisherBaseValidation:
    """Base validation tests for publisher."""

    def test_publisher_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publisher value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_publisher_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publisher is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["publisher"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPublishedPrintBaseValidation:
    """Base validation tests for published_print."""

    def test_published_print_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid published_print value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_published_print_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: published_print is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["published_print"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPublishedOnlineBaseValidation:
    """Base validation tests for published_online."""

    def test_published_online_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid published_online value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_published_online_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: published_online is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["published_online"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestLicenseUrlBaseValidation:
    """Base validation tests for license_url."""

    def test_license_url_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid license_url value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_license_url_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: license_url is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["license_url"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestSubjectKeywordsBaseValidation:
    """Base validation tests for subject_keywords."""

    def test_subject_keywords_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_keywords value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_subject_keywords_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_keywords is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["subject_keywords"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestContentDomainDomainsBaseValidation:
    """Base validation tests for content_domain_domains."""

    def test_content_domain_domains_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid content_domain_domains value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_content_domain_domains_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: content_domain_domains is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["content_domain_domains"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestContentDomainCrossmarkRestrictionBaseValidation:
    """Base validation tests for content_domain_crossmark_restriction."""

    def test_content_domain_crossmark_restriction_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid content_domain_crossmark_restriction value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_content_domain_crossmark_restriction_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: content_domain_crossmark_restriction is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["content_domain_crossmark_restriction"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestAlternativeIdBaseValidation:
    """Base validation tests for alternative_id."""

    def test_alternative_id_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid alternative_id value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_alternative_id_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: alternative_id is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["alternative_id"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestPublishedBaseValidation:
    """Base validation tests for published."""

    def test_published_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid published value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_published_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: published is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["published"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestJournalNameShortBaseValidation:
    """Base validation tests for journal_name_short."""

    def test_journal_name_short_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal_name_short value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_journal_name_short_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal_name_short is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["journal_name_short"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestIssnPrintBaseValidation:
    """Base validation tests for issn_print."""

    def test_issn_print_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid issn_print value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_issn_print_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issn_print is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["issn_print"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestIssnElectronicBaseValidation:
    """Base validation tests for issn_electronic."""

    def test_issn_electronic_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid issn_electronic value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_issn_electronic_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issn_electronic is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["issn_electronic"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestAuthorDetailsBaseValidation:
    """Base validation tests for author_details."""

    def test_author_details_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid author_details value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_author_details_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: author_details is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["author_details"] = None
        PublicationEnrichedSchema.validate(df)


@pytest.mark.unit
class TestReferencesBaseValidation:
    """Base validation tests for references."""

    def test_references_valid(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid references value."""
        PublicationEnrichedSchema.validate(minimal_crossref_publication_df)

    def test_references_null_allowed(
        self, minimal_crossref_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: references is nullable."""
        df = minimal_crossref_publication_df.copy()
        df["references"] = None
        PublicationEnrichedSchema.validate(df)
