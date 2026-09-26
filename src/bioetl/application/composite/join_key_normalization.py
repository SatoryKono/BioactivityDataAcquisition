"""Application adapters for composite join-key normalization."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING

from bioetl.domain.normalization.join_keys import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    JoinKeyNormalizationPolicy,
    get_join_key_normalization_policy,
    normalize_join_key_scalar,
    normalize_join_key_text,
    stringify_join_key_value,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite import CompositeConfig


def iter_configured_join_keys(config: CompositeConfig) -> Iterable[str]:
    """Yield every configured join key from enrichers and dependencies."""
    for enricher in config.enrichers:
        yield from enricher.join_keys
    for dependency in config.dependencies:
        yield from dependency.join_keys


def validate_join_key_normalization_policies(
    config: CompositeConfig,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> None:
    """Ensure every configured composite join key has an explicit policy."""
    configured_keys = set(iter_configured_join_keys(config))
    missing = sorted(
        key for key in configured_keys if key not in normalization_policies
    )
    if missing:
        missing_keys = ", ".join(missing)
        raise ValueError(
            "Composite config uses join keys without normalization policy: "
            f"{missing_keys}"
        )


def build_join_key_normalization_expr(
    *,
    column: str,
    key: str,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> pl.Expr | None:
    """Build a Polars expression that normalizes one resolved join-key column."""
    import polars as pl

    policy = get_join_key_normalization_policy(
        key,
        normalization_policies=normalization_policies,
    )
    if policy is None or not policy.requires_string_normalization:
        return None

    expr = pl.col(column).cast(pl.String)
    if policy.domain_canonicalizer is not None:
        return expr.map_elements(
            lambda value: (
                None
                if value is None
                else normalize_join_key_text(
                    value,
                    key=key,
                    normalization_policies=normalization_policies,
                )
            ),
            return_dtype=pl.String,
            skip_nulls=False,
        ).alias(column)
    if policy.trim:
        expr = expr.str.strip_chars()
    if policy.lowercase:
        expr = expr.str.to_lowercase()
    return expr.alias(column)


def normalize_join_key_dataframe_columns(
    *,
    df: pl.DataFrame,
    join_keys: Iterable[str],
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> pl.DataFrame:
    """Normalize exact-name join key columns in a DataFrame."""
    expressions = [
        expr
        for key in join_keys
        if key in df.columns
        if (
            expr := build_join_key_normalization_expr(
                column=key,
                key=key,
                normalization_policies=normalization_policies,
            )
        )
        is not None
    ]
    if not expressions:
        return df
    return df.with_columns(expressions)


__all__ = [
    "JOIN_KEY_NORMALIZATION_POLICIES",
    "JoinKeyNormalizationPolicy",
    "build_join_key_normalization_expr",
    "get_join_key_normalization_policy",
    "iter_configured_join_keys",
    "normalize_join_key_dataframe_columns",
    "normalize_join_key_scalar",
    "normalize_join_key_text",
    "stringify_join_key_value",
    "validate_join_key_normalization_policies",
]
