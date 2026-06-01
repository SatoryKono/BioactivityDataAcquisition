"""Base validation tests for Semanticscholar Publication schema.

Tests regex patterns, nullable constraints, and type validation
for all 35 fields in SemanticScholarPublicationSchema.

Generated from publication_validation_schema_v3.xlsx.
"""

import pytest
import pandas as pd
import pandera as pa
from typing import Any

from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)


@pytest.mark.unit
class TestPmidBaseValidation:
    """Base validation tests for pmid."""

    def test_pmid_base_validation__pmid_valid__700a320d(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid pmid value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_pmid_base_validation__pmid_null_allowed__08ce86f4(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmid is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["pmid"] = None
        SemanticScholarPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["-1", "abc", ""])
    def test_pmid_base_validation__pmid_invalid_format__17bfbf82(
        self, minimal_semanticscholar_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmid invalid format."""
        df = minimal_semanticscholar_publication_df.copy()
        df["pmid"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestDoiBaseValidation:
    """Base validation tests for doi."""

    def test_doi_base_validation__doi_valid__a30e1c20(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid doi value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_doi_base_validation__doi_null_allowed__5ba82159(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: doi is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["doi"] = None
        SemanticScholarPublicationSchema.validate(df)

    @pytest.mark.parametrize(
        "invalid_value", ["doi:10.1234", "10.123/x", "not-a-doi", ""]
    )
    def test_doi_base_validation__doi_invalid_format__1bdd4ed8(
        self, minimal_semanticscholar_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: doi invalid format."""
        df = minimal_semanticscholar_publication_df.copy()
        df["doi"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPmcIdBaseValidation:
    """Base validation tests for pmc_id."""

    def test_pmc_id_base_validation__pmc_id_valid__5ec7411f(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid pmc_id value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_pmc_id_base_validation__pmc_id_null_allowed__bdd6f1f5(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: pmc_id is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["pmc_id"] = None
        SemanticScholarPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", ["pmc123", "PMC", "123", ""])
    def test_pmc_id_base_validation__id_invalid_format__cb3cec42(
        self, minimal_semanticscholar_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: pmc_id invalid format."""
        df = minimal_semanticscholar_publication_df.copy()
        df["pmc_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestTitleBaseValidation:
    """Base validation tests for title."""

    def test_title_base_validation__title_valid__3c825b22(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid title value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_title_base_validation__title_null_allowed__4596e9c7(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: title is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["title"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestAbstractBaseValidation:
    """Base validation tests for abstract."""

    def test_base_validation__abstract_valid__3026d8ba(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid abstract value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_base_validation__null_allowed__c89132cb(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: abstract is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["abstract"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestAuthorsBaseValidation:
    """Base validation tests for authors."""

    def test_base_validation__authors_valid__09fecf19(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid authors value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_base_validation__authors_null_allowed__44cb58cc(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: authors is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["authors"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestAffiliationListBaseValidation:
    """Base validation tests for affiliation_list."""

    def test_list_base_validation__list_valid__9b735559(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid affiliation_list value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_list_base_validation__list_null_allowed__f7caea03(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: affiliation_list is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["affiliation_list"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestJournalBaseValidation:
    """Base validation tests for journal."""

    def test_base_validation__journal_valid__fdbe05e5(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid journal value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_base_validation__journal_null_allowed__61ac788f(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: journal is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["journal"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationYearBaseValidation:
    """Base validation tests for publication_year."""

    def test_year_base_validation__year_valid__bc6c9057(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_year value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_year_base_validation__year_null_allowed__27880e52(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_year is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_year"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationDateBaseValidation:
    """Base validation tests for publication_date."""

    def test_date_base_validation__date_valid__699c8fb3(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_date value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_date_base_validation__date_null_allowed__f5a159cb(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_date is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_date"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationTypeBaseValidation:
    """Base validation tests for publication_type."""

    def test_type_base_validation__type_valid__7ad2104f(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_type value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_type_base_validation__type_null_allowed__c9b934c4(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_type is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_type"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestLanguageBaseValidation:
    """Base validation tests for language."""

    def test_base_validation__language_valid__716ea602(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid language value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_base_validation__null_allowed__ba822ca3(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: language is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["language"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPageFirstBaseValidation:
    """Base validation tests for page_first."""

    def test_first_base_validation__page_first_valid__b2e94953(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_first value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_first_base_validation__first_null_allowed__4170b325(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_first is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["page_first"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPageLastBaseValidation:
    """Base validation tests for page_last."""

    def test_last_base_validation__page_last_valid__2cfd55e6(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_last value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_last_base_validation__last_null_allowed__e8dff6ab(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_last is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["page_last"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestCitationsReceivedBaseValidation:
    """Base validation tests for citations_received."""

    def test_base_validation__received_valid__9ba6c26f(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_received value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_base_validation__null_allowed__21d6a4e2(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_received is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_received"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestCitationsMadeBaseValidation:
    """Base validation tests for citations_made."""

    def test_made_base_validation__citations_made_valid__69b70d4d(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citations_made value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_made_base_validation__made_null_allowed__02d97dde(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citations_made is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_made"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestIsOaBaseValidation:
    """Base validation tests for is_oa."""

    def test_is_oa_base_validation__is_oa_valid__07113608(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid is_oa value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_is_oa_base_validation__is_oa_null_allowed__f88d84f5(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: is_oa is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["is_oa"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestLookupMethodBaseValidation:
    """Base validation tests for lookup_method."""

    def test_method_base_validation__lookup_method_valid__5bace48e(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid lookup_method value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_method_base_validation__method_null_allowed__74840504(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: lookup_method is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["lookup_method"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestOriginalIdBaseValidation:
    """Base validation tests for original_id."""

    def test_id_base_validation__original_id_valid__e12512c2(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid original_id value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_id_base_validation__id_null_allowed__ed51fd14(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: original_id is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["original_id"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestSourceBaseValidation:
    """Base validation tests for _source."""

    def test_source_base_validation__source_valid__3d94bde7(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid _source value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_source_base_validation__source_null_allowed__910440cc(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: _source is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["_source"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPaperIdBaseValidation:
    """Base validation tests for paper_id."""

    def test_paper_id_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid paper_id value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_paper_id_null_fails(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """FAIL: paper_id is non-nullable(PK)."""
        df = minimal_semanticscholar_publication_df.copy()
        df["paper_id"] = None
        with pytest.raises(pa.errors.SchemaError, match="paper_id"):
            SemanticScholarPublicationSchema.validate(df)

    @pytest.mark.parametrize(
        "invalid_value", ["short", "A1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0", ""]
    )
    def test_paper_id_invalid_format(
        self, minimal_semanticscholar_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: paper_id invalid format."""
        df = minimal_semanticscholar_publication_df.copy()
        df["paper_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestDblpIdBaseValidation:
    """Base validation tests for dblp_id."""

    def test_dblp_id_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid dblp_id value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_dblp_id_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: dblp_id is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["dblp_id"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestCorpusIdBaseValidation:
    """Base validation tests for corpus_id."""

    def test_corpus_id_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid corpus_id value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_corpus_id_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: corpus_id is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["corpus_id"] = None
        SemanticScholarPublicationSchema.validate(df)

    @pytest.mark.parametrize("invalid_value", [-1])
    def test_corpus_id_invalid_format(
        self, minimal_semanticscholar_publication_df: pd.DataFrame, invalid_value: Any
    ) -> None:
        """FAIL: corpus_id invalid format."""
        df = minimal_semanticscholar_publication_df.copy()
        df["corpus_id"] = invalid_value
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestTldrBaseValidation:
    """Base validation tests for tldr."""

    def test_tldr_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid tldr value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_tldr_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: tldr is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["tldr"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestVolumeBaseValidation:
    """Base validation tests for volume."""

    def test_volume_base_validation__volume_valid__19b9064a(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid volume value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_volume_base_validation__volume_null_allowed__f06d7e56(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: volume is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["volume"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPageRangeBaseValidation:
    """Base validation tests for page_range."""

    def test_range_base_validation__page_range_valid__8633194b(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid page_range value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_range_base_validation__range_null_allowed__e4646ac3(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: page_range is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["page_range"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestInfluentialCitationCountBaseValidation:
    """Base validation tests for influential_citation_count."""

    def test_influential_citation_count_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid influential_citation_count value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_influential_citation_count_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: influential_citation_count is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["influential_citation_count"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestOpenAccessUrlBaseValidation:
    """Base validation tests for open_access_url."""

    def test_open_access_url_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid open_access_url value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_open_access_url_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: open_access_url is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["open_access_url"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestOaStatusBaseValidation:
    """Base validation tests for oa_status."""

    def test_status_base_validation__oa_status_valid__b321083d(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid oa_status value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_status_base_validation__status_null_allowed__d89abc4b(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: oa_status is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["oa_status"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestSubjectFieldsBaseValidation:
    """Base validation tests for subject_fields."""

    def test_subject_fields_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid subject_fields value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_subject_fields_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: subject_fields is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["subject_fields"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestPublicationTypesBaseValidation:
    """Base validation tests for publication_types."""

    def test_types_base_validation__types_valid__6ac3a0aa(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid publication_types value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_types_base_validation__types_null_allowed__8c792f04(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: publication_types is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_types"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestAuthorS2IdsBaseValidation:
    """Base validation tests for author_s2_ids."""

    def test_author_s2_ids_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid author_s2_ids value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_author_s2_ids_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: author_s2_ids is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["author_s2_ids"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestAuthorHIndicesBaseValidation:
    """Base validation tests for author_h_indices."""

    def test_author_h_indices_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid author_h_indices value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_author_h_indices_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: author_h_indices is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["author_h_indices"] = None
        SemanticScholarPublicationSchema.validate(df)


@pytest.mark.unit
class TestCitationContextsBaseValidation:
    """Base validation tests for citation_contexts."""

    def test_citation_contexts_valid(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """PASS: valid citation_contexts value."""
        SemanticScholarPublicationSchema.validate(
            minimal_semanticscholar_publication_df
        )

    def test_citation_contexts_null_allowed(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        """SKIP: citation_contexts is nullable."""
        df = minimal_semanticscholar_publication_df.copy()
        df["citation_contexts"] = None
        SemanticScholarPublicationSchema.validate(df)
