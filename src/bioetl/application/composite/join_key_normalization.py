"""Canonical join-key normalization policies for composite pipelines."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import CompositeConfig


@dataclass(frozen=True, slots=True)
class JoinKeyNormalizationPolicy:
    """Normalization policy for one logical join key."""

    trim: bool = False
    lowercase: bool = False

    @property
    def requires_string_normalization(self) -> bool:
        """Return True when the policy mutates string values."""
        return self.trim or self.lowercase


_NOOP_POLICY = JoinKeyNormalizationPolicy()

JOIN_KEY_NORMALIZATION_POLICIES: Mapping[str, JoinKeyNormalizationPolicy] = {
    "canonical_smiles": JoinKeyNormalizationPolicy(trim=True),
    "cell_id": _NOOP_POLICY,
    "doi": JoinKeyNormalizationPolicy(trim=True, lowercase=True),
    "inchi_key": JoinKeyNormalizationPolicy(trim=True),
    "molecule_id": _NOOP_POLICY,
    "pmc_id": JoinKeyNormalizationPolicy(trim=True, lowercase=True),
    "pmid": JoinKeyNormalizationPolicy(trim=True, lowercase=True),
    "primary_component_id": _NOOP_POLICY,
    "protein_classification_id": _NOOP_POLICY,
    "publication_id": _NOOP_POLICY,
    "target_id": _NOOP_POLICY,
    "title": JoinKeyNormalizationPolicy(trim=True),
    "tissue_id": _NOOP_POLICY,
    "uniprot_accession": JoinKeyNormalizationPolicy(trim=True, lowercase=True),
}


def iter_configured_join_keys(config: CompositeConfig) -> Iterable[str]:
    """Yield every configured join key from enrichers and dependencies."""
    for enricher in config.enrichers:
        yield from enricher.join_keys
    for dependency in config.dependencies:
        yield from dependency.join_keys



def get_join_key_normalization_policy(
    key: str,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> JoinKeyNormalizationPolicy | None:
    """Return normalization policy for one logical join key."""
    return normalization_policies.get(key)



def validate_join_key_normalization_policies(
    config: CompositeConfig,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> None:
    """Ensure every configured composite join key has an explicit policy."""
    configured_keys = set(iter_configured_join_keys(config))
    missing = sorted(key for key in configured_keys if key not in normalization_policies)
    if missing:
        missing_keys = ", ".join(missing)
        raise ValueError(
            "Composite config uses join keys without normalization policy: "
            f"{missing_keys}"
        )



def normalize_join_key_text(
    value: str,
    *,
    key: str,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> str:
    """Apply canonical trim/casing transforms to one string join key value."""
    policy = get_join_key_normalization_policy(
        key,
        normalization_policies=normalization_policies,
    )
    if policy is None:
        return value

    normalized = value.strip() if policy.trim else value
    return normalized.lower() if policy.lowercase else normalized



def normalize_join_key_scalar(
    value: object,
    *,
    key: str,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> object:
    """Normalize one scalar join key while preserving non-string types."""
    if isinstance(value, str):
        return normalize_join_key_text(
            value,
            key=key,
            normalization_policies=normalization_policies,
        )
    return value



def stringify_join_key_value(
    value: object,
    *,
    key: str,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> str:
    """Convert a join key to a stable filter ID string with normalization."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    normalized = normalize_join_key_scalar(
        value,
        key=key,
        normalization_policies=normalization_policies,
    )
    return str(normalized)



def build_join_key_normalization_expr(
    *,
    column: str,
    key: str,
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy] = JOIN_KEY_NORMALIZATION_POLICIES,
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
    if policy.trim:
        expr = expr.str.strip_chars()
    if policy.lowercase:
        expr = expr.str.to_lowercase()
    return expr.alias(column)



def normalize_join_key_dataframe_columns(
    *,
    df: pl.DataFrame,
    join_keys: Iterable[str],
    normalization_policies: Mapping[str, JoinKeyNormalizationPolicy] = JOIN_KEY_NORMALIZATION_POLICIES,
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
        ) is not None
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
