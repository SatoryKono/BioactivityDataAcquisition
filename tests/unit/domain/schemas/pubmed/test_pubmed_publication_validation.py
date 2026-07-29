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
from tests.unit.domain.schemas._schema_validation_assertions import (
    assert_schema_validates_frame,
)


@pytest.mark.unit
class TestPmidBaseValidation:
    """Base validation tests for pmid."""

    def test_pmid_base_validation__pmid_valid__ac5b8af9(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid pmid value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_pmid_null_fails(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """FAIL: pmid is non-nullable(PK)."""
        df = minimal_pubmed_publication_df.copy()
        df["pmid"] = None
        with pytest.raises(pa.errors.SchemaError, match="pmid"):
            PubMedPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["0", "-1", "abc", ""])
    def test_pmid_base_validation__pmid_invalid_format__c59cffd7(
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

    def test_doi_base_validation__doi_valid__1f769adf(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid doi value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_doi_base_validation__doi_null_allowed__30060bb5(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: doi is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["doi"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)

    @pytest.mark.parametrize(
        "invalid_value", ["doi:10.1234", "10.123/x", "not-a-doi", ""]
    )
    def test_doi_base_validation__doi_invalid_format__dca4d211(
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

    def test_pmc_id_base_validation__pmc_id_valid__cf387190(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid pmc_id value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_pmc_id_base_validation__pmc_id_null_allowed__aba8ecb8(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmc_id is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["pmc_id"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)

    @pytest.mark.parametrize("invalid_value", ["pmc123", "PMC", "123", ""])
    def test_pmc_id_base_validation__id_invalid_format__625d71b6(
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

    def test_title_base_validation__title_valid__55d31543(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid title value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_title_base_validation__title_null_fails__7f8e50c6(
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

    def test_base_validation__abstract_valid__1f46af1f(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid abstract value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_base_validation__null_allowed__27d2ba8a(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: abstract is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["abstract"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestAuthorsBaseValidation:
    """Base validation tests for authors."""

    def test_base_validation__authors_valid__e1fba3b0(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid authors value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_base_validation__authors_null_allowed__36c5b6e1(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: authors is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["authors"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestAffiliationListBaseValidation:
    """Base validation tests for affiliation_list."""

    def test_list_base_validation__list_valid__75a267e6(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid affiliation_list value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_list_base_validation__list_null_allowed__ea1161fb(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: affiliation_list is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["affiliation_list"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestJournalBaseValidation:
    """Base validation tests for journal."""

    def test_base_validation__journal_valid__bd36d3e4(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_base_validation__journal_null_allowed__8309eae6(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["journal"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPublicationYearBaseValidation:
    """Base validation tests for publication_year."""

    def test_year_base_validation__year_valid__b3fc60b5(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_year value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_year_base_validation__year_null_allowed__d6491317(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_year is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_year"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPublicationDateBaseValidation:
    """Base validation tests for publication_date."""

    def test_date_base_validation__date_valid__c53410f2(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_date value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_date_base_validation__date_null_allowed__cd8c9572(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_date is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_date"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPublicationTypeBaseValidation:
    """Base validation tests for publication_type."""

    def test_type_base_validation__type_valid__56479027(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_type value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_type_base_validation__type_null_allowed__e5fd4415(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_type is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_type"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestLanguageBaseValidation:
    """Base validation tests for language."""

    def test_base_validation__language_valid__69bf5c2c(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid language value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_base_validation__null_allowed__ef9bc013(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: language is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["language"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPageFirstBaseValidation:
    """Base validation tests for page_first."""

    def test_first_base_validation__page_first_valid__5a6bc5f9(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_first value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_first_base_validation__first_null_allowed__c5182f9d(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_first is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["page_first"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPageLastBaseValidation:
    """Base validation tests for page_last."""

    def test_last_base_validation__page_last_valid__025923ad(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_last value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_last_base_validation__last_null_allowed__3985bf16(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_last is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["page_last"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestCitationsReceivedBaseValidation:
    """Base validation tests for citations_received."""

    def test_base_validation__received_valid__e0bedf67(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_received value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_base_validation__null_allowed__ae01aa38(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_received is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["citations_received"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestCitationsMadeBaseValidation:
    """Base validation tests for citations_made."""

    def test_made_base_validation__citations_made_valid__e5a96731(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_made value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_made_base_validation__made_null_allowed__417f0f4b(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_made is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["citations_made"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestIsOaBaseValidation:
    """Base validation tests for is_oa."""

    def test_is_oa_base_validation__is_oa_valid__07eafbc3(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid is_oa value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_is_oa_base_validation__is_oa_null_allowed__9322d77e(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: is_oa is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["is_oa"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestLookupMethodBaseValidation:
    """Base validation tests for lookup_method."""

    def test_method_base_validation__lookup_method_valid__87f15361(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid lookup_method value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_method_base_validation__method_null_allowed__063eb503(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: lookup_method is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["lookup_method"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestOriginalIdBaseValidation:
    """Base validation tests for original_id."""

    def test_id_base_validation__original_id_valid__1c0a817a(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid original_id value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_id_base_validation__id_null_allowed__f6f6c5a8(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: original_id is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["original_id"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestSourceBaseValidation:
    """Base validation tests for _source."""

    def test_source_base_validation__source_valid__2912b1b8(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid _source value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_source_base_validation__source_null_allowed__c856f10e(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: _source is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["_source"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPiiBaseValidation:
    """Base validation tests for pii."""

    def test_pii_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid pii value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_pii_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pii is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["pii"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestMidBaseValidation:
    """Base validation tests for mid."""

    def test_mid_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid mid value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_mid_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: mid is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["mid"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPublisherIdBaseValidation:
    """Base validation tests for publisher_id."""

    def test_publisher_id_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publisher_id value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_publisher_id_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publisher_id is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publisher_id"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestAbstractStructuredBaseValidation:
    """Base validation tests for abstract_structured."""

    def test_abstract_structured_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid abstract_structured value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_abstract_structured_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: abstract_structured is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["abstract_structured"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestJournalNameShortBaseValidation:
    """Base validation tests for journal_name_short."""

    def test_short_base_validation__name_short_valid__f50e3a58(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal_name_short value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_short_base_validation__short_null_allowed__d2f8ee24(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal_name_short is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["journal_name_short"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestJournalIsoAbbrevBaseValidation:
    """Base validation tests for journal_iso_abbrev."""

    def test_journal_iso_abbrev_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal_iso_abbrev value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_journal_iso_abbrev_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal_iso_abbrev is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["journal_iso_abbrev"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestIssnBaseValidation:
    """Base validation tests for issn."""

    def test_issn_base_validation__issn_valid__b32b5930(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid issn value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_issn_base_validation__issn_null_allowed__e1a4a438(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issn is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["issn"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)

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
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_journal_issn_type_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal_issn_type is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["journal_issn_type"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestNlmUniqueIdBaseValidation:
    """Base validation tests for nlm_unique_id."""

    def test_nlm_unique_id_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid nlm_unique_id value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_nlm_unique_id_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: nlm_unique_id is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["nlm_unique_id"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestCountryBaseValidation:
    """Base validation tests for country."""

    def test_country_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid country value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_country_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: country is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["country"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestMedlinePgnBaseValidation:
    """Base validation tests for medline_pgn."""

    def test_medline_pgn_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid medline_pgn value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_medline_pgn_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: medline_pgn is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["medline_pgn"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPageRangeBaseValidation:
    """Base validation tests for page_range."""

    def test_page_range_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_range value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_page_range_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_range is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["page_range"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPubMonthBaseValidation:
    """Base validation tests for pub_month."""

    def test_pub_month_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid pub_month value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_pub_month_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pub_month is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["pub_month"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPubDayBaseValidation:
    """Base validation tests for pub_day."""

    def test_pub_day_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid pub_day value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_pub_day_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pub_day is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["pub_day"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPublicationStatusBaseValidation:
    """Base validation tests for publication_status."""

    def test_publication_status_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_status value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_publication_status_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_status is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_status"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestDateCompletedBaseValidation:
    """Base validation tests for date_completed."""

    def test_date_completed_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid date_completed value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_date_completed_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: date_completed is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["date_completed"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestDateRevisedBaseValidation:
    """Base validation tests for date_revised."""

    def test_date_revised_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid date_revised value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_date_revised_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: date_revised is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["date_revised"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestCitationSubsetBaseValidation:
    """Base validation tests for citation_subset."""

    def test_citation_subset_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citation_subset value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_citation_subset_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citation_subset is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["citation_subset"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestAffiliationStructuredBaseValidation:
    """Base validation tests for affiliation_structured."""

    def test_affiliation_structured_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid affiliation_structured value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_affiliation_structured_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: affiliation_structured is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["affiliation_structured"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestAuthorCountBaseValidation:
    """Base validation tests for author_count."""

    def test_author_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid author_count value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_author_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: author_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["author_count"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestMeshHeadingCountBaseValidation:
    """Base validation tests for mesh_heading_count."""

    def test_mesh_heading_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid mesh_heading_count value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_mesh_heading_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: mesh_heading_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["mesh_heading_count"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestKeywordCountBaseValidation:
    """Base validation tests for keyword_count."""

    def test_keyword_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid keyword_count value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_keyword_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: keyword_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["keyword_count"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestGrantCountBaseValidation:
    """Base validation tests for grant_count."""

    def test_grant_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid grant_count value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_grant_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: grant_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["grant_count"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestChemicalCountBaseValidation:
    """Base validation tests for chemical_count."""

    def test_chemical_count_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid chemical_count value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_chemical_count_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: chemical_count is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["chemical_count"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestSubjectMeshBaseValidation:
    """Base validation tests for subject_mesh."""

    def test_mesh_base_validation__subject_mesh_valid__0df3b6c1(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_mesh value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_mesh_base_validation__mesh_null_allowed__7bb5fa77(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_mesh is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["subject_mesh"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestChemicalsBaseValidation:
    """Base validation tests for chemicals."""

    def test_chemicals_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid chemicals value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_chemicals_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: chemicals is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["chemicals"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestSubjectKeywordsBaseValidation:
    """Base validation tests for subject_keywords."""

    def test_base_validation__keywords_valid__b02b7a75(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_keywords value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_base_validation__null_allowed__2890d6af(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_keywords is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["subject_keywords"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestDatabanksBaseValidation:
    """Base validation tests for databanks."""

    def test_databanks_valid(self, minimal_pubmed_publication_df: pd.DataFrame) -> None:
        """PASS: valid databanks value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_databanks_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: databanks is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["databanks"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestGeneSymbolsBaseValidation:
    """Base validation tests for gene_symbols."""

    def test_gene_symbols_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid gene_symbols value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_gene_symbols_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: gene_symbols is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["gene_symbols"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestPublicationTypesBaseValidation:
    """Base validation tests for publication_types."""

    def test_publication_types_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_types value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_publication_types_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_types is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["publication_types"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)


@pytest.mark.unit
class TestAuthorsWithAffiliationsBaseValidation:
    """Base validation tests for authors_with_affiliations."""

    def test_authors_with_affiliations_valid(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid authors_with_affiliations value."""
        assert_schema_validates_frame(
            PubMedPublicationSchema, minimal_pubmed_publication_df
        )

    def test_authors_with_affiliations_null_allowed(
        self, minimal_pubmed_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: authors_with_affiliations is nullable."""
        df = minimal_pubmed_publication_df.copy()
        df["authors_with_affiliations"] = None
        assert_schema_validates_frame(PubMedPublicationSchema, df)
