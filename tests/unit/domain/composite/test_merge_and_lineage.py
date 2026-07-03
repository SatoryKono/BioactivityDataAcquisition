"""Tests for composite merge and lineage internal modules.

This test file provides focused coverage for composite merge/lineage internal modules:
- aggregation.py: AggregationFunction, EnricherCardinality, AggregationConfig
- strategy.py: MergeStrategy, ConflictResolution, FallbackStrategy
- result_merge.py: MergeResult
- result_composite.py: CompositeResult

These tests complement existing test_lineage.py and test_state.py by testing
merge-related value objects, strategy enums, and result models directly.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    EnricherCardinality,
)
from bioetl.domain.composite.result_composite import CompositeResult
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.composite.result_seed_dependency import (
    DependencyResult,
    DependencyStatus,
    SeedResult,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)

pytestmark = pytest.mark.unit


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def seed_result():
    """Create a sample SeedResult."""
    return SeedResult(
        pipeline_name="seed_pipeline",
        records_silver=100,
    )


@pytest.fixture
def dependency_result():
    """Create a sample DependencyResult."""
    return DependencyResult(
        pipeline_name="dep_pipeline",
        status=DependencyStatus.SUCCESS,
        records_silver=50,
    )


@pytest.fixture
def merge_result():
    """Create a sample MergeResult."""
    return MergeResult(
        records_merged=100,
        records_from_seed=100,
        records_enriched=80,
        records_fully_enriched=60,
        sources_used=("chembl", "crossref"),
        field_coverage={"title": 0.8, "doi": 0.9},
        duration_seconds=10.5,
        output_silver_path="data/silver/merged.parquet",
        output_gold_path="data/gold/merged.parquet",
    )


# ──────────────────────────────────────────────────────────────────────────────
# aggregation.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestAggregationFunction:
    """Tests for AggregationFunction enum."""

    def test_all_aggregation_functions_defined(self):
        """All required aggregation functions should be defined."""
        expected = {
            "COLLECT_LIST",
            "COLLECT_SET",
            "COUNT",
            "FIRST",
            "CONCAT_STR",
        }
        actual = {func.name for func in AggregationFunction}
        assert actual == expected

    def test_merge_lineage_aggregation_function_from_string_valid(self):
        """from_string should parse valid aggregation function strings."""
        assert (
            AggregationFunction.from_string("collect_list")
            == AggregationFunction.COLLECT_LIST
        )
        assert (
            AggregationFunction.from_string("COLLECT_LIST")
            == AggregationFunction.COLLECT_LIST
        )
        assert (
            AggregationFunction.from_string("Collect_List")
            == AggregationFunction.COLLECT_LIST
        )

    def test_merge_lineage_aggregation_function_from_string_invalid(self):
        """from_string should raise ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid aggregation function"):
            AggregationFunction.from_string("invalid_func")

    def test_merge_lineage_aggregation_function_lists_valid_options_on_error(self):
        """from_string error should list valid options."""
        with pytest.raises(ValueError) as exc_info:
            AggregationFunction.from_string("bogus")
        assert "collect_list" in str(exc_info.value)
        assert "count" in str(exc_info.value)


class TestEnricherCardinality:
    """Tests for EnricherCardinality enum."""

    def test_all_cardinalities_defined(self):
        """All required cardinalities should be defined."""
        expected = {"ONE_TO_ONE", "MANY_TO_ONE"}
        actual = {card.name for card in EnricherCardinality}
        assert actual == expected

    def test_merge_lineage_enricher_cardinality_from_string_valid(self):
        """from_string should parse valid cardinality strings."""
        assert (
            EnricherCardinality.from_string("one_to_one")
            == EnricherCardinality.ONE_TO_ONE
        )
        assert (
            EnricherCardinality.from_string("MANY_TO_ONE")
            == EnricherCardinality.MANY_TO_ONE
        )

    def test_merge_lineage_enricher_cardinality_from_string_invalid(self):
        """from_string should raise ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid cardinality"):
            EnricherCardinality.from_string("invalid_cardinality")


class TestAggregationFieldSpec:
    """Tests for AggregationFieldSpec dataclass."""

    def test_create_field_spec_minimal(self):
        """Create AggregationFieldSpec with minimal required fields."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )

        assert spec.source_field == "term"
        assert spec.agg_function == AggregationFunction.COLLECT_LIST
        assert spec.filter_condition is None
        assert spec.output_field is None

    def test_create_field_spec_full(self):
        """Create AggregationFieldSpec with all fields."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_SET,
            filter_condition="term_type == 'MESH_HEADING'",
            output_field="mesh_terms",
        )

        assert spec.filter_condition == "term_type == 'MESH_HEADING'"
        assert spec.output_field == "mesh_terms"

    def test_field_spec_coerces_string_function(self):
        """AggregationFieldSpec should coerce string to AggregationFunction."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function="collect_list",  # String
        )

        assert spec.agg_function == AggregationFunction.COLLECT_LIST

    def test_field_spec_validates_source_field(self):
        """AggregationFieldSpec should validate non-empty source_field."""
        with pytest.raises(
            ValueError, match="aggregation source_field cannot be empty"
        ):
            AggregationFieldSpec(
                source_field="",
                agg_function=AggregationFunction.COLLECT_LIST,
            )

    def test_effective_output_field_defaults_to_source(self):
        """effective_output_field should default to source_field when output_field is None."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )

        assert spec.effective_output_field == "term"

    def test_effective_output_field_uses_custom(self):
        """effective_output_field should use custom output_field when set."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
            output_field="custom_term",
        )

        assert spec.effective_output_field == "custom_term"

    def test_field_spec_is_frozen(self):
        """AggregationFieldSpec should be frozen (immutable)."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )

        with pytest.raises(AttributeError):
            spec.source_field = "new_term"  # type: ignore


class TestAggregationConfig:
    """Tests for AggregationConfig dataclass."""

    def test_create_aggregation_config_minimal(self):
        """Create AggregationConfig with minimal required fields."""
        field_spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )
        config = AggregationConfig(
            group_by="document_chembl_id",
            fields=(field_spec,),
        )

        assert config.group_by == "document_chembl_id"
        assert len(config.fields) == 1
        assert config.order_by == ()

    def test_create_aggregation_config_full(self):
        """Create AggregationConfig with all fields."""
        field_spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )
        config = AggregationConfig(
            group_by="document_chembl_id",
            fields=(field_spec,),
            order_by=("term", "term_type"),
        )

        assert config.order_by == ("term", "term_type")

    def test_aggregation_config_coerces_list_fields(self):
        """AggregationConfig should coerce list of fields to tuple."""
        field_spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )
        config = AggregationConfig(
            group_by="document_chembl_id",
            fields=[field_spec],  # List
        )

        assert isinstance(config.fields, tuple)

    def test_aggregation_config_coerces_dict_fields(self):
        """AggregationConfig should coerce dict fields to AggregationFieldSpec."""
        config = AggregationConfig(
            group_by="document_chembl_id",
            fields=[
                {
                    "source_field": "term",
                    "agg_function": "collect_list",
                }
            ],
        )

        assert len(config.fields) == 1
        assert isinstance(config.fields[0], AggregationFieldSpec)

    def test_aggregation_config_validates_group_by(self):
        """AggregationConfig should validate non-empty group_by."""
        field_spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )

        with pytest.raises(ValueError, match="aggregation group_by cannot be empty"):
            AggregationConfig(
                group_by="",
                fields=(field_spec,),
            )

    def test_aggregation_config_validates_fields_not_empty(self):
        """AggregationConfig should validate fields is not empty."""
        with pytest.raises(ValueError, match="aggregation.fields cannot be empty"):
            AggregationConfig(
                group_by="document_chembl_id",
                fields=(),
            )

    def test_aggregation_config_is_frozen(self):
        """AggregationConfig should be frozen (immutable)."""
        field_spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )
        config = AggregationConfig(
            group_by="document_chembl_id",
            fields=(field_spec,),
        )

        with pytest.raises(AttributeError):
            config.group_by = "new_group"  # type: ignore


# ──────────────────────────────────────────────────────────────────────────────
# strategy.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestMergeStrategy:
    """Tests for MergeStrategy enum."""

    def test_all_merge_strategies_defined(self):
        """All required merge strategies should be defined."""
        expected = {"LEFT_OUTER", "INNER", "UNION"}
        actual = {strategy.name for strategy in MergeStrategy}
        assert actual == expected

    def test_merge_lineage_merge_strategy_from_string_valid(self):
        """from_string should parse valid merge strategy strings."""
        assert MergeStrategy.from_string("left_outer") == MergeStrategy.LEFT_OUTER
        assert MergeStrategy.from_string("INNER") == MergeStrategy.INNER

    def test_merge_lineage_merge_strategy_from_string_invalid(self):
        """from_string should raise ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid merge strategy"):
            MergeStrategy.from_string("invalid_strategy")

    def test_merge_lineage_merge_strategy_lists_valid_options_on_error(self):
        """from_string error should list valid options."""
        with pytest.raises(ValueError) as exc_info:
            MergeStrategy.from_string("bogus")
        assert "left_outer" in str(exc_info.value)
        assert "inner" in str(exc_info.value)


class TestConflictResolution:
    """Tests for ConflictResolution enum."""

    def test_all_conflict_resolutions_defined(self):
        """All required conflict resolutions should be defined."""
        expected = {
            "SEED_PRIORITY",
            "ENRICHER_PRIORITY",
            "LATEST_TIMESTAMP",
            "EXPLICIT_RULES",
            "COALESCE",
        }
        actual = {resolution.name for resolution in ConflictResolution}
        assert actual == expected

    def test_merge_lineage_conflict_resolution_from_string_valid(self):
        """from_string should parse valid conflict resolution strings."""
        assert (
            ConflictResolution.from_string("seed_priority")
            == ConflictResolution.SEED_PRIORITY
        )
        assert ConflictResolution.from_string("COALESCE") == ConflictResolution.COALESCE

    def test_merge_lineage_conflict_resolution_from_string_invalid(self):
        """from_string should raise ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid conflict resolution"):
            ConflictResolution.from_string("invalid_resolution")


class TestFallbackStrategy:
    """Tests for FallbackStrategy enum."""

    def test_all_fallback_strategies_defined(self):
        """All required fallback strategies should be defined."""
        expected = {"SKIP", "USE_CACHED", "FAIL"}
        actual = {strategy.name for strategy in FallbackStrategy}
        assert actual == expected

    def test_merge_lineage_fallback_strategy_from_string_valid(self):
        """from_string should parse valid fallback strategy strings."""
        assert FallbackStrategy.from_string("skip") == FallbackStrategy.SKIP
        assert FallbackStrategy.from_string("FAIL") == FallbackStrategy.FAIL

    def test_merge_lineage_fallback_strategy_from_string_invalid(self):
        """from_string should raise ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid fallback strategy"):
            FallbackStrategy.from_string("invalid_strategy")


# ──────────────────────────────────────────────────────────────────────────────
# result_merge.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestMergeResult:
    """Tests for MergeResult dataclass."""

    def test_create_merge_result_minimal(self):
        """Create MergeResult with minimal fields."""
        result = MergeResult()

        assert result.records_merged == 0
        assert result.records_from_seed == 0
        assert result.records_enriched == 0
        assert result.sources_used == ()

    def test_create_merge_result_full(self, merge_result):
        """Create MergeResult with all fields."""
        assert merge_result.records_merged == 100
        assert merge_result.records_from_seed == 100
        assert merge_result.records_enriched == 80
        assert merge_result.sources_used == ("chembl", "crossref")
        assert merge_result.duration_seconds == 10.5

    def test_merge_result_coerces_list_sources(self):
        """MergeResult should coerce list sources_used to tuple."""
        result = MergeResult(
            sources_used=["chembl", "crossref"],  # List
        )

        assert isinstance(result.sources_used, tuple)

    def test_merge_result_coerces_list_quarantine(self):
        """MergeResult should coerce list quarantine_payloads to tuple."""
        result = MergeResult(
            quarantine_payloads=[{"id": "1"}, {"id": "2"}],  # List
        )

        assert isinstance(result.quarantine_payloads, tuple)

    def test_enrichment_rate_calculates_correctly(self):
        """enrichment_rate should calculate correctly."""
        result = MergeResult(
            records_merged=100,
            records_enriched=80,
        )

        assert result.enrichment_rate == 0.8

    def test_enrichment_rate_zero_when_no_records(self):
        """enrichment_rate should return 0.0 when no records merged."""
        result = MergeResult(records_merged=0, records_enriched=0)

        assert result.enrichment_rate == 0.0

    def test_merge_result_is_frozen(self):
        """MergeResult should be frozen (immutable)."""
        result = MergeResult(records_merged=100)

        with pytest.raises(AttributeError):
            result.records_merged = 200  # type: ignore


# ──────────────────────────────────────────────────────────────────────────────
# result_composite.py Tests
# ──────────────────────────────────────────────────────────────────────────────


class TestCompositeResult:
    """Tests for CompositeResult dataclass."""

    def test_create_composite_result_minimal(self, seed_result):
        """Create CompositeResult with minimal required fields."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
        )

        assert result.composite_name == "test_composite"
        assert result.composite_run_id == "run-123"
        assert result.seed_result == seed_result
        assert result.dependency_results == {}
        assert result.enrichment_results == {}

    def test_create_composite_result_full(self, seed_result, merge_result):
        """Create CompositeResult with all fields."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            dependency_results={
                "dep1": DependencyResult(
                    pipeline_name="dep1",
                    status=DependencyStatus.SUCCESS,
                    records_silver=50,
                )
            },
            merge_result=merge_result,
            total_duration_seconds=100.0,
            started_at=datetime(2024, 1, 1, tzinfo=UTC),
            completed_at=datetime(2024, 1, 1, 0, 1, 40, tzinfo=UTC),
            _required_dependencies=frozenset(["dep1"]),
        )

        assert result.dependency_results == {
            "dep1": DependencyResult(
                pipeline_name="dep1", status=DependencyStatus.SUCCESS, records_silver=50
            )
        }
        assert result.total_duration_seconds == 100.0

    def test_is_success_true_when_all_conditions_met(self, seed_result, merge_result):
        """is_success should return True when all conditions are met."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            merge_result=merge_result,
        )

        assert result.is_success

    def test_is_success_false_when_seed_failed(self):
        """is_success should return False when seed failed."""
        failed_seed = SeedResult(
            pipeline_name="seed_pipeline",
            records_silver=0,
        )
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=failed_seed,
            merge_result=MergeResult(records_merged=100),
        )

        assert not result.is_success

    def test_is_success_false_when_no_merge_result(self, seed_result):
        """is_success should return False when merge_result is None."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            merge_result=None,
        )

        assert not result.is_success

    def test_is_success_false_when_no_records_merged(self, seed_result):
        """is_success should return False when no records merged."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            merge_result=MergeResult(records_merged=0),
        )

        assert not result.is_success

    def test_required_dependencies_succeeded_true(self, seed_result):
        """required_dependencies_succeeded should return True when all required dependencies succeeded."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            dependency_results={
                "dep1": DependencyResult(
                    pipeline_name="dep1",
                    status=DependencyStatus.SUCCESS,
                    records_silver=50,
                ),
            },
            _required_dependencies=frozenset(["dep1"]),
        )

        assert result.required_dependencies_succeeded

    def test_required_dependencies_succeeded_false_when_missing(self, seed_result):
        """required_dependencies_succeeded should return False when required dependency is missing."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            dependency_results={},
            _required_dependencies=frozenset(["dep1"]),
        )

        assert not result.required_dependencies_succeeded

    def test_required_dependencies_succeeded_false_when_failed(self, seed_result):
        """required_dependencies_succeeded should return False when required dependency failed."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            dependency_results={
                "dep1": DependencyResult(
                    pipeline_name="dep1",
                    status=DependencyStatus.FAILED,
                    records_silver=0,
                ),
            },
            _required_dependencies=frozenset(["dep1"]),
        )

        assert not result.required_dependencies_succeeded

    def test_required_enrichers_succeeded_true(self, seed_result):
        """required_enrichers_succeeded should return True when all required enrichers succeeded."""
        from bioetl.domain.composite.result_enrichment import (
            EnrichmentResult,
            EnrichmentStatus,
        )

        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            enrichment_results={
                "enr1": EnrichmentResult(
                    enricher_name="enr1",
                    status=EnrichmentStatus.SUCCESS,
                    records_enriched=50,
                ),
            },
            _required_enrichers=frozenset(["enr1"]),
        )

        assert result.required_enrichers_succeeded

    def test_required_enrichers_succeeded_false_when_missing(self, seed_result):
        """required_enrichers_succeeded should return False when required enricher is missing."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            enrichment_results={},
            _required_enrichers=frozenset(["enr1"]),
        )

        assert not result.required_enrichers_succeeded

    def test_successful_dependencies(self, seed_result):
        """successful_dependencies should return list of successful dependencies."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            dependency_results={
                "dep1": DependencyResult(
                    pipeline_name="dep1",
                    status=DependencyStatus.SUCCESS,
                    records_silver=50,
                ),
                "dep2": DependencyResult(
                    pipeline_name="dep2",
                    status=DependencyStatus.FAILED,
                    records_silver=0,
                ),
            },
        )

        assert result.successful_dependencies == ["dep1"]

    def test_failed_dependencies(self, seed_result):
        """failed_dependencies should return list of failed dependencies."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            dependency_results={
                "dep1": DependencyResult(
                    pipeline_name="dep1",
                    status=DependencyStatus.SUCCESS,
                    records_silver=50,
                ),
                "dep2": DependencyResult(
                    pipeline_name="dep2",
                    status=DependencyStatus.FAILED,
                    records_silver=0,
                ),
            },
        )

        assert result.failed_dependencies == ["dep2"]

    def test_merge_lineage_successful_enrichers(self, seed_result):
        """successful_enrichers should return list of successful enrichers."""
        from bioetl.domain.composite.result_enrichment import (
            EnrichmentResult,
            EnrichmentStatus,
        )

        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            enrichment_results={
                "enr1": EnrichmentResult(
                    enricher_name="enr1",
                    status=EnrichmentStatus.SUCCESS,
                    records_enriched=50,
                ),
                "enr2": EnrichmentResult(
                    enricher_name="enr2",
                    status=EnrichmentStatus.FAILED,
                    records_enriched=0,
                ),
            },
        )

        assert result.successful_enrichers == ["enr1"]

    def test_merge_lineage_failed_enrichers(self, seed_result):
        """failed_enrichers should return list of failed enrichers."""
        from bioetl.domain.composite.result_enrichment import (
            EnrichmentResult,
            EnrichmentStatus,
        )

        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            enrichment_results={
                "enr1": EnrichmentResult(
                    enricher_name="enr1",
                    status=EnrichmentStatus.SUCCESS,
                    records_enriched=50,
                ),
                "enr2": EnrichmentResult(
                    enricher_name="enr2",
                    status=EnrichmentStatus.FAILED,
                    records_enriched=0,
                ),
            },
        )

        assert result.failed_enrichers == ["enr2"]

    def test_merge_lineage_skipped_enrichers(self, seed_result):
        """skipped_enrichers should return list of skipped enrichers."""
        from bioetl.domain.composite.result_enrichment import (
            EnrichmentResult,
            EnrichmentStatus,
        )

        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            enrichment_results={
                "enr1": EnrichmentResult(
                    enricher_name="enr1",
                    status=EnrichmentStatus.SUCCESS,
                    records_enriched=50,
                ),
                "enr2": EnrichmentResult(
                    enricher_name="enr2",
                    status=EnrichmentStatus.SKIPPED,
                    records_enriched=0,
                ),
            },
        )

        assert result.skipped_enrichers == ["enr2"]

    def test_merge_lineage_not_run_enrichers(self, seed_result):
        """not_run_enrichers should return list of not-run enrichers."""
        from bioetl.domain.composite.result_enrichment import (
            EnrichmentResult,
            EnrichmentStatus,
        )

        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            enrichment_results={
                "enr1": EnrichmentResult(
                    enricher_name="enr1",
                    status=EnrichmentStatus.SUCCESS,
                    records_enriched=50,
                ),
                "enr2": EnrichmentResult(
                    enricher_name="enr2",
                    status=EnrichmentStatus.NOT_RUN,
                    records_enriched=0,
                ),
            },
        )

        assert result.not_run_enrichers == ["enr2"]

    def test_merge_lineage_optional_failed_enrichers(self, seed_result):
        """optional_failed_enrichers should return list of failed optional enrichers."""
        from bioetl.domain.composite.result_enrichment import (
            EnrichmentResult,
            EnrichmentStatus,
        )

        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            enrichment_results={
                "enr1": EnrichmentResult(
                    enricher_name="enr1",
                    status=EnrichmentStatus.FAILED,
                    records_enriched=0,
                ),
                "enr2": EnrichmentResult(
                    enricher_name="enr2",
                    status=EnrichmentStatus.FAILED,
                    records_enriched=0,
                ),
            },
            _required_enrichers=frozenset(["enr1"]),
        )

        assert result.optional_failed_enrichers == ["enr2"]

    def test_total_records_enriched(self, seed_result):
        """total_records_enriched should sum records across all enrichers."""
        from bioetl.domain.composite.result_enrichment import (
            EnrichmentResult,
            EnrichmentStatus,
        )

        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            enrichment_results={
                "enr1": EnrichmentResult(
                    enricher_name="enr1",
                    status=EnrichmentStatus.SUCCESS,
                    records_enriched=50,
                ),
                "enr2": EnrichmentResult(
                    enricher_name="enr2",
                    status=EnrichmentStatus.SUCCESS,
                    records_enriched=30,
                ),
            },
        )

        assert result.total_records_enriched == 80

    def test_summary_generates_correct_dict(self, seed_result, merge_result):
        """summary should generate correct summary dictionary."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            merge_result=merge_result,
            had_warnings=True,
        )

        summary = result.summary()

        assert summary["composite_name"] == "test_composite"
        assert summary["composite_run_id"] == "run-123"
        assert summary["is_success"] is True
        assert summary["had_warnings"] is True
        assert summary["seed_records"] == 100
        assert summary["records_merged"] == 100

    def test_summary_includes_original_run_id(self, seed_result):
        """summary should include original_run_id when set."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
            original_run_id="original-run-456",
        )

        summary = result.summary()

        assert summary["original_run_id"] == "original-run-456"

    def test_composite_result_is_frozen(self, seed_result):
        """CompositeResult should be frozen (immutable)."""
        result = CompositeResult(
            composite_name="test_composite",
            composite_run_id="run-123",
            seed_result=seed_result,
        )

        with pytest.raises(AttributeError):
            result.composite_name = "new_name"  # type: ignore
