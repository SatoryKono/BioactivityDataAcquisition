"""Required-join coverage and cardinality checks."""

from __future__ import annotations

from typing import Literal

import polars as pl

JoinHow = Literal["inner", "left", "right", "full", "semi", "anti", "cross"]


class RequiredJoinKeyError(ValueError):
    """Required join failed closed: a key column is missing or seed rows are unmatched."""


class JoinCardinalityError(ValueError):
    """Optional left join changed the seed row count."""


def reject_required_coverage(
    *,
    required: bool,
    effective_how: JoinHow,
    pipeline_name: str,
    left_df: pl.DataFrame,
    right_df: pl.DataFrame,
    left_on: str | list[str],
    right_on: str | list[str],
) -> None:
    """Fail a required INNER join when any seed key is absent from the right side.

    Equal result height is not coverage: duplicate right keys can replace a
    missing seed row and keep the row count unchanged.
    """
    if not required or effective_how != "inner":
        return
    left_keys = [left_on] if isinstance(left_on, str) else left_on
    right_keys = [right_on] if isinstance(right_on, str) else right_on
    unmatched = left_df.select(left_keys).join(
        right_df.select(right_keys),
        left_on=left_keys,
        right_on=right_keys,
        how="anti",
    )
    if unmatched.height:
        raise RequiredJoinKeyError(
            f"Required join for {pipeline_name} has unmatched seed rows"
        )


def reject_join_cardinality(
    *,
    required: bool,
    join_how: JoinHow | None,
    resolved_how: JoinHow,
    pipeline_name: str,
    left_height: int,
    result_height: int,
) -> None:
    """Fail required joins and optional left joins that change seed height."""
    if result_height == left_height:
        return
    if required and join_how is None:
        raise RequiredJoinKeyError(
            f"Required join for {pipeline_name} changed cardinality "
            f"from {left_height} to {result_height}"
        )
    if resolved_how == "left":
        raise JoinCardinalityError(
            f"Join for {pipeline_name} changed cardinality "
            f"from {left_height} to {result_height}"
        )
