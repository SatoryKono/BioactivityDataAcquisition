"""Canonical field alias registry for cross-provider field unification.

Maps provider-specific field names to canonical names used in Gold/composite
layer.  Silver schemas retain provider-native names for auditability;
renaming happens in the composite merger via ``ColumnRenamer``.

RF-NORM-01: Normalization Unification Plan.

Usage::

    from bioetl.domain.registry.field_aliases import (
        get_canonical_name,
        get_provider_name,
        MOLECULE_FIELD_ALIASES,
    )

    # PubChem field → canonical
    canonical = get_canonical_name("pubchem", "h_bond_acceptor_count")
    assert canonical == "hba_count"

    # canonical → PubChem field
    provider = get_provider_name("pubchem", "hba_count")
    assert provider == "h_bond_acceptor_count"
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FieldAlias:
    """Mapping between a canonical field name and provider-specific names.

    Attributes:
        canonical_name: Unified name used in Gold / composite schemas.
        provider_aliases: ``{provider: provider_field_name}`` mapping.
            Providers whose native name equals the canonical name MAY be
            omitted (they are resolved automatically).
        description: Human-readable description of the field.
    """

    canonical_name: str
    provider_aliases: dict[str, str]
    description: str


# ============================================================================
# Molecule / Compound field aliases (ChEMBL ↔ PubChem)
# ============================================================================

MOLECULE_FIELD_ALIASES: tuple[FieldAlias, ...] = (
    FieldAlias(
        canonical_name="hba_count",
        provider_aliases={"pubchem": "h_bond_acceptor_count"},
        description="Hydrogen bond acceptor count",
    ),
    FieldAlias(
        canonical_name="hbd_count",
        provider_aliases={"pubchem": "h_bond_donor_count"},
        description="Hydrogen bond donor count",
    ),
    FieldAlias(
        canonical_name="polar_surface_area",
        provider_aliases={"pubchem": "tpsa"},
        description="Topological polar surface area (Å²)",
    ),
    FieldAlias(
        canonical_name="logp",
        provider_aliases={"pubchem": "xlogp"},
        description="Octanol-water partition coefficient",
    ),
    FieldAlias(
        canonical_name="standard_inchi",
        provider_aliases={"pubchem": "inchi"},
        description="Standard IUPAC InChI identifier",
    ),
)


# ============================================================================
# Lookup helpers
# ============================================================================

# Pre-built indices for O(1) lookups.
# ``_PROVIDER_TO_CANONICAL[provider][provider_field] → canonical_name``
_PROVIDER_TO_CANONICAL: dict[str, dict[str, str]] = {}
# ``_CANONICAL_TO_PROVIDER[provider][canonical_name] → provider_field``
_CANONICAL_TO_PROVIDER: dict[str, dict[str, str]] = {}


def _build_indices() -> None:
    """Populate lookup indices from all alias tuples."""
    for alias in MOLECULE_FIELD_ALIASES:
        for provider, provider_field in alias.provider_aliases.items():
            _PROVIDER_TO_CANONICAL.setdefault(provider, {})[provider_field] = (
                alias.canonical_name
            )
            _CANONICAL_TO_PROVIDER.setdefault(provider, {})[alias.canonical_name] = (
                provider_field
            )


_build_indices()


def get_canonical_name(provider: str, field_name: str) -> str:
    """Return canonical name for a provider-specific field.

    If the field is not aliased, the original *field_name* is returned
    unchanged (identity mapping).

    Args:
        provider: Provider identifier (e.g. ``"pubchem"``).
        field_name: Provider-native field name.

    Returns:
        Canonical field name.
    """
    return _PROVIDER_TO_CANONICAL.get(provider, {}).get(field_name, field_name)


def get_provider_name(provider: str, canonical_name: str) -> str:
    """Return provider-specific name for a canonical field.

    If no alias exists, the *canonical_name* is returned unchanged.

    Args:
        provider: Provider identifier.
        canonical_name: Canonical (Gold-layer) field name.

    Returns:
        Provider-native field name.
    """
    return _CANONICAL_TO_PROVIDER.get(provider, {}).get(canonical_name, canonical_name)


def get_all_aliases_for_provider(provider: str) -> dict[str, str]:
    """Return all ``{provider_field: canonical_name}`` mappings for a provider.

    Args:
        provider: Provider identifier.

    Returns:
        Dictionary of provider-field → canonical-name mappings.
    """
    return dict(_PROVIDER_TO_CANONICAL.get(provider, {}))


__all__ = [
    "MOLECULE_FIELD_ALIASES",
    "FieldAlias",
    "get_all_aliases_for_provider",
    "get_canonical_name",
    "get_provider_name",
]
