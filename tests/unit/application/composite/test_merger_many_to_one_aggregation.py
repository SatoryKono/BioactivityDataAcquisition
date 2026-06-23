"""Unit tests for MergeService MANY_TO_ONE aggregation behavior."""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config import EnricherConfig
from .test_merger import (
    aggregator,
    merge_config,
    merge_service,
    mock_logger,
    mock_storage,
)

# Re-export shared fixtures for pytest discovery in this module.
_FIXTURE_IMPORTS = (
    mock_logger,
    mock_storage,
    merge_config,
    aggregator,
    merge_service,
)


@pytest.mark.unit
class TestManyToOneAggregation:
    """Tests for 1:M enricher aggregation."""

    def test_aggregate_collect_list(self, aggregator):
        """Test COLLECT_LIST aggregation function."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
        )

        df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1", "CHEMBL2"],
                "term": ["Aspirin", "Pain", "Kinase"],
                "term_type": ["MESH_HEADING", "MESH_HEADING", "KEYWORD"],
            }
        )

        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    output_field="all_terms",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert len(result) == 2
        assert set(result["publication_id"].to_list()) == {"CHEMBL1", "CHEMBL2"}

        chembl1_terms = result.filter(pl.col("publication_id") == "CHEMBL1")[
            "all_terms"
        ][0]
        assert set(chembl1_terms) == {"Aspirin", "Pain"}

    def test_aggregate_collect_set(self, aggregator):
        """Test COLLECT_SET aggregation function (unique values)."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
        )

        df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1", "CHEMBL1"],
                "term": ["Aspirin", "Aspirin", "Pain"],  # Duplicate Aspirin
            }
        )

        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_SET,
                    output_field="unique_terms",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert len(result) == 1
        terms = result["unique_terms"][0]
        # Should have only unique values
        assert len(terms) == 2
        assert set(terms) == {"Aspirin", "Pain"}

    def test_aggregate_count(self, aggregator):
        """Test COUNT aggregation function."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
        )

        df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1", "CHEMBL1", "CHEMBL2"],
                "term": ["A", "B", "C", "D"],
            }
        )

        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COUNT,
                    output_field="term_count",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert len(result) == 2
        chembl1_count = result.filter(pl.col("publication_id") == "CHEMBL1")[
            "term_count"
        ][0]
        assert chembl1_count == 3

        chembl2_count = result.filter(pl.col("publication_id") == "CHEMBL2")[
            "term_count"
        ][0]
        assert chembl2_count == 1

    def test_aggregate_first(self, aggregator):
        """Test FIRST aggregation function."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
        )

        df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1", "CHEMBL1"],
                "term": ["First", "Second", "Third"],
            }
        )

        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.FIRST,
                    output_field="first_term",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert len(result) == 1
        assert result["first_term"][0] == "First"

    def test_aggregate_concat_str(self, aggregator):
        """Test CONCAT_STR aggregation function."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
        )

        df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1"],
                "term": ["Aspirin", "Pain"],
            }
        )

        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.CONCAT_STR,
                    output_field="terms_str",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert len(result) == 1
        assert result["terms_str"][0] == "Aspirin, Pain"

    def test_aggregate_with_filter(self, aggregator):
        """Test aggregation with filter condition."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
        )

        df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1", "CHEMBL1"],
                "term": ["Aspirin", "Pain", "Kinase"],
                "term_type": ["MESH_HEADING", "MESH_HEADING", "KEYWORD"],
            }
        )

        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    filter_condition="term_type == 'MESH_HEADING'",
                    output_field="mesh_terms",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        mesh_terms = result["mesh_terms"][0]
        assert set(mesh_terms) == {"Aspirin", "Pain"}
        assert "Kinase" not in mesh_terms

    def test_aggregate_multiple_fields(self, aggregator):
        """Test aggregation with multiple fields."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
        )

        df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1"],
                "term": ["Aspirin", "Pain"],
                "mesh_id": ["D001", "D002"],
            }
        )

        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    output_field="terms",
                ),
                AggregationFieldSpec(
                    source_field="mesh_id",
                    agg_function=AggregationFunction.COLLECT_SET,
                    output_field="mesh_ids",
                ),
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COUNT,
                    output_field="term_count",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert len(result) == 1
        assert set(result["terms"][0]) == {"Aspirin", "Pain"}
        assert set(result["mesh_ids"][0]) == {"D001", "D002"}
        assert result["term_count"][0] == 2

    def test_aggregate_with_null_values(self, aggregator):
        """Test aggregation handles null values correctly."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
        )

        df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1", "CHEMBL1"],
                "term": ["Aspirin", None, "Pain"],
            }
        )

        config = AggregationConfig(
            group_by="publication_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    output_field="terms",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        # Nulls should be dropped
        terms = result["terms"][0]
        assert len(terms) == 2
        assert set(terms) == {"Aspirin", "Pain"}

    def test_parse_filter_is_not_null(self, aggregator):
        """Test parsing IS NOT NULL filter condition."""
        import polars as pl

        expr = aggregator._parse_filter_condition("field IS NOT NULL")
        assert expr is not None

        # Test the expression works
        df = pl.DataFrame({"field": ["a", None, "b"]})
        result = df.filter(expr)
        assert len(result) == 2

    def test_parse_filter_is_null(self, aggregator):
        """Test parsing IS NULL filter condition."""
        import polars as pl

        expr = aggregator._parse_filter_condition("field IS NULL")
        assert expr is not None

        df = pl.DataFrame({"field": ["a", None, "b"]})
        result = df.filter(expr)
        assert len(result) == 1
        assert result["field"][0] is None

    def test_parse_filter_equality(self, aggregator):
        """Test parsing equality filter condition."""
        import polars as pl

        expr = aggregator._parse_filter_condition("term_type == 'MESH_HEADING'")
        assert expr is not None

        df = pl.DataFrame({"term_type": ["MESH_HEADING", "KEYWORD", "MESH_HEADING"]})
        result = df.filter(expr)
        assert len(result) == 2

    def test_parse_filter_inequality(self, aggregator):
        """Test parsing inequality filter condition."""
        import polars as pl

        expr = aggregator._parse_filter_condition("term_type != 'KEYWORD'")
        assert expr is not None

        df = pl.DataFrame({"term_type": ["MESH_HEADING", "KEYWORD", "MESH_QUALIFIER"]})
        result = df.filter(expr)
        assert len(result) == 2

    def test_parse_filter_invalid_returns_none(self, aggregator):
        """Test invalid filter returns None."""
        expr = aggregator._parse_filter_condition("some random text")
        assert expr is None

    @pytest.mark.asyncio
    async def test_apply_joins_with_many_to_one_enricher(self, merge_service):
        """Test _apply_joins aggregates MANY_TO_ONE enricher before join."""
        import polars as pl
        from bioetl.domain.composite.config import (
            AggregationConfig,
            AggregationFieldSpec,
            AggregationFunction,
            EnricherCardinality,
        )

        seed_df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL2"],
                "title": ["Study A", "Study B"],
            }
        )

        # Enricher has multiple rows per document
        enricher_df = pl.DataFrame(
            {
                "publication_id": ["CHEMBL1", "CHEMBL1", "CHEMBL1", "CHEMBL2"],
                "term": ["Aspirin", "Pain", "Drug", "Kinase"],
                "term_type": ["MESH_HEADING", "MESH_HEADING", "KEYWORD", "KEYWORD"],
            }
        )

        enricher_config = EnricherConfig(
            pipeline="chembl_publication_term",
            join_keys=("publication_id",),
            required=False,
            cardinality=EnricherCardinality.MANY_TO_ONE,
            aggregation=AggregationConfig(
                group_by="publication_id",
                fields=(
                    AggregationFieldSpec(
                        source_field="term",
                        agg_function=AggregationFunction.COLLECT_LIST,
                        filter_condition="term_type == 'MESH_HEADING'",
                        output_field="mesh_headings",
                    ),
                    AggregationFieldSpec(
                        source_field="term",
                        agg_function=AggregationFunction.COUNT,
                        output_field="term_count",
                    ),
                ),
            ),
        )

        result = await merge_service._join_planner.apply_joins(
            seed_df=seed_df,
            enricher_dfs={"chembl_publication_term": enricher_df},
            enrichers=[enricher_config],
            seed_pipeline="chembl_publication",
        )

        # Result should have 2 rows (no fan-out)
        assert len(result) == 2

        # Check aggregated values
        chembl1 = result.filter(pl.col("publication_id") == "CHEMBL1")
        # mesh_headings column should exist with qualified name
        mesh_col = next(c for c in result.columns if "mesh_headings" in c)
        mesh_terms = chembl1[mesh_col][0]
        assert set(mesh_terms) == {"Aspirin", "Pain"}

        # term_count should include all terms
        count_col = next(c for c in result.columns if "term_count" in c)
        assert chembl1[count_col][0] == 3  # Aspirin, Pain, Drug
