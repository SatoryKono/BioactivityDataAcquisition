"""Canonical field alias registry for cross-provider field unification.

Provides a single source of truth for mapping provider-specific field names
to canonical names used in Gold schemas and composite pipeline merge.

Problem:
    Different providers use different names for the same property:
    - ChEMBL: ``hba_count``, PubChem: ``h_bond_acceptor_count``
    - ChEMBL: ``polar_surface_area``, PubChem: ``tpsa``

    Without normalization, the composite merger cannot group these fields
    for conflict resolution or priority-based selection.

Solution:
    This registry defines canonical names and maps each provider's field
    name to its canonical equivalent. The ``ColumnRenamer`` uses this
    mapping during the rename step so that columns from different providers
    share the same field name in qualified format:

    - ``pubchem.compound.hba_count`` (not ``pubchem.compound.h_bond_acceptor_count``)
    - ``chembl.molecule.hba_count``

Requirements:
    - REQ-ARCH-003: No I/O in domain layer (immutable data only)

See Also:
    - ``application/composite/column_renamer.py``: Consumer of alias maps
    - ``configs/composites/molecule.yaml``: YAML field_aliases section
    - ``domain/mapping/molecule_fields.py``: Legacy flat mapping (to be superseded)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "FieldAlias",
    "get_alias_map_for_provider",
    "get_canonical_name",
    "get_provider_field",
]


@dataclass(frozen=True, slots=True)
class FieldAlias:
    """Immutable mapping from canonical field name to provider-specific aliases.

    Attributes:
        canonical_name: The canonical field name used in Gold schemas
            and composite merge configuration.
        provider_aliases: Mapping of ``{provider: provider_field_name}``.
            Providers whose field name already matches the canonical name
            may be omitted or included explicitly for documentation.
        description: Human-readable description of the field.

    Example:
        >>> alias = FieldAlias(
        ...     canonical_name="hba_count",
        ...     provider_aliases={"chembl": "hba_count", "pubchem": "h_bond_acceptor_count"},
        ...     description="Hydrogen bond acceptor count",
        ... )
        >>> alias.get_provider_field("pubchem")
        'h_bond_acceptor_count'
        >>> alias.get_provider_field("chembl")
        'hba_count'
    """

    canonical_name: str
    provider_aliases: dict[str, str]
    description: str

    def get_provider_field(self, provider: str) -> str:
        """Get the provider-specific field name.

        Args:
            provider: Provider name (e.g., ``'chembl'``, ``'pubchem'``).

        Returns:
            Provider-specific field name, or canonical_name if provider
            is not in the alias map.
        """
        return self.provider_aliases.get(provider, self.canonical_name)


# =============================================================================
# Molecule Field Alias Registry
# =============================================================================
# Canonical names follow ChEMBL conventions where possible (shorter, established).

MOLECULE_FIELD_ALIASES: Final[tuple[FieldAlias, ...]] = (
    FieldAlias(
        canonical_name="hba_count",
        provider_aliases={
            "chembl": "hba_count",
            "pubchem": "h_bond_acceptor_count",
        },
        description="Hydrogen bond acceptor count",
    ),
    FieldAlias(
        canonical_name="hbd_count",
        provider_aliases={
            "chembl": "hbd_count",
            "pubchem": "h_bond_donor_count",
        },
        description="Hydrogen bond donor count",
    ),
    FieldAlias(
        canonical_name="polar_surface_area",
        provider_aliases={
            "chembl": "polar_surface_area",
            "pubchem": "tpsa",
        },
        description="Topological polar surface area",
    ),
    FieldAlias(
        canonical_name="logp",
        provider_aliases={
            "chembl": "logp",
            "pubchem": "xlogp",
        },
        description="Octanol-water partition coefficient",
    ),
    FieldAlias(
        canonical_name="standard_inchi",
        provider_aliases={
            "chembl": "standard_inchi",
            "pubchem": "inchi",
        },
        description="Standard IUPAC InChI identifier",
    ),
)


# =============================================================================
# Indexed Lookups
# =============================================================================


def _build_provider_alias_index(
    aliases: tuple[FieldAlias, ...],
) -> dict[str, dict[str, str]]:
    """Build reverse index: provider -> {provider_field: canonical_name}.

    For each provider, creates a mapping from provider-specific field names
    to canonical names. Only includes entries where the provider field name
    differs from the canonical name (identity mappings are excluded since
    they don't need renaming).

    Args:
        aliases: Tuple of FieldAlias definitions.

    Returns:
        Nested dict keyed by provider, then by provider-specific field name.
    """
    index: dict[str, dict[str, str]] = {}
    for alias in aliases:
        for provider, provider_field in alias.provider_aliases.items():
            if provider_field != alias.canonical_name:
                if provider not in index:
                    index[provider] = {}
                index[provider][provider_field] = alias.canonical_name
    return index


_MOLECULE_ALIAS_INDEX: Final[dict[str, dict[str, str]]] = _build_provider_alias_index(
    MOLECULE_FIELD_ALIASES
)


def get_canonical_name(provider: str, field_name: str) -> str:
    """Get the canonical field name for a provider-specific field.

    If the field has a known alias for the given provider, returns the
    canonical name. Otherwise returns the field_name unchanged.

    Args:
        provider: Provider name (e.g., ``'pubchem'``).
        field_name: Provider-specific field name (e.g., ``'h_bond_acceptor_count'``).

    Returns:
        Canonical field name (e.g., ``'hba_count'``).

    Example:
        >>> get_canonical_name("pubchem", "h_bond_acceptor_count")
        'hba_count'
        >>> get_canonical_name("pubchem", "molecular_weight")
        'molecular_weight'
        >>> get_canonical_name("chembl", "hba_count")
        'hba_count'
    """
    provider_map = _MOLECULE_ALIAS_INDEX.get(provider, {})
    return provider_map.get(field_name, field_name)


def get_alias_map_for_provider(provider: str) -> dict[str, str]:
    """Get the full alias map for a provider.

    Returns a mapping of ``{provider_field: canonical_field}`` for fields
    where the provider uses a non-canonical name. Fields that already use
    the canonical name are not included.

    Args:
        provider: Provider name (e.g., ``'pubchem'``).

    Returns:
        Dict mapping provider-specific field names to canonical names.
        Empty dict if provider has no aliases.

    Example:
        >>> get_alias_map_for_provider("pubchem")
        {'h_bond_acceptor_count': 'hba_count', 'h_bond_donor_count': 'hbd_count', ...}
        >>> get_alias_map_for_provider("chembl")
        {}
    """
    return dict(_MOLECULE_ALIAS_INDEX.get(provider, {}))


def get_provider_field(canonical_name: str, provider: str) -> str:
    """Get the provider-specific field name for a canonical name.

    Reverse lookup: given a canonical name and a provider, returns the
    field name that provider uses.

    Args:
        canonical_name: Canonical field name (e.g., ``'hba_count'``).
        provider: Provider name (e.g., ``'pubchem'``).

    Returns:
        Provider-specific field name. Returns canonical_name if no alias
        is registered for the provider.

    Example:
        >>> get_provider_field("hba_count", "pubchem")
        'h_bond_acceptor_count'
        >>> get_provider_field("hba_count", "chembl")
        'hba_count'
    """
    for alias in MOLECULE_FIELD_ALIASES:
        if alias.canonical_name == canonical_name:
            return alias.get_provider_field(provider)
    return canonical_name
