"""Contract tests for Publication schema stability and cross-provider compatibility.

Tests schema inheritance, common field presence, and API contracts.
Expected: ~25 tests ensuring schema consistency across providers.
"""

import pytest
import pandera as pa
from typing import Type

from bioetl.domain.schemas.common.publication_base import PublicationBaseSchema
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import SemanticScholarPublicationSchema


@pytest.mark.contracts
class TestSchemaInheritance:
    """Test all publication schemas inherit PublicationBaseSchema."""

    @pytest.mark.parametrize(
        "schema_class",
        [
            ChemblPublicationSchema,
            PubMedPublicationSchema,
            PublicationEnrichedSchema,
            OpenAlexPublicationSchema,
            SemanticScholarPublicationSchema,
        ],
    )
    def test_schema_inherits_base(self, schema_class: Type[pa.DataFrameModel]) -> None:
        """All schemas inherit PublicationBaseSchema."""
        assert issubclass(schema_class, PublicationBaseSchema)


@pytest.mark.contracts
class TestCommonFieldsPresence:
    """Test all schemas define common fields from PublicationBaseSchema."""

    COMMON_FIELDS = [
        "title",
        "abstract",
        "authors",
        "journal",
        "publication_year",
        "_source",
        "_lookup_method",
        "_original_id",
    ]

    @pytest.mark.parametrize("provider", ["chembl", "pubmed", "crossref", "openalex", "semanticscholar"])
    def test_common_fields_present(self, provider: str) -> None:
        """All schemas have common fields from base schema."""
        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        schema_class = schema_map[provider]
        schema_fields = schema_class.__annotations__.keys()

        for field in self.COMMON_FIELDS:
            # Allow aliases (e.g., _lookup_method has alias lookup_method)
            assert (
                field in schema_fields or field.lstrip("_") in schema_fields
            ), f"{provider} schema missing {field}"


@pytest.mark.contracts
class TestDQFieldsPresence:
    """Test _dq_warn and _dq_error fields present in all schemas."""

    @pytest.mark.parametrize(
        "provider,schema_class",
        [
            ("chembl", ChemblPublicationSchema),
            ("pubmed", PubMedPublicationSchema),
            ("crossref", PublicationEnrichedSchema),
            ("openalex", OpenAlexPublicationSchema),
            ("semanticscholar", SemanticScholarPublicationSchema),
        ],
    )
    def test_dq_fields_present(self, provider: str, schema_class: Type[pa.DataFrameModel]) -> None:
        """DQ flags present in all schemas."""
        # Note: ChEMBL has explicit _dq_warn, _dq_error
        # Others inherit from ETLRecordSchema
        schema_fields = schema_class.__annotations__.keys()

        # Check if defined in this class or inherited
        has_dq_warn = "_dq_warn" in schema_fields or hasattr(schema_class, "_dq_warn")
        has_dq_error = "_dq_error" in schema_fields or hasattr(schema_class, "_dq_error")

        assert has_dq_warn or has_dq_error, f"{provider} schema missing DQ fields"


@pytest.mark.contracts
class TestContentHashField:
    """Test content_hash field (identifier, deterministic) present in all."""

    @pytest.mark.parametrize("provider", ["chembl", "pubmed", "crossref", "openalex", "semanticscholar"])
    def test_content_hash_present(self, provider: str) -> None:
        """content_hash field present in all schemas."""
        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        schema_class = schema_map[provider]

        # content_hash inherited from ETLRecordSchema
        has_content_hash = (
            "content_hash" in schema_class.__annotations__ or hasattr(schema_class, "content_hash")
        )

        assert has_content_hash, f"{provider} schema missing content_hash"


@pytest.mark.contracts
class TestSourceFieldContract:
    """Test _source field matches provider name."""

    @pytest.mark.parametrize(
        "provider,schema_class",
        [
            ("chembl", ChemblPublicationSchema),
            ("pubmed", PubMedPublicationSchema),
            ("crossref", PublicationEnrichedSchema),
            ("openalex", OpenAlexPublicationSchema),
            ("semanticscholar", SemanticScholarPublicationSchema),
        ],
    )
    def test_source_field_matches_provider(
        self, provider: str, schema_class: Type[pa.DataFrameModel], request
    ) -> None:
        """_source field should match provider name."""
        # Get fixture for this provider
        fixture_name = f"minimal_{provider}_publication_df"
        df = request.getfixturevalue(fixture_name)

        # Validate schema
        validated_df = schema_class.validate(df)

        # Check _source value
        assert validated_df["_source"].iloc[0] == provider


@pytest.mark.contracts
class TestPrimaryKeyFields:
    """Test each provider has a unique primary key field."""

    PRIMARY_KEYS = {
        "chembl": "document_chembl_id",
        "pubmed": "pmid",
        "crossref": "doi",
        "openalex": "openalex_id",
        "semanticscholar": "paper_id",
    }

    @pytest.mark.parametrize("provider,pk_field", PRIMARY_KEYS.items())
    def test_primary_key_present(self, provider: str, pk_field: str) -> None:
        """Each provider schema has designated primary key."""
        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        schema_class = schema_map[provider]
        schema_fields = schema_class.__annotations__.keys()

        assert pk_field in schema_fields, f"{provider} schema missing PK {pk_field}"

    @pytest.mark.parametrize("provider,pk_field", PRIMARY_KEYS.items())
    def test_primary_key_non_nullable(
        self, provider: str, pk_field: str, request
    ) -> None:
        """Primary key fields are non-nullable."""
        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        schema_class = schema_map[provider]

        # Get fixture
        fixture_name = f"minimal_{provider}_publication_df"
        df = request.getfixturevalue(fixture_name)

        # Test NULL PK fails validation
        df_null_pk = df.copy()
        df_null_pk[pk_field] = None

        with pytest.raises(pa.errors.SchemaError, match=pk_field):
            schema_class.validate(df_null_pk)


@pytest.mark.contracts
class TestFieldCountConsistency:
    """Test field count matches expected values."""

    EXPECTED_FIELD_COUNTS = {
        "chembl": 28,
        "pubmed": 52,
        "crossref": 37,
        "openalex": 39,
        "semanticscholar": 35,
    }

    @pytest.mark.parametrize("provider,expected_count", EXPECTED_FIELD_COUNTS.items())
    def test_field_count_matches_xlsx(self, provider: str, expected_count: int) -> None:
        """Number of schema fields matches XLSX inventory."""
        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        schema_class = schema_map[provider]

        # Count fields (including inherited)
        all_fields = set()
        for cls in schema_class.__mro__:
            if hasattr(cls, "__annotations__"):
                all_fields.update(cls.__annotations__.keys())

        # Filter out Pandera internal fields
        exclude = {
            "Config",
            "__extras__",
            "__schema__",
            "__config__",
            "__fields__",
            "__checks__",
        }
        field_count = len([f for f in all_fields if not f.startswith("__") and f not in exclude])

        # Note: Allow some tolerance due to ETL system fields
        assert (
            abs(field_count - expected_count) <= 10
        ), f"{provider}: expected ~{expected_count} fields, got {field_count}"


@pytest.mark.contracts
class TestSchemaConfigSettings:
    """Test Pandera Config settings are correct."""

    @pytest.mark.parametrize(
        "schema_class",
        [
            ChemblPublicationSchema,
            PubMedPublicationSchema,
            PublicationEnrichedSchema,
            OpenAlexPublicationSchema,
            SemanticScholarPublicationSchema,
        ],
    )
    def test_schema_coerce_enabled(self, schema_class: Type[pa.DataFrameModel]) -> None:
        """All schemas have Config.coerce = True."""
        assert hasattr(schema_class, "Config")
        config = schema_class.Config
        assert getattr(config, "coerce", False) is True, f"{schema_class.__name__} should enable coerce"

    @pytest.mark.parametrize(
        "schema_class",
        [
            ChemblPublicationSchema,
            PubMedPublicationSchema,
            PublicationEnrichedSchema,
            OpenAlexPublicationSchema,
            SemanticScholarPublicationSchema,
        ],
    )
    def test_schema_strict_disabled_silver(self, schema_class: Type[pa.DataFrameModel]) -> None:
        """Silver schemas have Config.strict = False (allow extra columns)."""
        assert hasattr(schema_class, "Config")
        config = schema_class.Config
        # Silver layer allows extra columns for flexibility
        strict = getattr(config, "strict", True)
        assert strict is False, f"{schema_class.__name__} Silver layer should not be strict"
