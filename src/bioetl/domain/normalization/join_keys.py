"""Pure join-key normalization policies and scalar helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "JOIN_KEY_NORMALIZATION_POLICIES",
    "JoinKeyNormalizationPolicy",
    "get_join_key_normalization_policy",
    "normalize_join_key_scalar",
    "normalize_join_key_text",
    "stringify_join_key_value",
]


@dataclass(frozen=True, slots=True)
class JoinKeyNormalizationPolicy:
    """Normalization policy for one logical join key."""

    trim: bool = False
    lowercase: bool = False

    @property
    def requires_string_normalization(self) -> bool:
        """Return True when the policy mutates string values."""
        return self.trim or self.lowercase


_NOOP_POLICY = JoinKeyNormalizationPolicy()  # EXC-002: immutable module constant

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


def get_join_key_normalization_policy(
    key: str,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> JoinKeyNormalizationPolicy | None:
    """Return normalization policy for one logical join key."""
    return normalization_policies.get(key)


def normalize_join_key_text(
    value: str,
    *,
    key: str,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
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
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
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
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
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
