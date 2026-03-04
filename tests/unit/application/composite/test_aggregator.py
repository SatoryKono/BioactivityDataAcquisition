"""Unit tests for EnricherAggregatorService."""

from __future__ import annotations

from unittest.mock import MagicMock

import polars as pl
import pytest

from bioetl.application.composite.aggregator import EnricherAggregatorService
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
)


@pytest.fixture
def mock_logger():
    """Create a mock LoggerPort."""
    return MagicMock()


@pytest.fixture
def aggregator(mock_logger):
    """Create an EnricherAggregatorService instance."""
    return EnricherAggregatorService(mock_logger)


# ---------------------------------------------------------------------------
# aggregate() tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAggregateCollectList:
    """Tests for COLLECT_LIST aggregation."""

    def test_collect_list_basic(self, aggregator: EnricherAggregatorService):
        """Test COLLECT_LIST collects all non-null values into a list."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D2"],
                "term": ["cancer", "oncology", "diabetes"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert len(result) == 2
        d1_row = result.filter(pl.col("doc_id") == "D1")
        terms = d1_row["term"].to_list()[0]
        assert sorted(terms) == ["cancer", "oncology"]

    def test_collect_list_drops_nulls(self, aggregator: EnricherAggregatorService):
        """Test COLLECT_LIST drops null values."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1"],
                "term": ["cancer", None, "oncology"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        terms = result["term"].to_list()[0]
        assert len(terms) == 2
        assert None not in terms


@pytest.mark.unit
class TestAggregateCollectSet:
    """Tests for COLLECT_SET aggregation."""

    def test_collect_set_deduplicates(self, aggregator: EnricherAggregatorService):
        """Test COLLECT_SET returns unique values only."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1"],
                "term": ["cancer", "cancer", "oncology"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_SET,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        terms = result["term"].to_list()[0]
        assert sorted(terms) == ["cancer", "oncology"]


@pytest.mark.unit
class TestAggregateCount:
    """Tests for COUNT aggregation."""

    def test_count_basic(self, aggregator: EnricherAggregatorService):
        """Test COUNT returns number of rows per group."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1", "D2"],
                "term": ["a", "b", "c", "d"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COUNT,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        d1 = result.filter(pl.col("doc_id") == "D1")["term"].to_list()[0]
        d2 = result.filter(pl.col("doc_id") == "D2")["term"].to_list()[0]
        assert d1 == 3
        assert d2 == 1


@pytest.mark.unit
class TestAggregateFirst:
    """Tests for FIRST aggregation."""

    def test_first_takes_first_value(self, aggregator: EnricherAggregatorService):
        """Test FIRST returns the first value per group."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1"],
                "term": ["first", "second"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.FIRST,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert result["term"].to_list()[0] == "first"


@pytest.mark.unit
class TestAggregateConcatStr:
    """Tests for CONCAT_STR aggregation."""

    def test_concat_str_joins_values(self, aggregator: EnricherAggregatorService):
        """Test CONCAT_STR joins values with comma separator."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1"],
                "term": ["cancer", "oncology", "tumor"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.CONCAT_STR,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        concatenated = result["term"].to_list()[0]
        assert "cancer" in concatenated
        assert "oncology" in concatenated
        assert ", " in concatenated

    def test_concat_str_drops_nulls(self, aggregator: EnricherAggregatorService):
        """Test CONCAT_STR drops null values before concatenation."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1"],
                "term": ["cancer", None, "tumor"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.CONCAT_STR,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        concatenated = result["term"].to_list()[0]
        assert "None" not in concatenated


# ---------------------------------------------------------------------------
# Output field aliasing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestOutputFieldAlias:
    """Tests for output_field aliasing in aggregation."""

    def test_output_field_renames_column(self, aggregator: EnricherAggregatorService):
        """Test that output_field renames the result column."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1"],
                "term": ["cancer", "oncology"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    output_field="mesh_terms",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert "mesh_terms" in result.columns
        assert "term" not in result.columns

    def test_default_output_field_uses_source(
        self, aggregator: EnricherAggregatorService
    ):
        """Test that omitting output_field keeps the source field name."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1"],
                "term": ["cancer"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.FIRST,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert "term" in result.columns


# ---------------------------------------------------------------------------
# Filter condition tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterCondition:
    """Tests for filter_condition in aggregation fields."""

    def test_filter_is_not_null(self, aggregator: EnricherAggregatorService):
        """Test IS NOT NULL filter condition."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1"],
                "term_type": ["MESH", None, "MESH"],
                "term": ["cancer", "unknown", "tumor"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    filter_condition="term_type IS NOT NULL",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        terms = result["term"].to_list()[0]
        assert len(terms) == 2

    def test_filter_is_null(self, aggregator: EnricherAggregatorService):
        """Test IS NULL filter condition."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1"],
                "term_type": ["MESH", None, "MESH"],
                "term": ["cancer", "unknown", "tumor"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    filter_condition="term_type IS NULL",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        terms = result["term"].to_list()[0]
        assert len(terms) == 1

    def test_filter_equality(self, aggregator: EnricherAggregatorService):
        """Test == equality filter condition."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1"],
                "term_type": ["MESH", "KEYWORD", "MESH"],
                "term": ["cancer", "chemo", "tumor"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    filter_condition="term_type == 'MESH'",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        terms = result["term"].to_list()[0]
        assert sorted(terms) == ["cancer", "tumor"]

    def test_filter_inequality(self, aggregator: EnricherAggregatorService):
        """Test != inequality filter condition."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D1"],
                "term_type": ["MESH", "KEYWORD", "MESH"],
                "term": ["cancer", "chemo", "tumor"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                    filter_condition="term_type != 'MESH'",
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        terms = result["term"].to_list()[0]
        assert terms == ["chemo"]

    def test_invalid_filter_returns_unfiltered(
        self, aggregator: EnricherAggregatorService, mock_logger: MagicMock
    ):
        """Test that an unparseable filter condition returns None (no filter)."""
        result = aggregator._parse_filter_condition("bad filter!")

        assert result is None
        mock_logger.warning.assert_called_once()


# ---------------------------------------------------------------------------
# Multiple fields aggregation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMultipleFields:
    """Tests for aggregating multiple fields simultaneously."""

    def test_multiple_fields_in_single_config(
        self, aggregator: EnricherAggregatorService
    ):
        """Test aggregation with multiple field specs in one config."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D2"],
                "term": ["cancer", "oncology", "diabetes"],
                "score": [0.9, 0.8, 0.7],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                ),
                AggregationFieldSpec(
                    source_field="score",
                    agg_function=AggregationFunction.FIRST,
                ),
            ),
        )

        result = aggregator.aggregate(df, config, "test_enricher")

        assert len(result) == 2
        assert "term" in result.columns
        assert "score" in result.columns


# ---------------------------------------------------------------------------
# Logging tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAggregatorLogging:
    """Tests for logging behavior."""

    def test_aggregate_logs_debug_and_info(
        self, aggregator: EnricherAggregatorService, mock_logger: MagicMock
    ):
        """Test that aggregate() logs debug before and info after."""
        df = pl.DataFrame({"doc_id": ["D1"], "term": ["cancer"]})
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.FIRST,
                ),
            ),
        )

        aggregator.aggregate(df, config, "my_enricher")

        mock_logger.debug.assert_called_once()
        mock_logger.info.assert_called_once()

        # Verify enricher name is passed to logs
        debug_kwargs = mock_logger.debug.call_args
        assert debug_kwargs[1]["enricher"] == "my_enricher"

    def test_aggregate_logs_row_counts(
        self, aggregator: EnricherAggregatorService, mock_logger: MagicMock
    ):
        """Test that info log contains rows_before and rows_after."""
        df = pl.DataFrame(
            {
                "doc_id": ["D1", "D1", "D2"],
                "term": ["a", "b", "c"],
            }
        )
        config = AggregationConfig(
            group_by="doc_id",
            fields=(
                AggregationFieldSpec(
                    source_field="term",
                    agg_function=AggregationFunction.COLLECT_LIST,
                ),
            ),
        )

        aggregator.aggregate(df, config, "test")

        info_kwargs = mock_logger.info.call_args[1]
        assert info_kwargs["rows_before"] == 3
        assert info_kwargs["rows_after"] == 2
