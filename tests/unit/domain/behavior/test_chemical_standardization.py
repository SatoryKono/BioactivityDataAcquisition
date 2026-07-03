"""Evidence tests for governed chemical structure standardization behavior."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.chemical_standardization import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    standardize_chemical_structure,
)


@pytest.mark.unit
def test_standardizes_valid_pubchem_structure_from_behavior_surface() -> None:
    """The canonical behavior API exposes stable PubChem standardization fields."""
    result = standardize_chemical_structure(
        canonical_smiles=" CCO ",
        isomeric_smiles=" CCO ",
        inchi=" InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3 ",
        inchi_key=" lfqscwfljhtthz-uhfffaoysa-n ",
        covalent_unit_count=1,
        charge=0,
    )

    assert result.structure_parent_key == "inchikey14:LFQSCWFLJHTTHZ"
    assert result.chemical_standardization_status == "standardized"
    assert (
        result.chemical_standardization_policy_version
        == CHEMICAL_STANDARDIZATION_POLICY_VERSION
    )


@pytest.mark.unit
def test_partial_standardization_keeps_visible_parent_key_warning() -> None:
    """Partial structures keep bounded warning evidence for operator triage."""
    result = standardize_chemical_structure(
        canonical_smiles="not a smiles",
        isomeric_smiles=None,
        inchi="InChI=1S/H2O/h1H2",
        inchi_key=None,
    )

    assert result.chemical_standardization_status == "partial"
    assert result.structure_parent_key is None
    assert (
        "structure_parent_key_unavailable" in result.chemical_standardization_warnings
    )
