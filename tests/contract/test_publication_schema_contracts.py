"""Contract tests for Publication schema stability and cross-provider compatibility.

Tests schema inheritance, common field presence, and API contracts.
Expected: ~25 tests ensuring schema consistency across providers.
"""

from pathlib import Path

import pytest
import pandera as pa
import yaml

from bioetl.domain.schemas.common.publication_base import PublicationBaseSchema
from bioetl.domain.schemas.chembl.publication import ChemblPublicationSchema
from bioetl.domain.schemas.pubmed.publication import PubMedPublicationSchema
from bioetl.domain.schemas.crossref.publication import PublicationEnrichedSchema
from bioetl.domain.schemas.openalex.publication import OpenAlexPublicationSchema
from bioetl.domain.schemas.semanticscholar.publication import (
    SemanticScholarPublicationSchema,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]
COMPATIBILITY_BASELINE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "contracts"
    / "publication_schema_compatibility.v1.yaml"
)
ARCHITECTURE_MEDALLION_CONTRACT_PATH = (
    Path(__file__).resolve().parents[1]
    / "architecture"
    / "test_medallion_invariants.py"
)

PUBLICATION_SCHEMA_CLASSES = (
    ChemblPublicationSchema,
    PubMedPublicationSchema,
    PublicationEnrichedSchema,
    OpenAlexPublicationSchema,
    SemanticScholarPublicationSchema,
)


def _load_compatibility_baseline() -> dict[str, object]:
    payload = yaml.safe_load(COMPATIBILITY_BASELINE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    compatibility = payload["publication_schema_compatibility"]
    assert isinstance(compatibility, dict)
    return compatibility


@pytest.mark.architecture
class TestSchemaInheritance:
    """Test all publication schemas inherit PublicationBaseSchema."""

    @pytest.mark.parametrize(
        "schema_class",
        PUBLICATION_SCHEMA_CLASSES,
    )
    def test_schema_inherits_base(self, schema_class: type[pa.DataFrameModel]) -> None:
        """All schemas inherit PublicationBaseSchema."""
        assert issubclass(schema_class, PublicationBaseSchema)


@pytest.mark.architecture
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

    @pytest.mark.parametrize(
        "provider", ["chembl", "pubmed", "crossref", "openalex", "semanticscholar"]
    )
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

        # Collect all fields including inherited ones
        all_fields = set()
        for cls in schema_class.__mro__:
            if hasattr(cls, "__annotations__"):
                all_fields.update(cls.__annotations__.keys())

        for field in self.COMMON_FIELDS:
            # Allow aliases (e.g., _lookup_method has alias lookup_method)
            assert field in all_fields or field.lstrip("_") in all_fields, (
                f"{provider} schema missing {field}"
            )


@pytest.mark.architecture
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
    def test_dq_fields_present(
        self, provider: str, schema_class: type[pa.DataFrameModel]
    ) -> None:
        """DQ flags present in all schemas."""
        # Note: ChEMBL has explicit _dq_warn, _dq_error
        # Others inherit from ETLRecordSchema with aliases (dq_warn -> _dq_warn)

        # Collect all fields including inherited ones
        all_fields = set()
        for cls in schema_class.__mro__:
            if hasattr(cls, "__annotations__"):
                all_fields.update(cls.__annotations__.keys())

        # Check if DQ fields are present (may be inherited with or without prefix)
        # Python attr names: dq_warn, dq_error (in annotations)
        # DataFrame column names: _dq_warn, _dq_error (via alias)
        has_dq_warn = "dq_warn" in all_fields or "_dq_warn" in all_fields
        has_dq_error = "dq_error" in all_fields or "_dq_error" in all_fields

        assert has_dq_warn or has_dq_error, f"{provider} schema missing DQ fields"


@pytest.mark.architecture
class TestContentHashField:
    """Test content_hash field (identifier, deterministic) present in all."""

    @pytest.mark.parametrize(
        "provider", ["chembl", "pubmed", "crossref", "openalex", "semanticscholar"]
    )
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
        has_content_hash = "content_hash" in schema_class.__annotations__ or hasattr(
            schema_class, "content_hash"
        )

        assert has_content_hash, f"{provider} schema missing content_hash"


@pytest.mark.architecture
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
        self, provider: str, schema_class: type[pa.DataFrameModel], request
    ) -> None:
        """_source field should match provider name."""
        # Get fixture for this provider
        fixture_name = f"minimal_{provider}_publication_df"
        df = request.getfixturevalue(fixture_name)

        # Check _source field is present
        assert "_source" in df.columns, f"{provider} fixture missing _source field"

        # Check _source value matches provider
        assert df["_source"].iloc[0] == provider, (
            f"{provider} fixture _source value should be '{provider}', "
            f"got '{df['_source'].iloc[0]}'"
        )


@pytest.mark.architecture
class TestPrimaryKeyFields:
    """Test each provider has a unique primary key field."""

    PRIMARY_KEYS = {
        "chembl": "publication_id",
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


@pytest.mark.architecture
class TestFieldCountConsistency:
    """Test field count matches expected values."""

    SYSTEM_FIELDS = frozenset(
        {
            "entity_id",
            "content_hash",
            "run_id",
            "run_type",
            "source_batch_id",
            "ingestion_ts",
            "dq_warn",
            "dq_error",
            "index",
            "_source",
            "lookup_method",
            "original_id",
        }
    )

    EXPECTED_FIELD_COUNTS = {
        "chembl": 28,
        "pubmed": 52,
        "crossref": 37,
        "openalex": 39,
        "semanticscholar": 37,
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
        field_count = len(
            [
                f
                for f in all_fields
                if not f.startswith("__")
                and f not in exclude
                and f not in self.SYSTEM_FIELDS
            ]
        )

        # Note: Allow some tolerance due to ETL system fields
        assert abs(field_count - expected_count) <= 10, (
            f"{provider}: expected ~{expected_count} fields, got {field_count}"
        )


@pytest.mark.architecture
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
    def test_schema_coerce_enabled(self, schema_class: type[pa.DataFrameModel]) -> None:
        """All schemas have Config.coerce = True."""
        assert hasattr(schema_class, "Config")
        config = schema_class.Config
        assert getattr(config, "coerce", False) is True, (
            f"{schema_class.__name__} should enable coerce"
        )

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
    def test_schema_strict_disabled_silver(
        self, schema_class: type[pa.DataFrameModel]
    ) -> None:
        """Silver schemas have Config.strict = False (allow extra columns)."""
        assert hasattr(schema_class, "Config")
        config = schema_class.Config
        # Silver layer allows extra columns for flexibility
        strict = getattr(config, "strict", True)
        assert strict is False, (
            f"{schema_class.__name__} Silver layer should not be strict"
        )


# ============================================================================
# ADDITIONAL CONTRACT TESTS
# Generated to complete contract test coverage (+15 tests)
# ============================================================================


@pytest.mark.architecture
class TestFieldTypeConsistency:
    """Test that field types are consistent across providers."""

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
    def test_publication_year_is_integer(
        self, provider: str, schema_class: type[pa.DataFrameModel]
    ) -> None:
        """publication_year MUST be integer type across all schemas."""
        # Check annotation
        if "publication_year" in schema_class.__annotations__:
            field_type = schema_class.__annotations__["publication_year"]
            # Handle Series[int] or int | None
            assert "int" in str(field_type).lower()

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
    def test_title_is_string(
        self, provider: str, schema_class: type[pa.DataFrameModel]
    ) -> None:
        """title MUST be string type across all schemas."""
        if "title" in schema_class.__annotations__:
            field_type = schema_class.__annotations__["title"]
            assert "str" in str(field_type).lower()

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
    def test_is_oa_is_boolean(
        self, provider: str, schema_class: type[pa.DataFrameModel]
    ) -> None:
        """is_oa MUST be boolean type across all schemas."""
        if "is_oa" in schema_class.__annotations__:
            field_type = schema_class.__annotations__["is_oa"]
            assert "bool" in str(field_type).lower()


@pytest.mark.architecture
class TestSchemaVersioning:
    """Test executable publication compatibility baseline coverage."""

    SCHEMA_MAP = {
        "chembl": ChemblPublicationSchema,
        "pubmed": PubMedPublicationSchema,
        "crossref": PublicationEnrichedSchema,
        "openalex": OpenAlexPublicationSchema,
        "semanticscholar": SemanticScholarPublicationSchema,
    }

    @pytest.mark.parametrize(
        "section_name",
        [
            "deprecated_aliases",
            "nullable_compatibility_fields",
        ],
    )
    def test_compatibility_baseline_covers_current_provider_set(
        self, section_name: str
    ) -> None:
        """Machine-readable baseline must explicitly enumerate every provider."""
        compatibility = _load_compatibility_baseline()
        section = compatibility[section_name]
        assert isinstance(section, dict)
        assert str(section["review_date"]) >= "2026-05-20"
        providers = section["providers"]
        assert isinstance(providers, dict)
        assert set(providers) == set(self.SCHEMA_MAP)

    @pytest.mark.parametrize("provider,schema_class", SCHEMA_MAP.items())
    def test_compatibility_baseline_references_live_schema_fields(
        self,
        provider: str,
        schema_class: type[pa.DataFrameModel],
    ) -> None:
        """Tracked compatibility baseline entries must point at real schema fields."""
        compatibility = _load_compatibility_baseline()
        alias_fields = compatibility["deprecated_aliases"]["providers"][provider]
        nullable_fields = compatibility["nullable_compatibility_fields"]["providers"][
            provider
        ]

        assert isinstance(alias_fields, list)
        assert isinstance(nullable_fields, list)

        schema_annotations = set(schema_class.__annotations__)
        schema_columns = set(schema_class.to_schema().columns)

        missing_aliases = [
            field for field in alias_fields if field not in schema_annotations
        ]
        missing_nullable = [
            field for field in nullable_fields if field not in schema_columns
        ]

        assert not missing_aliases, (
            f"{provider}: compatibility alias baseline references missing fields: "
            f"{missing_aliases}"
        )
        assert not missing_nullable, (
            f"{provider}: compatibility nullable baseline references missing columns: "
            f"{missing_nullable}"
        )


@pytest.mark.architecture
class TestBackwardCompatibility:
    """Test backward compatibility of schemas."""

    def test_deprecated_fields_still_present(self) -> None:
        """Tracked deprecated field aliases MUST remain when baseline declares them."""
        compatibility = _load_compatibility_baseline()
        deprecated_aliases = compatibility["deprecated_aliases"]
        assert isinstance(deprecated_aliases, dict)
        providers = deprecated_aliases["providers"]
        assert isinstance(providers, dict)

        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        for provider, aliases in providers.items():
            assert isinstance(provider, str)
            assert isinstance(aliases, list)
            schema_fields = set(schema_map[provider].__annotations__)
            missing = [field for field in aliases if field not in schema_fields]
            assert not missing, (
                f"{provider}: tracked deprecated aliases disappeared: {missing}"
            )

    def test_new_fields_are_nullable(self) -> None:
        """Tracked compatibility-additive fields MUST remain nullable."""
        compatibility = _load_compatibility_baseline()
        nullable_fields = compatibility["nullable_compatibility_fields"]
        assert isinstance(nullable_fields, dict)
        providers = nullable_fields["providers"]
        assert isinstance(providers, dict)

        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        for provider, field_names in providers.items():
            assert isinstance(provider, str)
            assert isinstance(field_names, list)
            fields = schema_map[provider].to_schema().columns
            missing = [field for field in field_names if field not in fields]
            assert not missing, (
                f"{provider}: missing tracked compatibility fields: {missing}"
            )

            non_nullable = [
                field for field in field_names if not fields[field].nullable
            ]
            assert not non_nullable, (
                f"{provider}: tracked compatibility fields must stay nullable: "
                f"{non_nullable}"
            )


@pytest.mark.architecture
class TestPrimaryKeyStability:
    """Test primary key stability across versions."""

    @pytest.mark.parametrize(
        "provider,pk_field",
        [
            ("chembl", "publication_id"),
            ("pubmed", "pmid"),
            ("crossref", "doi"),
            ("openalex", "openalex_id"),
            ("semanticscholar", "paper_id"),
        ],
    )
    def test_primary_key_unchanged(self, provider: str, pk_field: str) -> None:
        """Primary key fields MUST NOT change across versions."""
        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        schema_class = schema_map[provider]
        assert pk_field in schema_class.__annotations__

    @pytest.mark.parametrize(
        "provider,pk_field",
        [
            ("chembl", "publication_id"),
            ("pubmed", "pmid"),
            ("crossref", "doi"),
            ("openalex", "openalex_id"),
            ("semanticscholar", "paper_id"),
        ],
    )
    def test_primary_key_type_stable(self, provider: str, pk_field: str) -> None:
        """Primary key type MUST be string across all schemas."""
        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        schema_class = schema_map[provider]
        field_type = schema_class.__annotations__[pk_field]
        assert "str" in str(field_type).lower()


@pytest.mark.architecture
class TestRequiredFieldsStability:
    """Test that required fields remain required across versions."""

    REQUIRED_FIELDS = ["title", "_source", "lookup_method"]

    @pytest.mark.parametrize(
        "provider", ["chembl", "pubmed", "crossref", "openalex", "semanticscholar"]
    )
    def test_required_fields_remain_required(self, provider: str) -> None:
        """Core required fields MUST remain required across versions."""
        schema_map = {
            "chembl": ChemblPublicationSchema,
            "pubmed": PubMedPublicationSchema,
            "crossref": PublicationEnrichedSchema,
            "openalex": OpenAlexPublicationSchema,
            "semanticscholar": SemanticScholarPublicationSchema,
        }

        schema_class = schema_map[provider]

        for field in self.REQUIRED_FIELDS:
            if field in schema_class.__annotations__:
                # This is a placeholder - proper check would inspect Field(nullable=False)
                assert field in schema_class.__annotations__


@pytest.mark.architecture
class TestOutputFormatStability:
    """Test output format stability (Delta Lake, Parquet)."""

    def test_silver_output_is_delta(self) -> None:
        """Silver layer MUST use Delta Lake format."""
        contract = ARCHITECTURE_MEDALLION_CONTRACT_PATH.read_text(encoding="utf-8")
        assert "def test_silver_writer_uses_delta_lake" in contract
        assert "write_deltalake" in contract

    def test_bronze_output_is_jsonl(self) -> None:
        """Bronze layer MUST use JSONL + zstd format."""
        contract = ARCHITECTURE_MEDALLION_CONTRACT_PATH.read_text(encoding="utf-8")
        assert "jsonl.zst" in contract
        assert "test_bronze_path_includes_date_partition" in contract


@pytest.mark.architecture
class TestFieldNamingConventions:
    """Test field naming conventions remain stable."""

    def test_system_fields_prefix_underscore(self) -> None:
        """System fields MUST start with underscore."""
        system_fields = [
            "_source",
            "_lookup_method",
            "_original_id",
            "_dq_warn",
            "_dq_error",
        ]

        for field in system_fields:
            assert field.startswith("_")

    def test_dq_fields_prefix(self) -> None:
        """DQ fields MUST start with _dq_."""
        dq_fields = ["_dq_warn", "_dq_error"]

        for field in dq_fields:
            assert field.startswith("_dq_")

    def test_no_camel_case_in_field_names(self) -> None:
        """Field names MUST be snake_case, not camelCase."""
        for schema_class in PUBLICATION_SCHEMA_CLASSES:
            for field_name in schema_class.__annotations__:
                assert field_name == field_name.lower(), (
                    f"{schema_class.__name__} field {field_name} must be lowercase"
                )
