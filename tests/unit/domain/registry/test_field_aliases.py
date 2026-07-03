"""Unit tests for field alias registry.

Tests the canonical field alias registry for cross-provider field unification.
"""

from __future__ import annotations

import pytest

from bioetl.domain.registry.field_aliases import (
    MOLECULE_FIELD_ALIASES,
    FieldAlias,
    get_alias_map_for_provider,
    get_canonical_name,
    get_provider_field,
)


pytestmark = pytest.mark.unit


class TestFieldAlias:
    """Tests for FieldAlias dataclass."""

    def test_field_alias_is_frozen(self) -> None:
        """FieldAlias should be immutable."""
        alias = FieldAlias(
            canonical_name="hba_count",
            provider_aliases={"chembl": "hba_count"},
            description="test",
        )
        with pytest.raises(AttributeError):
            alias.canonical_name = "other"  # type: ignore[misc]

    def test_get_provider_field_known(self) -> None:
        """Should return provider-specific field name."""
        alias = FieldAlias(
            canonical_name="hba_count",
            provider_aliases={
                "chembl": "hba_count",
                "pubchem": "h_bond_acceptor_count",
            },
            description="HBA count",
        )
        assert alias.get_provider_field("pubchem") == "h_bond_acceptor_count"
        assert alias.get_provider_field("chembl") == "hba_count"

    def test_get_provider_field_unknown_provider(self) -> None:
        """Should return canonical name for unknown provider."""
        alias = FieldAlias(
            canonical_name="hba_count",
            provider_aliases={"chembl": "hba_count"},
            description="HBA count",
        )
        assert alias.get_provider_field("zinc") == "hba_count"


class TestMoleculeFieldAliases:
    """Tests for MOLECULE_FIELD_ALIASES registry."""

    def test_registry_is_tuple(self) -> None:
        """Registry should be an immutable tuple."""
        assert isinstance(MOLECULE_FIELD_ALIASES, tuple)

    def test_registry_is_not_empty(self) -> None:
        """Registry should contain aliases."""
        assert len(MOLECULE_FIELD_ALIASES) > 0

    def test_all_entries_are_field_alias(self) -> None:
        """All entries should be FieldAlias instances."""
        for alias in MOLECULE_FIELD_ALIASES:
            assert isinstance(alias, FieldAlias)

    def test_canonical_names_are_unique(self) -> None:
        """Canonical names should be unique."""
        names = [a.canonical_name for a in MOLECULE_FIELD_ALIASES]
        assert len(names) == len(set(names))

    @pytest.mark.parametrize(
        "canonical_name",
        [
            "hba_count",
            "hbd_count",
            "polar_surface_area",
            "logp",
            "standard_inchi",
        ],
    )
    def test_expected_canonical_names_present(self, canonical_name: str) -> None:
        """All expected canonical names should be in the registry."""
        names = {a.canonical_name for a in MOLECULE_FIELD_ALIASES}
        assert canonical_name in names

    @pytest.mark.parametrize(
        ("canonical", "provider", "expected"),
        [
            ("hba_count", "chembl", "hba_count"),
            ("hba_count", "pubchem", "h_bond_acceptor_count"),
            ("hbd_count", "chembl", "hbd_count"),
            ("hbd_count", "pubchem", "h_bond_donor_count"),
            ("polar_surface_area", "chembl", "polar_surface_area"),
            ("polar_surface_area", "pubchem", "tpsa"),
            ("logp", "chembl", "logp"),
            ("logp", "pubchem", "xlogp"),
            ("standard_inchi", "chembl", "standard_inchi"),
            ("standard_inchi", "pubchem", "inchi"),
        ],
    )
    def test_molecule_field_aliases__provider_aliases__07053c75(
        self, canonical: str, provider: str, expected: str
    ) -> None:
        """Provider aliases should map correctly."""
        alias = next(a for a in MOLECULE_FIELD_ALIASES if a.canonical_name == canonical)
        assert alias.get_provider_field(provider) == expected


class TestGetCanonicalName:
    """Tests for get_canonical_name function."""

    def test_pubchem_h_bond_acceptor_count(self) -> None:
        """PubChem h_bond_acceptor_count should map to hba_count."""
        assert get_canonical_name("pubchem", "h_bond_acceptor_count") == "hba_count"

    def test_pubchem_h_bond_donor_count(self) -> None:
        """PubChem h_bond_donor_count should map to hbd_count."""
        assert get_canonical_name("pubchem", "h_bond_donor_count") == "hbd_count"

    def test_pubchem_tpsa(self) -> None:
        """PubChem tpsa should map to polar_surface_area."""
        assert get_canonical_name("pubchem", "tpsa") == "polar_surface_area"

    def test_pubchem_xlogp(self) -> None:
        """PubChem xlogp should map to logp."""
        assert get_canonical_name("pubchem", "xlogp") == "logp"

    def test_pubchem_inchi(self) -> None:
        """PubChem inchi should map to standard_inchi."""
        assert get_canonical_name("pubchem", "inchi") == "standard_inchi"

    def test_chembl_already_canonical(self) -> None:
        """ChEMBL fields already use canonical names, should pass through."""
        assert get_canonical_name("chembl", "hba_count") == "hba_count"
        assert get_canonical_name("chembl", "logp") == "logp"

    def test_unknown_field_passthrough(self) -> None:
        """Unknown fields should pass through unchanged."""
        assert get_canonical_name("pubchem", "molecular_weight") == "molecular_weight"

    def test_unknown_provider_passthrough(self) -> None:
        """Unknown providers should pass through unchanged."""
        assert get_canonical_name("zinc", "hba_count") == "hba_count"


class TestGetAliasMapForProvider:
    """Tests for get_alias_map_for_provider function."""

    def test_pubchem_has_aliases(self) -> None:
        """PubChem should have non-empty alias map."""
        alias_map = get_alias_map_for_provider("pubchem")
        assert len(alias_map) > 0

    def test_pubchem_alias_map_contents(self) -> None:
        """PubChem alias map should contain expected mappings."""
        alias_map = get_alias_map_for_provider("pubchem")
        assert alias_map["h_bond_acceptor_count"] == "hba_count"
        assert alias_map["h_bond_donor_count"] == "hbd_count"
        assert alias_map["tpsa"] == "polar_surface_area"
        assert alias_map["xlogp"] == "logp"
        assert alias_map["inchi"] == "standard_inchi"

    def test_chembl_has_no_aliases(self) -> None:
        """ChEMBL already uses canonical names, should have empty alias map."""
        alias_map = get_alias_map_for_provider("chembl")
        assert alias_map == {}

    def test_unknown_provider_empty(self) -> None:
        """Unknown provider should return empty alias map."""
        alias_map = get_alias_map_for_provider("zinc")
        assert alias_map == {}

    def test_returns_new_dict(self) -> None:
        """Should return a new dict (not reference to internal state)."""
        map1 = get_alias_map_for_provider("pubchem")
        map2 = get_alias_map_for_provider("pubchem")
        assert map1 == map2
        assert map1 is not map2


class TestGetProviderField:
    """Tests for get_provider_field function."""

    def test_canonical_to_pubchem(self) -> None:
        """Should return PubChem-specific field name."""
        assert get_provider_field("hba_count", "pubchem") == "h_bond_acceptor_count"
        assert get_provider_field("logp", "pubchem") == "xlogp"
        assert get_provider_field("standard_inchi", "pubchem") == "inchi"

    def test_canonical_to_chembl(self) -> None:
        """Should return ChEMBL-specific field name (same as canonical)."""
        assert get_provider_field("hba_count", "chembl") == "hba_count"
        assert get_provider_field("logp", "chembl") == "logp"

    def test_unknown_canonical_passthrough(self) -> None:
        """Unknown canonical name should pass through unchanged."""
        assert get_provider_field("molecular_weight", "pubchem") == "molecular_weight"

    def test_unknown_provider_returns_canonical(self) -> None:
        """Unknown provider should return canonical name."""
        assert get_provider_field("hba_count", "zinc") == "hba_count"
