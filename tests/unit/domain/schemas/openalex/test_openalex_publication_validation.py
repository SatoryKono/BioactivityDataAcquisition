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
"""Base validation tests for Openalex Publication schema.

Tests regex patterns, nullable constraints, and type validation
for all 39 fields in OpenAlexPublicationSchema.

Generated from publication_validation_schema_v3.xlsx.
"""

import pytest
import pandas as pd
import pandera as pa
from typing import Any

from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from tests.unit.domain.schemas._schema_validation_assertions import (
    assert_schema_validates_frame,
)


@pytest.mark.unit
class TestPmidBaseValidation:
    """Base validation tests for pmid."""

    def test_pmid_base_validation__pmid_valid__7734822a(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid pmid value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_pmid_base_validation__pmid_null_allowed__34f0c769(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmid is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["pmid"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)

    @pytest.mark.parametrize("invalid_value", ["-1", "abc", ""])
    def test_pmid_base_validation__pmid_invalid_format__147db229(
        self, minimal_openalex_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmid invalid format."""
        df = minimal_openalex_publication_df.copy()
        df["pmid"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            OpenAlexPublicationSchema.validate(df)


@pytest.mark.unit
class TestDoiBaseValidation:
    """Base validation tests for doi."""

    def test_doi_base_validation__doi_valid__570b4641(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid doi value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_doi_base_validation__doi_null_allowed__1c563d77(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: doi is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["doi"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)

    @pytest.mark.parametrize(
        "invalid_value", ["doi:10.1234", "10.123/x", "not-a-doi", ""]
    )
    def test_doi_base_validation__doi_invalid_format__5b2b9a34(
        self, minimal_openalex_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: doi invalid format."""
        df = minimal_openalex_publication_df.copy()
        df["doi"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            OpenAlexPublicationSchema.validate(df)


@pytest.mark.unit
class TestPmcIdBaseValidation:
    """Base validation tests for pmc_id."""

    def test_case__cfcf9e0e12(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid pmc_id value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_pmc_id_base_validation__pmc_id_null_allowed__e69600a9(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmc_id is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["pmc_id"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)

    @pytest.mark.parametrize("invalid_value", ["pmc123", "PMC", "123", ""])
    def test_pmc_id_base_validation__id_invalid_format__d060aeb5(
        self, minimal_openalex_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmc_id invalid format."""
        df = minimal_openalex_publication_df.copy()
        df["pmc_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            OpenAlexPublicationSchema.validate(df)


@pytest.mark.unit
class TestTitleBaseValidation:
    """Base validation tests for title."""

    def test_title_base_validation__title_valid__f0480b60(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid title value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_title_base_validation__title_null_allowed__a020dcb9(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: title is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["title"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestAbstractBaseValidation:
    """Base validation tests for abstract."""

    def test_base_validation__abstract_valid__1786737a(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid abstract value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_base_validation__null_allowed__83f71059(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: abstract is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["abstract"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestAuthorsBaseValidation:
    """Base validation tests for authors."""

    def test_base_validation__authors_valid__1b7708fb(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid authors value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_base_validation__authors_null_allowed__17e42ec1(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: authors is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["authors"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestAffiliationListBaseValidation:
    """Base validation tests for affiliation_list."""

    def test_list_base_validation__list_valid__9c4b3854(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid affiliation_list value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_list_base_validation__list_null_allowed__2f66c351(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: affiliation_list is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["affiliation_list"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestJournalBaseValidation:
    """Base validation tests for journal."""

    def test_base_validation__journal_valid__e11857a4(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_base_validation__journal_null_allowed__30841956(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["journal"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestPublicationYearBaseValidation:
    """Base validation tests for publication_year."""

    def test_year_base_validation__year_valid__02ecc258(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_year value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_year_base_validation__year_null_allowed__00ab813b(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_year is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["publication_year"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestPublicationDateBaseValidation:
    """Base validation tests for publication_date."""

    def test_date_base_validation__date_valid__b60de007(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_date value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_date_base_validation__date_null_allowed__a3b45b35(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_date is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["publication_date"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestPublicationTypeBaseValidation:
    """Base validation tests for publication_type."""

    def test_type_base_validation__type_valid__cc7a7392(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_type value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_type_base_validation__type_null_allowed__b5c1169e(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_type is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["publication_type"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestLanguageBaseValidation:
    """Base validation tests for language."""

    def test_base_validation__language_valid__930b0ca0(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid language value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_base_validation__null_allowed__d48d098f(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: language is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["language"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestPageFirstBaseValidation:
    """Base validation tests for page_first."""

    def test_first_base_validation__page_first_valid__0fc772d6(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_first value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_first_base_validation__first_null_allowed__801b7eb4(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_first is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["page_first"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestPageLastBaseValidation:
    """Base validation tests for page_last."""

    def test_last_base_validation__page_last_valid__1478a440(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_last value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_last_base_validation__last_null_allowed__d68f2bd9(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_last is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["page_last"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestCitationsReceivedBaseValidation:
    """Base validation tests for citations_received."""

    def test_base_validation__received_valid__ec78fa2f(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_received value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_base_validation__null_allowed__c9b96145(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_received is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["citations_received"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestCitationsMadeBaseValidation:
    """Base validation tests for citations_made."""

    def test_made_base_validation__citations_made_valid__e0ed6e09(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_made value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_made_base_validation__made_null_allowed__5a5f2487(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_made is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["citations_made"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestIsOaBaseValidation:
    """Base validation tests for is_oa."""

    def test_is_oa_base_validation__is_oa_valid__9c9c5632(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid is_oa value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_is_oa_base_validation__is_oa_null_allowed__b03e1c4d(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: is_oa is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["is_oa"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestLookupMethodBaseValidation:
    """Base validation tests for lookup_method."""

    def test_method_base_validation__lookup_method_valid__dc1f61f0(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid lookup_method value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_method_base_validation__method_null_allowed__ae4a964f(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: lookup_method is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["lookup_method"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestOriginalIdBaseValidation:
    """Base validation tests for original_id."""

    def test_id_base_validation__original_id_valid__68e85e11(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid original_id value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_id_base_validation__id_null_allowed__b2e9e81e(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: original_id is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["original_id"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestSourceBaseValidation:
    """Base validation tests for _source."""

    def test_case__bf98a63411(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid _source value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_source_base_validation__source_null_allowed__33eee906(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: _source is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["_source"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestOpenalexIdBaseValidation:
    """Base validation tests for openalex_id."""

    def test_openalex_id_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid openalex_id value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_openalex_id_null_fails(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: openalex_id is non-nullable(PK)."""
        df = minimal_openalex_publication_df.copy()
        df["openalex_id"] = None
        with pytest.raises(pa.errors.SchemaError, match="openalex_id"):
            OpenAlexPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["w123", "W", "2148", ""])
    def test_openalex_id_invalid_format(
        self, minimal_openalex_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: openalex_id invalid format."""
        df = minimal_openalex_publication_df.copy()
        df["openalex_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            OpenAlexPublicationSchema.validate(df)


@pytest.mark.unit
class TestIssnBaseValidation:
    """Base validation tests for issn."""

    def test_issn_base_validation__issn_valid__5625a23b(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid issn value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_issn_base_validation__issn_null_allowed__4c88c228(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issn is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["issn"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)

    def test_issn_base_validation__accepts_any_string__b5453d66(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: issn has no format validation in OpenAlex schema."""
        df = minimal_openalex_publication_df.copy()
        df["issn"] = "1234-5678"
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestPublisherBaseValidation:
    """Base validation tests for publisher."""

    def test_base_validation__publisher_valid__c6367a8e(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publisher value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_base_validation__null_allowed__0914d52c(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publisher is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["publisher"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestOaStatusBaseValidation:
    """Base validation tests for oa_status."""

    def test_oa_status_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid oa_status value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_oa_status_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: oa_status is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["oa_status"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestVolumeBaseValidation:
    """Base validation tests for volume."""

    def test_case__675547e9dc(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid volume value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_volume_base_validation__volume_null_allowed__2b6917a6(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: volume is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["volume"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestIssueBaseValidation:
    """Base validation tests for issue."""

    def test_issue_base_validation__issue_valid__2621e055(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid issue value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_issue_base_validation__issue_null_allowed__08cd8c32(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: issue is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["issue"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestFwciBaseValidation:
    """Base validation tests for fwci."""

    def test_fwci_valid(self, minimal_openalex_publication_df: pd.DataFrame) -> None:
        """PASS: valid fwci value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_fwci_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: fwci is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["fwci"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestIsRetractedBaseValidation:
    """Base validation tests for is_retracted."""

    def test_is_retracted_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid is_retracted value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_is_retracted_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: is_retracted is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["is_retracted"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestSubjectTopicsBaseValidation:
    """Base validation tests for subject_topics."""

    def test_subject_topics_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_topics value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_subject_topics_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_topics is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["subject_topics"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestPrimaryTopicBaseValidation:
    """Base validation tests for primary_topic."""

    def test_primary_topic_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid primary_topic value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_primary_topic_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: primary_topic is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["primary_topic"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestGrantsBaseValidation:
    """Base validation tests for grants."""

    def test_grants_valid(self, minimal_openalex_publication_df: pd.DataFrame) -> None:
        """PASS: valid grants value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_grants_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: grants is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["grants"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestSubjectMeshBaseValidation:
    """Base validation tests for subject_mesh."""

    def test_subject_mesh_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_mesh value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_subject_mesh_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_mesh is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["subject_mesh"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestSubjectKeywordsBaseValidation:
    """Base validation tests for subject_keywords."""

    def test_base_validation__keywords_valid__66d3828c(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_keywords value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_base_validation__null_allowed__8d218e85(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_keywords is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["subject_keywords"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestMagIdBaseValidation:
    """Base validation tests for mag_id."""

    def test_mag_id_valid(self, minimal_openalex_publication_df: pd.DataFrame) -> None:
        """PASS: valid mag_id value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_mag_id_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: mag_id is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["mag_id"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestAuthorOpenalexIdsBaseValidation:
    """Base validation tests for author_openalex_ids."""

    def test_author_openalex_ids_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid author_openalex_ids value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_author_openalex_ids_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: author_openalex_ids is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["author_openalex_ids"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestInstitutionIdsBaseValidation:
    """Base validation tests for institution_ids."""

    def test_institution_ids_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid institution_ids value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_institution_ids_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: institution_ids is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["institution_ids"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestInstitutionCountryCodesBaseValidation:
    """Base validation tests for institution_country_codes."""

    def test_institution_country_codes_valid(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid institution_country_codes value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_institution_country_codes_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: institution_country_codes is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["institution_country_codes"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)


@pytest.mark.unit
class TestRorIdsBaseValidation:
    """Base validation tests for ror_ids."""

    def test_ror_ids_valid(self, minimal_openalex_publication_df: pd.DataFrame) -> None:
        """PASS: valid ror_ids value."""
        assert_schema_validates_frame(
            OpenAlexPublicationSchema, minimal_openalex_publication_df
        )

    def test_ror_ids_null_allowed(
        self, minimal_openalex_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: ror_ids is nullable."""
        df = minimal_openalex_publication_df.copy()
        df["ror_ids"] = None
        assert_schema_validates_frame(OpenAlexPublicationSchema, df)
