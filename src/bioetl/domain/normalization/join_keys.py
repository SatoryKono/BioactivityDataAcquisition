"""Pure join-key normalization policies and scalar helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from bioetl.domain.normalization.identifiers import (
    normalize_doi,
    normalize_pmc_id,
    normalize_pmid,
)
from bioetl.domain.normalization.text import normalize_title
from bioetl.domain.value_objects.identifiers import ChemblId, UniProtId

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
    domain_canonicalizer: Callable[[str], str | None] | None = None

    @property
    def requires_string_normalization(self) -> bool:
        """Return True when the policy mutates string values."""
        return self.trim or self.lowercase or self.domain_canonicalizer is not None


def _normalize_join_key_doi(value: str) -> str | None:
    """Normalize DOI text through the domain identifier seam."""
    return normalize_doi(value)


def _normalize_join_key_pmid(value: str) -> str | None:
    """Normalize PMID join text while tolerating an explicit PMID prefix."""
    normalized = value.strip()
    if normalized.lower().startswith("pmid:"):
        normalized = normalized[5:]
    return normalize_pmid(normalized)


def _normalize_join_key_pmc_id(value: str) -> str | None:
    """Normalize PMC join text through the domain identifier seam."""
    return normalize_pmc_id(value)


def _normalize_join_key_inchi_key(value: str) -> str | None:
    """Normalize InChIKey join text through the canonical value object seam."""
    from bioetl.domain.value_objects.chemical import InChIKey

    normalized = InChIKey.from_raw(value)
    return None if normalized is None else normalized.value


def _normalize_join_key_target_id(value: str) -> str | None:
    """Normalize ChEMBL target join text through the canonical value object seam."""
    normalized = ChemblId.from_raw(value)
    return None if normalized is None else normalized.value


def _normalize_join_key_uniprot_accession(value: str) -> str | None:
    """Normalize UniProt accession join text through the canonical value object seam."""
    normalized = UniProtId.from_raw(value)
    return None if normalized is None else normalized.value


def _normalize_join_key_title(value: str) -> str | None:
    """Normalize title join text through the canonical title cleanup seam.

    Title fallback remains case-preserving on purpose. HTML/entity cleanup,
    Unicode NFC normalization, control-character removal and whitespace
    collapsing now match provider publication title profiles.
    """
    return normalize_title(value)


_NOOP_POLICY = JoinKeyNormalizationPolicy()  # EXC-002: immutable module constant

JOIN_KEY_NORMALIZATION_POLICIES: Mapping[str, JoinKeyNormalizationPolicy] = {
    "canonical_smiles": JoinKeyNormalizationPolicy(trim=True),
    "cell_id": _NOOP_POLICY,
    "doi": JoinKeyNormalizationPolicy(
        trim=True,
        lowercase=True,
        domain_canonicalizer=_normalize_join_key_doi,
    ),
    "inchi_key": JoinKeyNormalizationPolicy(
        trim=True,
        domain_canonicalizer=_normalize_join_key_inchi_key,
    ),
    "molecule_id": _NOOP_POLICY,
    "pmc_id": JoinKeyNormalizationPolicy(
        trim=True,
        lowercase=True,
        domain_canonicalizer=_normalize_join_key_pmc_id,
    ),
    "pmid": JoinKeyNormalizationPolicy(
        trim=True,
        lowercase=True,
        domain_canonicalizer=_normalize_join_key_pmid,
    ),
    "primary_component_id": _NOOP_POLICY,
    "protein_classification_id": _NOOP_POLICY,
    "publication_id": _NOOP_POLICY,
    "target_id": JoinKeyNormalizationPolicy(
        trim=True,
        domain_canonicalizer=_normalize_join_key_target_id,
    ),
    "title": JoinKeyNormalizationPolicy(
        trim=True,
        domain_canonicalizer=_normalize_join_key_title,
    ),
    "tissue_id": _NOOP_POLICY,
    "uniprot_accession": JoinKeyNormalizationPolicy(
        trim=True,
        domain_canonicalizer=_normalize_join_key_uniprot_accession,
    ),
}


def get_join_key_normalization_policy(
    key: str,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> JoinKeyNormalizationPolicy | None:
    """Return normalization policy for one logical join key."""
    return normalization_policies.get(key)


def _apply_join_key_policy(
    value: str,
    policy: JoinKeyNormalizationPolicy,
) -> str | None:
    """Normalize one string value according to a resolved join-key policy."""
    if policy.domain_canonicalizer is not None:
        normalized = policy.domain_canonicalizer(value)
        if normalized is None:
            return None
    elif policy.trim:
        normalized = value.strip()
    else:
        normalized = value
    return normalized.lower() if policy.lowercase else normalized


def normalize_join_key_text(
    value: str,
    *,
    key: str,
    normalization_policies: Mapping[
        str, JoinKeyNormalizationPolicy
    ] = JOIN_KEY_NORMALIZATION_POLICIES,
) -> str | None:
    """Apply canonical trim/casing transforms to one string join key value."""
    policy = get_join_key_normalization_policy(
        key,
        normalization_policies=normalization_policies,
    )
    if policy is None:
        return value

    return _apply_join_key_policy(value, policy)


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
    if normalized is None:
        return ""
    return str(normalized)
