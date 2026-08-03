"""Pure helper functions for join-key resolution and normalization."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING

from bioetl.application.composite.join_key_normalization import (
    JoinKeyNormalizationPolicy,
    build_join_key_normalization_expr,
)

if TYPE_CHECKING:
    import polars as pl


def build_qualified_join_key(
    *,
    parse_pipeline_name: Callable[[str], tuple[str, str]],
    pipeline: str | None,
    key: str,
) -> str | None:
    """Build a qualified ``provider.entity.key`` name when pipeline is parseable."""
    if pipeline is None:
        return None
    try:
        provider, entity = parse_pipeline_name(pipeline)
    except ValueError:
        return None
    return f"{provider}.{entity}.{key}"


def find_join_key_column(
    *,
    key: str,
    columns: list[str],
    pipeline: str | None,
    parse_pipeline_name: Callable[[str], tuple[str, str]],
) -> str | None:
    """Find key column name with qualified candidate preferred over fallback forms."""
    qualified = build_qualified_join_key(
        parse_pipeline_name=parse_pipeline_name,
        pipeline=pipeline,
        key=key,
    )
    if qualified is not None and qualified in columns:
        return qualified
    if key in columns:
        return key
    return next((column for column in columns if column.endswith(f".{key}")), None)


def normalize_join_key_columns(
    *,
    df: pl.DataFrame,
    join_keys: list[str],
    pipeline: str | None,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy],
    parse_pipeline_name: Callable[[str], tuple[str, str]],
) -> pl.DataFrame:
    """Apply canonical trim/casing policy to resolved join-key columns."""
    expressions = [
        expr
        for key in join_keys
        if (
            column := find_join_key_column(
                key=key,
                columns=df.columns,
                pipeline=pipeline,
                parse_pipeline_name=parse_pipeline_name,
            )
        )
        if (
            expr := build_join_key_normalization_expr(
                column=column,
                key=key,
                normalization_policies=normalization_policies,
            )
        )
        is not None
    ]
    if not expressions:
        return df
    return df.with_columns(expressions)


def resolve_join_key_names(
    *,
    primary_key: str,
    seed_pipeline: str | None,
    enricher_pipeline: str,
    merged_columns: list[str],
    parse_pipeline_name: Callable[[str], tuple[str, str]],
) -> tuple[str, str, str | None]:
    """Resolve qualified join keys for the common symmetric join case."""
    return _resolve_join_key_names_internal(
        left_key=primary_key,
        right_key=primary_key,
        left_pipeline=seed_pipeline,
        right_pipeline=enricher_pipeline,
        merged_columns=merged_columns,
        parse_pipeline_name=parse_pipeline_name,
    )


def resolve_join_key_names_asymmetric(
    *,
    left_key: str,
    right_key: str,
    left_pipeline: str | None,
    right_pipeline: str,
    merged_columns: list[str],
    parse_pipeline_name: Callable[[str], tuple[str, str]],
) -> tuple[str, str, str | None]:
    """Resolve qualified join keys when left/right key names differ."""
    return _resolve_join_key_names_internal(
        left_key=left_key,
        right_key=right_key,
        left_pipeline=left_pipeline,
        right_pipeline=right_pipeline,
        merged_columns=merged_columns,
        parse_pipeline_name=parse_pipeline_name,
    )


def _resolve_join_key_names_internal(
    *,
    left_key: str,
    right_key: str,
    left_pipeline: str | None,
    right_pipeline: str,
    merged_columns: list[str],
    parse_pipeline_name: Callable[[str], tuple[str, str]],
) -> tuple[str, str, str | None]:
    """Resolve one qualified left/right join-key pair with optional asymmetry."""
    left_join_key_qualified = build_qualified_join_key(
        parse_pipeline_name=parse_pipeline_name,
        pipeline=left_pipeline,
        key=left_key,
    )
    left_join_key = (
        left_join_key_qualified
        if left_join_key_qualified is not None
        and left_join_key_qualified in merged_columns
        else left_key
    )
    right_join_key = (
        build_qualified_join_key(
            parse_pipeline_name=parse_pipeline_name,
            pipeline=right_pipeline,
            key=right_key,
        )
        or right_key
    )
    return left_join_key, right_join_key, left_join_key_qualified


def resolve_composite_join_keys(
    *,
    join_keys_list: list[str],
    left_pipeline: str | None,
    right_pipeline: str,
    merged_columns: list[str],
    parse_pipeline_name: Callable[[str], tuple[str, str]],
) -> tuple[list[str], list[str], set[str]]:
    """Resolve composite join keys for dependency joins."""
    left_keys: list[str] = []
    right_keys: list[str] = []
    all_join_key_set: set[str] = set()

    for key in join_keys_list:
        left_key, right_key, left_key_qualified = resolve_join_key_names_asymmetric(
            left_key=key,
            right_key=key,
            left_pipeline=left_pipeline,
            right_pipeline=right_pipeline,
            merged_columns=merged_columns,
            parse_pipeline_name=parse_pipeline_name,
        )
        left_keys.append(left_key)
        right_keys.append(right_key)
        all_join_key_set.add(left_key)
        all_join_key_set.add(right_key)
        if left_key_qualified is not None and left_key_qualified != left_key:
            all_join_key_set.add(left_key_qualified)

    return left_keys, right_keys, all_join_key_set


__all__ = [
    "build_qualified_join_key",
    "find_join_key_column",
    "normalize_join_key_columns",
    "resolve_composite_join_keys",
    "resolve_join_key_names",
    "resolve_join_key_names_asymmetric",
]
