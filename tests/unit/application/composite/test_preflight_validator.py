"""Tests for CompositePreflightValidationService.

Tests preflight validation of field_priorities configuration against source schemas,
including negative cases for:
- Missing fields
- Unknown sources
- Type mismatches
"""

from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
    FieldInfo,
    PreflightValidationError,
    PreflightValidationResult,
    ValidationIssue,
)
from bioetl.domain.composite.config import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    CompositeConfig,
    CompositeDQConfig,
    DependencyConfig,
    EnricherConfig,
    EnricherCardinality,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.infrastructure.config.composite_config_api import load_composite_config


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def validator(mock_logger: MagicMock) -> CompositePreflightValidationService:
    """Create CompositePreflightValidationService instance."""
    return CompositePreflightValidationService(mock_logger)


@pytest.fixture
def basic_composite_config() -> CompositeConfig:
    """Create basic composite config for testing."""
    return CompositeConfig(
        name="test_composite",
        version="1.0.0",
        seed=SeedConfig(
            pipeline="chembl_publication",
            output_keys=("publication_id", "doi", "pmid"),
            silver_table="silver/chembl/publication",
        ),
        enrichers=(
            EnricherConfig(
                pipeline="crossref_publication",
                join_keys=("doi",),
            ),
            EnricherConfig(
                pipeline="pubmed_publication",
                join_keys=("pmid",),
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.EXPLICIT_RULES,
            output_silver_path="silver/composite/test",
            output_gold_path="gold/composite/test",
            field_priorities={
                "title": ("chembl", "crossref", "pubmed"),
                "abstract": ("pubmed", "chembl"),
                "citation_count": ("crossref", "pubmed"),
            },
        ),
        dq=CompositeDQConfig(),
    )


class TestFieldInfo:
    """Tests for FieldInfo dataclass."""

    def test_field_info_creation(self) -> None:
        """FieldInfo stores field metadata."""
        info = FieldInfo(
            name="title",
            dtype="str",
            nullable=True,
            source="chembl",
        )
        assert info.name == "title"
        assert info.dtype == "str"
        assert info.nullable is True
        assert info.source == "chembl"

    def test_field_info_immutable(self) -> None:
        """FieldInfo is immutable."""
        info = FieldInfo(name="title", dtype="str", nullable=True, source="chembl")
        with pytest.raises(AttributeError):
            info.name = "changed"  # type: ignore[misc]


class TestValidationIssue:
    """Tests for ValidationIssue dataclass."""

    def test_validation_issue_error(self) -> None:
        """ValidationIssue captures error information."""
        issue = ValidationIssue(
            field="title",
            source="unknown_source",
            issue_type="unknown_source",
            message="Source 'unknown_source' not found",
            severity="error",
        )
        assert issue.field == "title"
        assert issue.source == "unknown_source"
        assert issue.issue_type == "unknown_source"
        assert issue.severity == "error"

    def test_validation_issue_default_severity(self) -> None:
        """ValidationIssue defaults to error severity."""
        issue = ValidationIssue(
            field="title",
            source="chembl",
            issue_type="missing_field",
            message="Field not found",
        )
        assert issue.severity == "error"


class TestPreflightValidationResult:
    """Tests for PreflightValidationResult."""

    def test_valid_result(self) -> None:
        """Valid result has is_valid=True and no errors."""
        result = PreflightValidationResult(
            is_valid=True,
            issues=[],
            resolved_fields={"title": "chembl", "abstract": "pubmed"},
        )
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.resolved_fields["title"] == "chembl"

    def test_invalid_result_with_errors(self) -> None:
        """Invalid result has errors."""
        result = PreflightValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    field="missing_field",
                    source="chembl",
                    issue_type="missing_field",
                    message="Field not found",
                    severity="error",
                ),
                ValidationIssue(
                    field="title",
                    source="openalex",
                    issue_type="missing_field",
                    message="Field not in source",
                    severity="warning",
                ),
            ],
            resolved_fields={},
        )
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.errors[0].field == "missing_field"
        assert result.warnings[0].field == "title"

    def test_result_can_store_profile_refs(self) -> None:
        result = PreflightValidationResult(
            is_valid=True,
            profile_refs={},
        )

        assert result.profile_refs == {}


class TestPreflightValidationError:
    """Tests for PreflightValidationError exception."""

    def test_error_message_format(self) -> None:
        """PreflightValidationError formats error message correctly."""
        result = PreflightValidationResult(
            is_valid=False,
            issues=[
                ValidationIssue(
                    field="unknown_field",
                    source="chembl,crossref",
                    issue_type="missing_field",
                    message="Field 'unknown_field' not found in ANY source schema",
                    severity="error",
                ),
            ],
        )
        error = PreflightValidationError(result)
        assert "preflight validation failed" in str(error).lower()
        assert "unknown_field" in str(error)
        assert error.result == result


class TestCompositePreflightValidationServiceBasic:
    """Basic tests for CompositePreflightValidationService."""

    def test_get_valid_sources(
        self,
        validator: CompositePreflightValidationService,
        basic_composite_config: CompositeConfig,
    ) -> None:
        """Validator extracts valid source names from config."""
        sources = validator._get_valid_sources(basic_composite_config)

        assert "seed" in sources
        assert "chembl" in sources
        assert "crossref" in sources
        assert "pubmed" in sources

    def test_get_valid_sources_includes_dependency_and_qualified_tokens(
        self,
        validator: CompositePreflightValidationService,
    ) -> None:
        config = CompositeConfig(
            name="test_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_activity",
                output_keys=("activity_id", "molecule_id", "publication_id"),
                silver_table="silver/chembl/activity",
            ),
            dependencies=(
                DependencyConfig(
                    pipeline="chembl_compound_record",
                    join_keys=("molecule_id", "publication_id"),
                ),
            ),
            enrichers=(),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.EXPLICIT_RULES,
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
                field_priorities={
                    "molecule_id": ("chembl.activity",),
                },
            ),
        )

        sources = validator._get_valid_sources(config)

        assert "seed" in sources
        assert "chembl" in sources
        assert "chembl.activity" in sources
        assert "chembl_activity" in sources
        assert "chembl.compound_record" in sources

    def test_validate_fails_on_field_level_normalization_mismatch_without_override(
        self,
        validator: CompositePreflightValidationService,
        basic_composite_config: CompositeConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source_fields = {
            "chembl": {"title": FieldInfo("title", "str", True, "chembl")},
            "chembl_publication": {"title": FieldInfo("title", "str", True, "chembl")},
            "chembl.publication": {"title": FieldInfo("title", "str", True, "chembl")},
            "crossref": {"title": FieldInfo("title", "str", True, "crossref")},
            "crossref_publication": {
                "title": FieldInfo("title", "str", True, "crossref")
            },
            "crossref.publication": {
                "title": FieldInfo("title", "str", True, "crossref")
            },
            "pubmed": {"title": FieldInfo("title", "str", True, "pubmed")},
            "pubmed_publication": {"title": FieldInfo("title", "str", True, "pubmed")},
            "pubmed.publication": {"title": FieldInfo("title", "str", True, "pubmed")},
        }
        source_profiles = {
            "chembl": MagicMock(field_hashes={"title": "chembl-hash"}),
            "chembl_publication": MagicMock(field_hashes={"title": "chembl-hash"}),
            "chembl.publication": MagicMock(field_hashes={"title": "chembl-hash"}),
            "crossref": MagicMock(field_hashes={"title": "crossref-hash"}),
            "crossref_publication": MagicMock(field_hashes={"title": "crossref-hash"}),
            "crossref.publication": MagicMock(field_hashes={"title": "crossref-hash"}),
            "pubmed": MagicMock(field_hashes={"title": "pubmed-hash"}),
            "pubmed_publication": MagicMock(field_hashes={"title": "pubmed-hash"}),
            "pubmed.publication": MagicMock(field_hashes={"title": "pubmed-hash"}),
        }

        monkeypatch.setattr(validator, "_load_source_fields", lambda _: source_fields)
        monkeypatch.setattr(
            validator, "_load_source_profiles", lambda _: source_profiles
        )

        with pytest.raises(PreflightValidationError, match="title"):
            validator.validate(basic_composite_config)

    def test_validate_allows_declared_normalization_override(
        self,
        validator: CompositePreflightValidationService,
        basic_composite_config: CompositeConfig,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        source_fields = {
            "chembl": {"title": FieldInfo("title", "str", True, "chembl")},
            "chembl_publication": {"title": FieldInfo("title", "str", True, "chembl")},
            "chembl.publication": {"title": FieldInfo("title", "str", True, "chembl")},
            "crossref": {"title": FieldInfo("title", "str", True, "crossref")},
            "crossref_publication": {
                "title": FieldInfo("title", "str", True, "crossref")
            },
            "crossref.publication": {
                "title": FieldInfo("title", "str", True, "crossref")
            },
            "pubmed": {"title": FieldInfo("title", "str", True, "pubmed")},
            "pubmed_publication": {"title": FieldInfo("title", "str", True, "pubmed")},
            "pubmed.publication": {"title": FieldInfo("title", "str", True, "pubmed")},
        }
        source_profiles = {
            "chembl": MagicMock(field_hashes={"title": "chembl-hash"}),
            "chembl_publication": MagicMock(field_hashes={"title": "chembl-hash"}),
            "chembl.publication": MagicMock(field_hashes={"title": "chembl-hash"}),
            "crossref": MagicMock(field_hashes={"title": "crossref-hash"}),
            "crossref_publication": MagicMock(field_hashes={"title": "crossref-hash"}),
            "crossref.publication": MagicMock(field_hashes={"title": "crossref-hash"}),
            "pubmed": MagicMock(field_hashes={"title": "pubmed-hash"}),
            "pubmed_publication": MagicMock(field_hashes={"title": "pubmed-hash"}),
            "pubmed.publication": MagicMock(field_hashes={"title": "pubmed-hash"}),
        }
        config = CompositeConfig(
            name=basic_composite_config.name,
            version=basic_composite_config.version,
            seed=basic_composite_config.seed,
            enrichers=basic_composite_config.enrichers,
            merge=MergeConfig(
                strategy=basic_composite_config.merge.strategy,
                conflict_resolution=basic_composite_config.merge.conflict_resolution,
                output_silver_path=basic_composite_config.merge.output_silver_path,
                output_gold_path=basic_composite_config.merge.output_gold_path,
                field_priorities=basic_composite_config.merge.field_priorities,
                normalization_compatibility_overrides={
                    "title": "reviewed publication bridge"
                },
            ),
            dq=basic_composite_config.dq,
        )

        monkeypatch.setattr(validator, "_load_source_fields", lambda _: source_fields)
        monkeypatch.setattr(
            validator, "_load_source_profiles", lambda _: source_profiles
        )

        result = validator.validate(config, fail_on_error=False)
        sources = validator._get_valid_sources(config)

        assert result.is_valid is False
        assert all(
            issue.issue_type != "normalization_profile_mismatch"
            for issue in result.issues
        )
        assert "chembl_publication" in sources

    def test_simplify_dtype_common_types(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Validator simplifies common dtype strings."""
        assert validator._simplify_dtype("Int64Dtype()") == "int"
        assert validator._simplify_dtype("Int64") == "int"
        assert validator._simplify_dtype("Float64") == "float"
        assert validator._simplify_dtype("object") == "str"
        assert validator._simplify_dtype("String") == "str"
        assert validator._simplify_dtype("boolean") == "bool"

    def test_dtype_in_group_string_types(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """String types are in same compatibility group."""
        str_group = frozenset({"str", "object", "String"})
        assert validator._dtype_in_group("str", str_group)
        assert validator._dtype_in_group("String", str_group)
        assert validator._dtype_in_group("object", str_group)

    def test_dtype_in_group_numeric_types(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Numeric types are in same compatibility group."""
        num_group = frozenset(
            {"int", "Int64", "int64", "Int64Dtype", "float", "Float64", "float64"}
        )
        assert validator._dtype_in_group("int", num_group)
        assert validator._dtype_in_group("float", num_group)
        assert validator._dtype_in_group("Int64", num_group)


class TestCompositePreflightValidationServiceValidation:
    """Tests for validation logic."""

    def test_validate_skips_when_no_field_priorities(
        self, validator: CompositePreflightValidationService, mock_logger: MagicMock
    ) -> None:
        """Validation passes when no field_priorities configured."""
        config = CompositeConfig(
            name="test_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("publication_id", "doi"),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.SEED_PRIORITY,
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
                field_priorities={},  # Empty - no validation needed
            ),
        )

        result = validator.validate(config, fail_on_error=False)
        assert result.is_valid is True
        assert result.issues == []

    def test_validate_unknown_source_error(
        self, validator: CompositePreflightValidationService, mock_logger: MagicMock
    ) -> None:
        """Validation fails for unknown source in field_priorities."""
        config = CompositeConfig(
            name="test_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("publication_id", "doi"),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.EXPLICIT_RULES,
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
                field_priorities={
                    "title": ("chembl", "unknown_provider", "crossref"),
                },
            ),
        )

        result = validator.validate(config, fail_on_error=False)

        # Should have unknown_source error
        unknown_issues = [i for i in result.issues if i.issue_type == "unknown_source"]
        assert len(unknown_issues) >= 1
        assert unknown_issues[0].source == "unknown_provider"

    def test_validate_missing_field_in_all_sources_error(
        self, validator: CompositePreflightValidationService, mock_logger: MagicMock
    ) -> None:
        """Validation fails when field doesn't exist in ANY source."""
        config = CompositeConfig(
            name="test_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("publication_id", "doi"),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.EXPLICIT_RULES,
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
                field_priorities={
                    "completely_nonexistent_field_xyz123": ("chembl", "crossref"),
                },
            ),
        )

        result = validator.validate(config, fail_on_error=False)

        # Should have missing_field error (not just warnings)
        missing_errors = [i for i in result.errors if i.issue_type == "missing_field"]
        assert len(missing_errors) >= 1
        assert "completely_nonexistent_field_xyz123" in missing_errors[0].field

    def test_validate_raises_on_error_when_fail_on_error_true(
        self, validator: CompositePreflightValidationService, mock_logger: MagicMock
    ) -> None:
        """Validation raises PreflightValidationError when fail_on_error=True."""
        config = CompositeConfig(
            name="test_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("publication_id", "doi"),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.EXPLICIT_RULES,
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
                field_priorities={
                    "nonexistent_field": ("chembl", "crossref"),
                },
            ),
        )

        with pytest.raises(PreflightValidationError) as exc_info:
            validator.validate(config, fail_on_error=True)

        assert exc_info.value.result.is_valid is False
        assert len(exc_info.value.result.errors) >= 1

    def test_validate_rejects_many_to_one_aggregation_without_order_by(
        self,
        validator: CompositePreflightValidationService,
    ) -> None:
        """Order-sensitive many-to-one aggregation must declare deterministic order."""
        config = CompositeConfig(
            name="test_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("publication_id",),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(
                    pipeline="publication_terms",
                    join_keys=("publication_id",),
                    cardinality=EnricherCardinality.MANY_TO_ONE,
                    aggregation=AggregationConfig(
                        group_by="publication_id",
                        fields=(
                            AggregationFieldSpec(
                                source_field="term",
                                agg_function=AggregationFunction.COLLECT_LIST,
                            ),
                        ),
                    ),
                ),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.SEED_PRIORITY,
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
                field_priorities={},
            ),
        )

        result = validator.validate(config, fail_on_error=False)

        issues = [
            issue
            for issue in result.errors
            if issue.issue_type == "missing_deterministic_order"
        ]
        assert len(issues) == 1
        assert issues[0].field == "aggregation.order_by"

    def test_validate_accepts_many_to_one_aggregation_with_order_by(
        self,
        validator: CompositePreflightValidationService,
    ) -> None:
        """Explicit order_by makes order-sensitive many-to-one aggregation valid."""
        config = CompositeConfig(
            name="test_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("publication_id",),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(
                    pipeline="publication_terms",
                    join_keys=("publication_id",),
                    cardinality=EnricherCardinality.MANY_TO_ONE,
                    aggregation=AggregationConfig(
                        group_by="publication_id",
                        order_by=("rank",),
                        fields=(
                            AggregationFieldSpec(
                                source_field="term",
                                agg_function=AggregationFunction.COLLECT_LIST,
                            ),
                        ),
                    ),
                ),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.SEED_PRIORITY,
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
                field_priorities={},
            ),
        )

        result = validator.validate(config, fail_on_error=False)

        assert result.errors == []


class TestCompositePreflightValidationServiceWithSchemas:
    """Tests that use actual schema registry."""

    def test_validate_valid_field_priorities(
        self, validator: CompositePreflightValidationService, mock_logger: MagicMock
    ) -> None:
        """Validation passes for valid field_priorities with real schemas."""
        config = CompositeConfig(
            name="test_composite",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("publication_id", "doi", "pmid"),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(pipeline="crossref_publication", join_keys=("doi",)),
                EnricherConfig(pipeline="pubmed_publication", join_keys=("pmid",)),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.EXPLICIT_RULES,
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
                field_priorities={
                    # These fields exist in the schemas
                    "title": ("chembl", "crossref", "pubmed"),
                    "abstract": ("pubmed", "chembl"),
                    "doi": ("chembl", "crossref"),
                },
                normalization_compatibility_overrides={
                    "title": "reviewed publication bridge",
                    "abstract": "reviewed publication bridge",
                    "doi": "reviewed publication bridge",
                },
            ),
        )

        result = validator.validate(config, fail_on_error=False)

        assert result.is_valid is True
        assert result.errors == []
        # Should have resolved fields
        assert len(result.resolved_fields) > 0

    def test_activity_composite_loads_dependency_schema_surface(
        self,
        validator: CompositePreflightValidationService,
    ) -> None:
        """Dependency-backed composite should load dependency entity schema."""
        config = load_composite_config("activity")

        source_fields = validator._load_source_fields(config)

        assert "chembl.compound_record" in source_fields
        dependency_fields = source_fields["chembl.compound_record"]
        assert "record_id" in dependency_fields
        assert "doi" not in dependency_fields

    def test_log_resolved_field_sources(
        self, validator: CompositePreflightValidationService, mock_logger: MagicMock
    ) -> None:
        """Validator logs resolved field sources."""
        result = PreflightValidationResult(
            is_valid=True,
            issues=[],
            resolved_fields={
                "title": "chembl",
                "abstract": "pubmed",
                "citation_count": "crossref",
            },
        )

        validator.log_resolved_field_sources(result, "test_composite")

        # Check that info was logged
        mock_logger.info.assert_called()
        # Check debug was called for each field
        assert mock_logger.debug.call_count >= 3


class TestTypeCompatibility:
    """Tests for type compatibility checking."""

    def test_check_type_compatibility_same_types(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Same types are compatible."""
        result = validator._check_type_compatibility(
            "title",
            {"chembl": "str", "crossref": "str", "pubmed": "str"},
        )
        assert result is None  # No issue

    def test_check_type_compatibility_compatible_types(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Types in same group are compatible."""
        # String types
        result = validator._check_type_compatibility(
            "title",
            {"chembl": "str", "crossref": "String", "pubmed": "object"},
        )
        assert result is None  # No issue

        # Numeric types
        result = validator._check_type_compatibility(
            "count",
            {"chembl": "int", "crossref": "Int64", "pubmed": "float"},
        )
        assert result is None  # No issue

    def test_check_type_compatibility_incompatible_types(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Incompatible types return validation issue."""
        result = validator._check_type_compatibility(
            "mixed_field",
            {"chembl": "str", "crossref": "int", "pubmed": "bool"},
        )
        assert result is not None
        assert result.issue_type == "type_mismatch"
        assert result.severity == "error"
        assert "mixed_field" in result.message


class TestValidateFieldPriority:
    """Tests for _validate_field_priority method."""

    def test_validate_field_priority_all_valid(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """All valid sources and fields return no issues."""
        valid_sources = frozenset({"seed", "chembl", "crossref", "pubmed"})
        source_fields = {
            "chembl": {
                "title": FieldInfo("title", "str", True, "chembl"),
            },
            "crossref": {
                "title": FieldInfo("title", "str", True, "crossref"),
            },
            "pubmed": {
                "title": FieldInfo("title", "str", True, "pubmed"),
            },
            "seed": {
                "title": FieldInfo("title", "str", True, "seed"),
            },
        }

        issues, resolved = validator._validate_field_priority(
            field_name="title",
            priorities=("chembl", "crossref", "pubmed"),
            valid_sources=valid_sources,
            source_fields=source_fields,
        )

        # No errors (warnings are OK)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0
        assert resolved == "chembl"  # First source with field

    def test_validate_field_priority_unknown_source(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Unknown source in priorities returns error."""
        valid_sources = frozenset({"seed", "chembl"})
        source_fields = {
            "chembl": {"title": FieldInfo("title", "str", True, "chembl")},
            "seed": {"title": FieldInfo("title", "str", True, "seed")},
        }

        issues, _resolved = validator._validate_field_priority(
            field_name="title",
            priorities=("unknown", "chembl"),
            valid_sources=valid_sources,
            source_fields=source_fields,
        )

        unknown_issues = [i for i in issues if i.issue_type == "unknown_source"]
        assert len(unknown_issues) == 1
        assert unknown_issues[0].source == "unknown"

    def test_validate_field_priority_missing_in_some_sources_warning(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Field missing in some sources returns warning (not error)."""
        valid_sources = frozenset({"seed", "chembl", "crossref"})
        source_fields = {
            "chembl": {
                "title": FieldInfo("title", "str", True, "chembl"),
            },
            "crossref": {},  # No title field
            "seed": {
                "title": FieldInfo("title", "str", True, "seed"),
            },
        }

        issues, resolved = validator._validate_field_priority(
            field_name="title",
            priorities=("chembl", "crossref"),
            valid_sources=valid_sources,
            source_fields=source_fields,
        )

        # Should have warning for crossref
        warnings = [i for i in issues if i.severity == "warning"]
        assert len(warnings) >= 1
        assert any("crossref" in w.source for w in warnings)
        # Should still resolve to chembl
        assert resolved == "chembl"

    def test_validate_field_priority_missing_in_all_sources_error(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Field missing in ALL sources returns error."""
        valid_sources = frozenset({"seed", "chembl", "crossref"})
        source_fields = {
            "chembl": {},  # No such field
            "crossref": {},  # No such field
            "seed": {},  # No such field
        }

        issues, resolved = validator._validate_field_priority(
            field_name="nonexistent",
            priorities=("chembl", "crossref"),
            valid_sources=valid_sources,
            source_fields=source_fields,
        )

        # Should have error
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) >= 1
        assert "nonexistent" in errors[0].message
        # No resolved source
        assert resolved is None

    def test_validate_field_priority_supports_pipeline_token(
        self, validator: CompositePreflightValidationService
    ) -> None:
        """Pipeline-id source tokens should resolve against source field map."""
        valid_sources = frozenset(
            {
                "seed",
                "chembl",
                "chembl.activity",
                "chembl_activity",
                "chembl.compound_record",
                "chembl_compound_record",
            }
        )
        source_fields = {
            "chembl_compound_record": {
                "record_id": FieldInfo("record_id", "int", False, "dependency"),
            },
        }

        issues, resolved = validator._validate_field_priority(
            field_name="record_id",
            priorities=("chembl_compound_record",),
            valid_sources=valid_sources,
            source_fields=source_fields,
        )

        errors = [i for i in issues if i.severity == "error"]
        assert errors == []
        assert resolved == "chembl_compound_record"
