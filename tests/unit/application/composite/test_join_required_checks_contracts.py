"""Unit tests for the composite join coverage and cardinality guards.

``reject_required_coverage`` and ``reject_join_cardinality`` are the only
guards that fail a composite join closed before the merge continues. Neither
had a direct test, so the guards could silently stop protecting seed height
and key coverage.
"""

from __future__ import annotations

import polars as pl
import pytest

from bioetl.application.composite.helpers.join_required_checks import (
    JoinCardinalityError,
    RequiredJoinKeyError,
    reject_join_cardinality,
    reject_required_coverage,
)


@pytest.mark.unit
class TestRejectRequiredCoverage:
    """A required inner join must not lose seed rows."""

    def test_reject_required_coverage__unmatched_seed_key__raises_required_join_error(
        self,
    ) -> None:
        left = pl.DataFrame({"id": ["a", "b"]})
        right = pl.DataFrame({"rid": ["a"]})

        with pytest.raises(RequiredJoinKeyError, match="unmatched seed rows"):
            reject_required_coverage(
                required=True,
                effective_how="inner",
                pipeline_name="pubmed_publication",
                left_df=left,
                right_df=right,
                left_on="id",
                right_on="rid",
            )

    def test_reject_required_coverage__duplicate_right_rows_mask_missing_seed_key__raises(
        self,
    ) -> None:
        left = pl.DataFrame({"id": ["a", "b", "c"]})
        right = pl.DataFrame({"rid": ["a", "a", "c"]})

        with pytest.raises(RequiredJoinKeyError, match="unmatched seed rows"):
            reject_required_coverage(
                required=True,
                effective_how="inner",
                pipeline_name="pubmed_publication",
                left_df=left,
                right_df=right,
                left_on="id",
                right_on="rid",
            )

    def test_reject_required_coverage__fully_matched_seed_keys__returns_none(
        self,
    ) -> None:
        left = pl.DataFrame({"id": ["a", "b"]})
        right = pl.DataFrame({"rid": ["a", "b"]})

        result = reject_required_coverage(
            required=True,
            effective_how="inner",
            pipeline_name="pubmed_publication",
            left_df=left,
            right_df=right,
            left_on="id",
            right_on="rid",
        )

        assert result is None

    def test_reject_required_coverage__optional_join_with_unmatched_keys__returns_none(
        self,
    ) -> None:
        left = pl.DataFrame({"id": ["a", "b"]})
        right = pl.DataFrame({"rid": ["a"]})

        result = reject_required_coverage(
            required=False,
            effective_how="inner",
            pipeline_name="pubmed_publication",
            left_df=left,
            right_df=right,
            left_on="id",
            right_on="rid",
        )

        assert result is None

    def test_reject_required_coverage__required_left_join__returns_none(
        self,
    ) -> None:
        left = pl.DataFrame({"id": ["a", "b"]})
        right = pl.DataFrame({"rid": ["a"]})

        result = reject_required_coverage(
            required=True,
            effective_how="left",
            pipeline_name="pubmed_publication",
            left_df=left,
            right_df=right,
            left_on="id",
            right_on="rid",
        )

        assert result is None


@pytest.mark.unit
class TestRejectJoinCardinality:
    """A join must not silently change the seed row count."""

    def test_reject_join_cardinality__unchanged_seed_height__returns_none(
        self,
    ) -> None:
        result = reject_join_cardinality(
            required=False,
            join_how=None,
            resolved_how="inner",
            pipeline_name="pubmed_publication",
            left_height=3,
            result_height=3,
        )

        assert result is None

    def test_reject_join_cardinality__required_join_without_explicit_type__raises_required_join_error(
        self,
    ) -> None:
        with pytest.raises(RequiredJoinKeyError, match="changed cardinality"):
            reject_join_cardinality(
                required=True,
                join_how=None,
                resolved_how="inner",
                pipeline_name="pubmed_publication",
                left_height=3,
                result_height=5,
            )

    def test_reject_join_cardinality__optional_left_join_growing_seed_height__raises_cardinality_error(
        self,
    ) -> None:
        with pytest.raises(JoinCardinalityError, match="changed cardinality"):
            reject_join_cardinality(
                required=False,
                join_how="left",
                resolved_how="left",
                pipeline_name="pubmed_publication",
                left_height=3,
                result_height=5,
            )

    def test_reject_join_cardinality__required_left_join_growing_seed_height__raises_cardinality_error(
        self,
    ) -> None:
        with pytest.raises(JoinCardinalityError, match="changed cardinality"):
            reject_join_cardinality(
                required=True,
                join_how="left",
                resolved_how="left",
                pipeline_name="pubmed_publication",
                left_height=3,
                result_height=5,
            )
