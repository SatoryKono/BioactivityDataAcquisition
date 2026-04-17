"""Unit tests for composite pipeline configuration models.

Tests for CompositeConfig, EnricherConfig, SeedConfig, MergeConfig,
AggregationConfig, AggregationFieldSpec, EnricherCardinality.
"""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
    CompositeDQConfig,
    CompositeConfig,
    DQOverrideConfig,
    EnricherCardinality,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import (
    ConflictResolution,
    FallbackStrategy,
    MergeStrategy,
)


class TestSeedConfig:
    """Tests for SeedConfig."""

    def test_valid_seed_config(self):
        """Valid seed config should be created successfully."""
        config = SeedConfig(
            pipeline="chembl_publication",
            output_keys=("document_id", "doi", "pmid"),
            silver_table="silver/chembl/publication",
        )
        assert config.pipeline == "chembl_publication"
        assert config.output_keys == ("document_id", "doi", "pmid")
        assert config.silver_table == "silver/chembl/publication"
        assert config.limit is None

    def test_seed_config_with_limit(self):
        """Seed config with limit should work."""
        config = SeedConfig(
            pipeline="chembl_publication",
            output_keys=("doi",),
            silver_table="silver/chembl/publication",
            limit=100,
        )
        assert config.limit == 100

    def test_seed_config_converts_list_to_tuple(self):
        """Lists should be converted to tuples for immutability."""
        config = SeedConfig(
            pipeline="chembl_publication",
            output_keys=["doi", "pmid"],  # type: ignore
            silver_table="silver/chembl/publication",
        )
        assert isinstance(config.output_keys, tuple)
        assert config.output_keys == ("doi", "pmid")

    def test_seed_config_empty_pipeline_raises(self):
        """Empty pipeline name should raise ValueError."""
        with pytest.raises(ValueError, match="pipeline name cannot be empty"):
            SeedConfig(
                pipeline="",
                output_keys=("doi",),
                silver_table="silver/chembl/publication",
            )

    def test_seed_config_empty_output_keys_raises(self):
        """Empty output_keys should raise ValueError."""
        with pytest.raises(ValueError, match="output_keys cannot be empty"):
            SeedConfig(
                pipeline="chembl_publication",
                output_keys=(),
                silver_table="silver/chembl/publication",
            )

    def test_seed_config_invalid_limit_raises(self):
        """Non-positive limit should raise ValueError."""
        with pytest.raises(ValueError, match="limit must be positive"):
            SeedConfig(
                pipeline="chembl_publication",
                output_keys=("doi",),
                silver_table="silver/chembl/publication",
                limit=0,
            )


class TestEnricherConfig:
    """Tests for EnricherConfig."""

    def test_valid_enricher_config(self):
        """Valid enricher config should be created successfully."""
        config = EnricherConfig(
            pipeline="crossref_publication",
            join_keys=("doi",),
            required=True,
            timeout_seconds=600,
        )
        assert config.pipeline == "crossref_publication"
        assert config.join_keys == ("doi",)
        assert config.required is True
        assert config.timeout_seconds == 600
        assert config.fallback_strategy == FallbackStrategy.SKIP

    def test_enricher_config_with_fallback_keys(self):
        """Enricher with multiple join keys should work."""
        config = EnricherConfig(
            pipeline="openalex_publication",
            join_keys=("doi", "pmid"),
            required=False,
        )
        assert config.join_keys == ("doi", "pmid")
        assert config.primary_join_key == "doi"
        assert config.has_fallback_keys is True

    def test_enricher_config_single_key_no_fallback(self):
        """Enricher with single key should have no fallback."""
        config = EnricherConfig(
            pipeline="pubmed_publication",
            join_keys=("pmid",),
        )
        assert config.has_fallback_keys is False

    def test_enricher_config_filter_condition(self):
        """Enricher with filter condition should store it."""
        config = EnricherConfig(
            pipeline="pubmed_publication",
            join_keys=("pmid",),
            filter_condition="pmid IS NOT NULL",
        )
        assert config.filter_condition == "pmid IS NOT NULL"

    def test_enricher_config_string_fallback_strategy(self):
        """String fallback strategy should be converted to enum."""
        config = EnricherConfig(
            pipeline="test",
            join_keys=("id",),
            fallback_strategy="use_cached",  # type: ignore
        )
        assert config.fallback_strategy == FallbackStrategy.USE_CACHED

    def test_enricher_config_empty_pipeline_raises(self):
        """Empty pipeline should raise ValueError."""
        with pytest.raises(ValueError, match="pipeline name cannot be empty"):
            EnricherConfig(
                pipeline="",
                join_keys=("doi",),
            )

    def test_enricher_config_empty_join_keys_raises(self):
        """Empty join_keys should raise ValueError."""
        with pytest.raises(ValueError, match="join_keys cannot be empty"):
            EnricherConfig(
                pipeline="crossref",
                join_keys=(),
            )

    def test_enricher_config_many_to_one_requires_aggregation(self):
        """MANY_TO_ONE cardinality requires aggregation config."""
        with pytest.raises(ValueError, match="requires aggregation"):
            EnricherConfig(
                pipeline="test",
                join_keys=("id",),
                cardinality=EnricherCardinality.MANY_TO_ONE,
                aggregation=None,
            )

    def test_enricher_config_many_to_one_with_aggregation(self):
        """MANY_TO_ONE cardinality with aggregation should work."""
        config = EnricherConfig(
            pipeline="chembl_publication_term",
            join_keys=("publication_id",),
            cardinality=EnricherCardinality.MANY_TO_ONE,
            aggregation=AggregationConfig(
                group_by="publication_id",
                fields=(
                    AggregationFieldSpec(
                        source_field="term",
                        agg_function=AggregationFunction.COLLECT_LIST,
                        output_field="terms",
                    ),
                ),
            ),
        )
        assert config.cardinality == EnricherCardinality.MANY_TO_ONE
        assert config.aggregation is not None
        assert config.is_many_to_one is True

    def test_enricher_config_one_to_one_no_aggregation_ok(self):
        """ONE_TO_ONE cardinality without aggregation should work."""
        config = EnricherConfig(
            pipeline="test",
            join_keys=("id",),
            cardinality=EnricherCardinality.ONE_TO_ONE,
        )
        assert config.cardinality == EnricherCardinality.ONE_TO_ONE
        assert config.aggregation is None
        assert config.is_many_to_one is False

    def test_enricher_config_string_cardinality_converted(self):
        """String cardinality should be converted to enum."""
        config = EnricherConfig(
            pipeline="test",
            join_keys=("id",),
            cardinality="one_to_one",  # type: ignore
        )
        assert config.cardinality == EnricherCardinality.ONE_TO_ONE

    def test_enricher_config_dict_aggregation_converted(self):
        """Dict aggregation should be converted to AggregationConfig."""
        config = EnricherConfig(
            pipeline="test",
            join_keys=("id",),
            cardinality=EnricherCardinality.MANY_TO_ONE,
            aggregation={  # type: ignore
                "group_by": "id",
                "fields": [
                    {
                        "source_field": "val",
                        "agg_function": "collect_list",
                        "output_field": "values",
                    }
                ],
            },
        )
        assert isinstance(config.aggregation, AggregationConfig)
        assert config.aggregation.group_by == "id"


class TestAggregationFunction:
    """Tests for AggregationFunction enum."""

    def test_from_string_valid(self):
        """Valid string should convert to enum."""
        assert (
            AggregationFunction.from_string("collect_list")
            == AggregationFunction.COLLECT_LIST
        )
        assert (
            AggregationFunction.from_string("COLLECT_SET")
            == AggregationFunction.COLLECT_SET
        )
        assert AggregationFunction.from_string("count") == AggregationFunction.COUNT
        assert AggregationFunction.from_string("first") == AggregationFunction.FIRST
        assert (
            AggregationFunction.from_string("concat_str")
            == AggregationFunction.CONCAT_STR
        )

    def test_from_string_invalid_raises(self):
        """Invalid string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid aggregation function"):
            AggregationFunction.from_string("invalid")


class TestEnricherCardinality:
    """Tests for EnricherCardinality enum."""

    def test_from_string_valid(self):
        """Valid string should convert to enum."""
        assert (
            EnricherCardinality.from_string("one_to_one")
            == EnricherCardinality.ONE_TO_ONE
        )
        assert (
            EnricherCardinality.from_string("MANY_TO_ONE")
            == EnricherCardinality.MANY_TO_ONE
        )

    def test_from_string_invalid_raises(self):
        """Invalid string should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid cardinality"):
            EnricherCardinality.from_string("invalid")


class TestAggregationFieldSpec:
    """Tests for AggregationFieldSpec."""

    def test_valid_field_spec(self):
        """Valid field spec should be created successfully."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
            filter_condition="term_type == 'MESH_HEADING'",
            output_field="mesh_headings",
        )
        assert spec.source_field == "term"
        assert spec.agg_function == AggregationFunction.COLLECT_LIST
        assert spec.filter_condition == "term_type == 'MESH_HEADING'"
        assert spec.output_field == "mesh_headings"
        assert spec.effective_output_field == "mesh_headings"

    def test_field_spec_defaults_output_to_source(self):
        """Output field defaults to source field if not specified."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function=AggregationFunction.COLLECT_LIST,
        )
        assert spec.output_field is None
        assert spec.effective_output_field == "term"

    def test_field_spec_string_agg_function_converted(self):
        """String agg_function should be converted to enum."""
        spec = AggregationFieldSpec(
            source_field="term",
            agg_function="collect_set",  # type: ignore
        )
        assert spec.agg_function == AggregationFunction.COLLECT_SET

    def test_field_spec_empty_source_raises(self):
        """Empty source_field should raise ValueError."""
        with pytest.raises(ValueError, match="source_field cannot be empty"):
            AggregationFieldSpec(
                source_field="",
                agg_function=AggregationFunction.COLLECT_LIST,
            )


class TestAggregationConfig:
    """Tests for AggregationConfig."""

    def test_valid_config(self):
        """Valid aggregation config should be created successfully."""
        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    filter_condition="term_type == 'MESH_HEADING'",
                    output_field="mesh_headings",
                ),
                AggregationFieldSpec(
                    source_field="mesh_id",
                    agg_function=AggregationFunction.COLLECT_SET,
                    output_field="mesh_ids",
                ),
            ),
        )
        assert config.group_by == "publication_id"
        assert len(config.fields) == 2

    def test_empty_fields_raises(self):
        """Empty fields should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AggregationConfig(group_by="id", fields=())

    def test_empty_group_by_raises(self):
        """Empty group_by should raise ValueError."""
        with pytest.raises(ValueError, match="group_by cannot be empty"):
            AggregationConfig(
                group_by="",
                fields=(
                    AggregationFieldSpec(
                        source_field="val",
                        agg_function=AggregationFunction.COLLECT_LIST,
                    ),
                ),
            )

    def test_list_to_tuple_conversion(self):
        """List of fields should be converted to tuple."""
        config = AggregationConfig(
            group_by="id",
            fields=[  # type: ignore
                AggregationFieldSpec(
                    source_field="val",
                    agg_function=AggregationFunction.COLLECT_LIST,
                ),
            ],
        )
        assert isinstance(config.fields, tuple)

    def test_dict_fields_converted(self):
        """Dict fields should be converted to AggregationFieldSpec."""
        config = AggregationConfig(
            group_by="id",
            fields=[  # type: ignore
                {
                    "source_field": "val",
                    "agg_function": "collect_list",
                    "output_field": "values",
                }
            ],
        )
        assert isinstance(config.fields[0], AggregationFieldSpec)
        assert config.fields[0].source_field == "val"


class TestMergeConfig:
    """Tests for MergeConfig."""

    def test_valid_merge_config(self):
        """Valid merge config should be created successfully."""
        config = MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="silver/composite/publication",
            output_gold_path="gold/publication_enriched",
        )
        assert config.strategy == MergeStrategy.LEFT_OUTER
        assert config.conflict_resolution == ConflictResolution.SEED_PRIORITY
        assert config.output_silver_path == "silver/composite/publication"
        assert config.output_gold_path == "gold/publication_enriched"

    def test_merge_config_string_strategy(self):
        """String strategy should be converted to enum."""
        config = MergeConfig(
            strategy="inner",  # type: ignore
            conflict_resolution="coalesce",  # type: ignore
            output_silver_path="silver/test",
            output_gold_path="gold/test",
        )
        assert config.strategy == MergeStrategy.INNER
        assert config.conflict_resolution == ConflictResolution.COALESCE

    def test_merge_config_with_field_priorities(self):
        """Merge config with field priorities should work."""
        config = MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.EXPLICIT_RULES,
            output_silver_path="silver/test",
            output_gold_path="gold/test",
            field_priorities={
                "title": ("chembl", "crossref"),
                "abstract": ("pubmed", "openalex"),
            },
        )
        assert config.get_field_priority("title") == ("chembl", "crossref")
        assert config.get_field_priority("nonexistent") is None

    def test_merge_config_explicit_rules_requires_priorities(self):
        """EXPLICIT_RULES without field_priorities should raise."""
        with pytest.raises(ValueError, match="field_priorities required"):
            MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.EXPLICIT_RULES,
                output_silver_path="silver/test",
                output_gold_path="gold/test",
            )


class TestCompositeDQConfig:
    """Tests for CompositeDQConfig."""

    def test_valid_dq_config(self):
        """Valid DQ config should be created successfully."""
        config = CompositeDQConfig(
            soft_fail_threshold=0.10,
            hard_fail_threshold=0.30,
        )
        assert config.soft_fail_threshold == pytest.approx(0.10)
        assert config.hard_fail_threshold == pytest.approx(0.30)

    def test_dq_config_with_overrides(self):
        """DQ config with enricher overrides should work."""
        config = CompositeDQConfig(
            soft_fail_threshold=0.10,
            hard_fail_threshold=0.30,
            enricher_overrides={
                "semanticscholar": DQOverrideConfig(
                    soft_fail_threshold=0.20,
                    hard_fail_threshold=0.50,
                ),
            },
        )
        assert config.get_enricher_soft_threshold("semanticscholar") == pytest.approx(0.20)
        assert config.get_enricher_hard_threshold("semanticscholar") == pytest.approx(0.50)
        # Non-overridden enrichers use defaults
        assert config.get_enricher_soft_threshold("crossref") == pytest.approx(0.10)
        assert config.get_enricher_hard_threshold("crossref") == pytest.approx(0.30)

    def test_dq_config_invalid_thresholds(self):
        """Invalid threshold order should raise ValueError."""
        with pytest.raises(ValueError, match="soft_fail_threshold must be less than"):
            CompositeDQConfig(
                soft_fail_threshold=0.50,
                hard_fail_threshold=0.30,
            )


class TestCompositeConfig:
    """Tests for CompositeConfig."""

    @pytest.fixture
    def valid_composite_config(self):
        """Create a valid composite config for testing."""
        return CompositeConfig(
            name="composite_publication",
            version="1.0.0",
            seed=SeedConfig(
                pipeline="chembl_publication",
                output_keys=("document_id", "doi", "pmid"),
                silver_table="silver/chembl/publication",
            ),
            enrichers=(
                EnricherConfig(
                    pipeline="crossref_publication",
                    join_keys=("doi",),
                    required=True,
                ),
                EnricherConfig(
                    pipeline="pubmed_publication",
                    join_keys=("pmid",),
                    required=False,
                ),
            ),
            merge=MergeConfig(
                strategy=MergeStrategy.LEFT_OUTER,
                conflict_resolution=ConflictResolution.SEED_PRIORITY,
                output_silver_path="silver/composite/publication",
                output_gold_path="gold/publication_enriched",
            ),
        )

    def test_valid_composite_config(self, valid_composite_config):
        """Valid composite config should be created successfully."""
        config = valid_composite_config
        assert config.name == "composite_publication"
        assert config.version == "1.0.0"
        assert len(config.enrichers) == 2

    def test_composite_config_required_enrichers(self, valid_composite_config):
        """Required enrichers should be correctly identified."""
        config = valid_composite_config
        assert config.required_enrichers == ("crossref_publication",)
        assert config.optional_enrichers == ("pubmed_publication",)

    def test_composite_config_get_enricher(self, valid_composite_config):
        """get_enricher should return correct enricher config."""
        config = valid_composite_config
        enricher = config.get_enricher("crossref_publication")
        assert enricher is not None
        assert enricher.pipeline == "crossref_publication"
        assert enricher.required is True
        assert config.get_enricher("nonexistent") is None

    def test_composite_config_lock_key(self, valid_composite_config):
        """Lock key should be generated correctly."""
        config = valid_composite_config
        assert config.lock_key == "composite:composite_publication"

    def test_composite_config_validates_join_keys(self):
        """Join keys must exist in seed output_keys."""
        with pytest.raises(ValueError, match="join_key 'invalid' not found"):
            CompositeConfig(
                name="test",
                version="1.0.0",
                seed=SeedConfig(
                    pipeline="seed",
                    output_keys=("id", "doi"),
                    silver_table="silver/test",
                ),
                enrichers=(
                    EnricherConfig(
                        pipeline="enricher",
                        join_keys=("invalid",),  # Not in seed output_keys
                    ),
                ),
                merge=MergeConfig(
                    strategy=MergeStrategy.LEFT_OUTER,
                    conflict_resolution=ConflictResolution.SEED_PRIORITY,
                    output_silver_path="silver/test",
                    output_gold_path="gold/test",
                ),
            )

    def test_composite_config_validates_unique_enrichers(self):
        """Enricher pipeline names must be unique."""
        with pytest.raises(ValueError, match="Duplicate enricher pipelines"):
            CompositeConfig(
                name="test",
                version="1.0.0",
                seed=SeedConfig(
                    pipeline="seed",
                    output_keys=("id",),
                    silver_table="silver/test",
                ),
                enrichers=(
                    EnricherConfig(
                        pipeline="enricher",
                        join_keys=("id",),
                    ),
                    EnricherConfig(
                        pipeline="enricher",  # Duplicate
                        join_keys=("id",),
                    ),
                ),
                merge=MergeConfig(
                    strategy=MergeStrategy.LEFT_OUTER,
                    conflict_resolution=ConflictResolution.SEED_PRIORITY,
                    output_silver_path="silver/test",
                    output_gold_path="gold/test",
                ),
            )

    def test_composite_config_to_dict(self, valid_composite_config):
        """to_dict should serialize config correctly."""
        config = valid_composite_config
        data = config.to_dict()
        assert data["name"] == "composite_publication"
        assert data["version"] == "1.0.0"
        assert len(data["enrichers"]) == 2
