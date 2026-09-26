# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for Semantic Scholar Publication Schema field validations.

Exercises SemanticScholarPublicationSchema via Pandera validate() on
minimal fixtures. Field-table density is intentional (#6646); empty
pass-bodies and self-fulfilled regex-only checks are forbidden.
"""

from __future__ import annotations

import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.common.publication_base import LOOKUP_METHODS
from bioetl.domain.schemas.semanticscholar.publication import (
    OA_STATUS_VALUES,
    SemanticScholarPublicationSchema,
)
from bioetl.domain.validation import MAX_PUBLICATION_YEAR, MIN_PUBLICATION_YEAR
from tests.unit.domain.schemas._schema_validation_assertions import (
    assert_schema_validates_frame,
)

pytestmark = pytest.mark.unit


class TestPaperIdValidation:
    def test_valid_paper_id_format(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["paper_id"] = "649def34f8be52c8b66281af98ae884c09aef38b"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_paper_id_too_short(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["paper_id"] = "abc123"
        with pytest.raises(pa.errors.SchemaError, match="paper_id"):
            SemanticScholarPublicationSchema.validate(df)

    def test_invalid_paper_id_not_hex(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["paper_id"] = "invalid-not-hex-characters-need-40-total"
        with pytest.raises(pa.errors.SchemaError, match="paper_id"):
            SemanticScholarPublicationSchema.validate(df)


class TestDoiValidation:
    def test_valid_doi_format(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["doi"] = "10.1038/s41586-024-07487-w"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_doi_format(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["doi"] = "not-a-valid-doi"
        with pytest.raises(pa.errors.SchemaError, match="doi"):
            SemanticScholarPublicationSchema.validate(df)


class TestPmidValidation:
    def test_valid_pmid_numeric(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["pmid"] = "12345678"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_pmid_non_numeric(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["pmid"] = "abc-not-numeric"
        with pytest.raises(pa.errors.SchemaError, match="pmid"):
            SemanticScholarPublicationSchema.validate(df)


class TestPmcIdValidation:
    def test_pmc_id_validation__valid_pmc_id_format__e264e3a6(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["pmc_id"] = "PMC1234567"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_pmc_id_no_prefix(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["pmc_id"] = "1234567"
        with pytest.raises(pa.errors.SchemaError, match="pmc_id"):
            SemanticScholarPublicationSchema.validate(df)


class TestYearValidation:
    def test_valid_year_in_range(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_year"] = 2024
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_year_at_lower_bound(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_year"] = MIN_PUBLICATION_YEAR
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_year_below_lower_bound(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_year"] = MIN_PUBLICATION_YEAR - 1
        with pytest.raises(pa.errors.SchemaError, match="publication_year"):
            SemanticScholarPublicationSchema.validate(df)

    def test_year_above_upper_bound(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_year"] = MAX_PUBLICATION_YEAR + 1
        with pytest.raises(pa.errors.SchemaError, match="publication_year"):
            SemanticScholarPublicationSchema.validate(df)


class TestPublicationDateValidation:
    def test_valid_date_format(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_date"] = "2024-05-15"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_date_format_slash(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["publication_date"] = "15/05/2024"
        with pytest.raises(pa.errors.SchemaError, match="publication_date"):
            SemanticScholarPublicationSchema.validate(df)


class TestMetricsValidation:
    def test_valid_citation_count(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_received"] = 42
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_negative_citation_count(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_received"] = -1
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(df)

    def test_valid_reference_count(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_made"] = 85
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_negative_reference_count(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["citations_made"] = -1
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(df)


class TestCorpusIdValidation:
    def test_valid_corpus_id(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["corpus_id"] = 123456
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_negative_corpus_id(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["corpus_id"] = -1
        with pytest.raises(pa.errors.SchemaError, match="corpus_id"):
            SemanticScholarPublicationSchema.validate(df)


class TestOaStatusValidation:
    @pytest.mark.parametrize("status", OA_STATUS_VALUES)
    def test_valid_oa_status(
        self,
        status: str,
        minimal_semanticscholar_publication_df: pd.DataFrame,
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["oa_status"] = status
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_oa_status(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["oa_status"] = "INVALID"
        with pytest.raises(pa.errors.SchemaError, match="oa_status"):
            SemanticScholarPublicationSchema.validate(df)

    def test_oa_status_values_are_lowercase(self) -> None:
        for status in OA_STATUS_VALUES:
            assert status == status.lower()
        assert "closed" in OA_STATUS_VALUES


class TestLookupMethodValidation:
    @pytest.mark.parametrize("method", LOOKUP_METHODS)
    def test_valid_lookup_method(
        self,
        method: str,
        minimal_semanticscholar_publication_df: pd.DataFrame,
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["_lookup_method"] = method
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_lookup_method(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["_lookup_method"] = "invalid_method"
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(df)


class TestSourceValidation:
    def test_valid_source(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        assert df["_source"].iloc[0] == "semanticscholar"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_source_field_contract(self) -> None:
        field_info = SemanticScholarPublicationSchema.__dict__["_source"]
        assert field_info.nullable is False
        assert any(
            "equal_to" in getattr(check, "name", str(check))
            for check in field_info.checks
        )
        assert any("semanticscholar" in str(check) for check in field_info.checks)
        assert any("semanticscholar" in str(check) for check in field_info.checks)


class TestSchemaFieldDefinitions:
    def test_schema_has_semanticscholar_fields(self) -> None:
        schema = SemanticScholarPublicationSchema.to_schema()
        required_fields = [
            "paper_id",
            "doi",
            "pmid",
            "dblp_id",
            "corpus_id",
            "title",
            "abstract",
            "tldr",
            "publication_year",
            "publication_date",
            "journal",
            "volume",
            "page_range",
            "citations_received",
            "citations_made",
            "influential_citation_count",
            "is_oa",
            "open_access_url",
            "oa_status",
            "subject_fields",
            "publication_type",
            "publication_types",
            "authors",
        ]
        for field in required_fields:
            assert field in schema.columns, f"Missing field: {field}"

    def test_paper_id_not_nullable(self) -> None:
        schema = SemanticScholarPublicationSchema.to_schema()
        paper_id_col = schema.columns.get("paper_id")
        assert paper_id_col is not None
        assert paper_id_col.nullable is False

    def test_source_field_validated(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        field_info = SemanticScholarPublicationSchema.__dict__["_source"]
        assert field_info.nullable is False
        assert any("semanticscholar" in str(check) for check in field_info.checks)
        ok = minimal_semanticscholar_publication_df.copy()
        assert ok["_source"].iloc[0] == "semanticscholar"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, ok)

    def test_optional_fields_nullable(self) -> None:
        schema = SemanticScholarPublicationSchema.to_schema()
        nullable_fields = [
            "doi",
            "pmid",
            "dblp_id",
            "title",
            "abstract",
            "tldr",
            "publication_date",
            "journal",
            "volume",
            "page_range",
            "open_access_url",
            "oa_status",
            "subject_fields",
            "publication_type",
            "publication_types",
            "authors",
        ]
        for field in nullable_fields:
            col = schema.columns.get(field)
            assert col is not None, f"Missing field: {field}"
            assert col.nullable is True, f"Field {field} should be nullable"


class TestContentHashValidation:
    def test_valid_content_hash_format(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["content_hash"] = "a" * 64
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_invalid_content_hash_short(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        df = minimal_semanticscholar_publication_df.copy()
        df["content_hash"] = "short"
        with pytest.raises(pa.errors.SchemaError, match="content_hash"):
            SemanticScholarPublicationSchema.validate(df)


class TestDataFrameWithPandas:
    def test_paper_id_pattern_with_dataframe(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        good = minimal_semanticscholar_publication_df.copy()
        good["paper_id"] = "649def34f8be52c8b66281af98ae884c09aef38b"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, good)
        bad = minimal_semanticscholar_publication_df.copy()
        bad["paper_id"] = "invalid"
        with pytest.raises(pa.errors.SchemaError, match="paper_id"):
            SemanticScholarPublicationSchema.validate(bad)

    def test_doi_pattern_with_dataframe(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        good = minimal_semanticscholar_publication_df.copy()
        good["doi"] = "10.1038/s41586-024-07487-w"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, good)
        bad = minimal_semanticscholar_publication_df.copy()
        bad["doi"] = "invalid-doi"
        with pytest.raises(pa.errors.SchemaError, match="doi"):
            SemanticScholarPublicationSchema.validate(bad)

    def test_publication_date_pattern_with_dataframe(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        good = minimal_semanticscholar_publication_df.copy()
        good["publication_date"] = "2024-05-15"
        assert_schema_validates_frame(SemanticScholarPublicationSchema, good)
        bad = minimal_semanticscholar_publication_df.copy()
        bad["publication_date"] = "15/05/2024"
        with pytest.raises(pa.errors.SchemaError, match="publication_date"):
            SemanticScholarPublicationSchema.validate(bad)


class TestNewFieldValidations:
    def test_dblp_id_nullable(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        schema = SemanticScholarPublicationSchema.to_schema()
        dblp_col = schema.columns.get("dblp_id")
        assert dblp_col is not None
        assert dblp_col.nullable is True
        df = minimal_semanticscholar_publication_df.copy()
        df["dblp_id"] = None
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_influential_citation_count_nullable(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        schema = SemanticScholarPublicationSchema.to_schema()
        col = schema.columns.get("influential_citation_count")
        assert col is not None
        assert col.nullable is True
        df = minimal_semanticscholar_publication_df.copy()
        df["influential_citation_count"] = None
        assert_schema_validates_frame(SemanticScholarPublicationSchema, df)

    def test_influential_citation_count_must_be_non_negative(
        self, minimal_semanticscholar_publication_df: pd.DataFrame
    ) -> None:
        good = minimal_semanticscholar_publication_df.copy()
        good["influential_citation_count"] = 0
        assert_schema_validates_frame(SemanticScholarPublicationSchema, good)
        bad = minimal_semanticscholar_publication_df.copy()
        bad["influential_citation_count"] = -1
        with pytest.raises(pa.errors.SchemaError):
            SemanticScholarPublicationSchema.validate(bad)
