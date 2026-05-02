"""Tests for governed chemical structure standardization policies."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.chemical_standardization import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    standardize_chemical_structure,
)


@pytest.mark.unit
def test_standardizes_valid_pubchem_structure() -> None:
    """Valid structure identifiers are normalized and versioned."""
    result = standardize_chemical_structure(
        canonical_smiles=" CCO ",
        isomeric_smiles=" CCO ",
        inchi=" InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3 ",
        inchi_key=" lfqscwfljhtthz-uhfffaoysa-n ",
        covalent_unit_count=1,
        charge=0,
    )

    assert result.standardized_canonical_smiles == "CCO"
    assert result.standardized_isomeric_smiles == "CCO"
    assert result.standardized_inchi == "InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3"
    assert result.standardized_inchi_key == "LFQSCWFLJHTTHZ-UHFFFAOYSA-N"
    assert result.structure_parent_key == "inchikey14:LFQSCWFLJHTTHZ"
    assert result.chemical_standardization_status == "standardized"
    assert result.chemical_standardization_warnings == ()
    assert (
        result.chemical_standardization_policy_version
        == CHEMICAL_STANDARDIZATION_POLICY_VERSION
    )


@pytest.mark.unit
def test_reports_invalid_identifier_when_alternate_structure_is_valid() -> None:
    """Invalid inputs remain visible when another structural identifier survives."""
    result = standardize_chemical_structure(
        canonical_smiles="not a smiles",
        isomeric_smiles=None,
        inchi="InChI=1S/H2O/h1H2",
        inchi_key=None,
    )

    assert result.standardized_canonical_smiles is None
    assert result.standardized_inchi == "InChI=1S/H2O/h1H2"
    assert result.chemical_standardization_status == "partial"
    assert "canonical_smiles_invalid" in result.chemical_standardization_warnings
    assert (
        "structure_parent_key_unavailable" in result.chemical_standardization_warnings
    )


@pytest.mark.unit
def test_reports_multi_component_parent_deferred() -> None:
    """Salt-like inputs are not silently collapsed without a chemistry toolkit."""
    result = standardize_chemical_structure(
        canonical_smiles="CCO.Cl",
        isomeric_smiles=None,
        inchi=None,
        inchi_key=None,
        covalent_unit_count=2,
    )

    assert result.standardized_canonical_smiles == "CCO.Cl"
    assert result.structure_parent_key is None
    assert result.chemical_standardization_status == "partial"
    assert "multi_component_parent_deferred" in (
        result.chemical_standardization_warnings
    )


@pytest.mark.unit
def test_missing_structure_status_is_explicit() -> None:
    """Absent structural identifiers receive a bounded missing status."""
    result = standardize_chemical_structure(
        canonical_smiles=None,
        isomeric_smiles=" ",
        inchi=None,
        inchi_key=None,
    )

    assert result.chemical_standardization_status == "missing_structure"
    assert result.structure_parent_key is None
    assert "structure_parent_key_unavailable" in (
        result.chemical_standardization_warnings
    )


@pytest.mark.unit
def test_invalid_structure_status_is_explicit() -> None:
    """Invalid-only structures do not masquerade as standardized records."""
    result = standardize_chemical_structure(
        canonical_smiles="not a smiles",
        isomeric_smiles=None,
        inchi="invalid",
        inchi_key="invalid",
    )

    assert result.chemical_standardization_status == "invalid"
    assert result.standardized_canonical_smiles is None
    assert result.standardized_inchi is None
    assert result.standardized_inchi_key is None
    assert "canonical_smiles_invalid" in result.chemical_standardization_warnings
    assert "inchi_invalid" in result.chemical_standardization_warnings
    assert "inchi_key_invalid" in result.chemical_standardization_warnings
