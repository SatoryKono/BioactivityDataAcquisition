# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Governance checks for PubChem semantic payload registry."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

_REGISTRY = {
    "scalar_identifier_fields": [
        "molecule_id",
        "canonical_smiles",
        "isomeric_smiles",
        "inchi",
        "inchi_key",
        "standardized_canonical_smiles",
        "standardized_isomeric_smiles",
        "standardized_inchi",
        "standardized_inchi_key",
        "structure_parent_key",
    ],
    "iupac_name_variants": [
        "Allowed",
        "CAS-like Style",
        "Markup",
        "Preferred",
        "Systematic",
        "Traditional",
    ],
    "smiles_name_variants": ["Absolute", "Connectivity"],
    "property_urn_axes": [
        "datatype",
        "label",
        "name",
        "implementation",
        "software",
        "source",
        "release",
    ],
}
_EXPECTED_PROPERTY_VOCAB = {
    "datatype": ["1", "16", "5", "7"],
    "label": [
        "Compound",
        "Compound Complexity",
        "Count",
        "Fingerprint",
        "IUPAC Name",
        "InChI",
        "InChIKey",
        "Log P",
        "Mass",
        "Molecular Formula",
        "Molecular Weight",
        "SMILES",
        "Topological",
        "Weight",
    ],
    "name": [
        "Absolute",
        "Allowed",
        "CAS-like Style",
        "Canonicalized",
        "Connectivity",
        "Exact",
        "Hydrogen Bond Acceptor",
        "Hydrogen Bond Donor",
        "Markup",
        "MonoIsotopic",
        "Polar Surface Area",
        "Preferred",
        "Rotatable Bond",
        "Standard",
        "SubStructure Keys",
        "Systematic",
        "Traditional",
        "XLogP3",
        "XLogP3-AA",
    ],
    "implementation": [
        "E_COMPLEXITY",
        "E_NHACCEPTORS",
        "E_NHDONORS",
        "E_NROTBONDS",
        "E_SCREEN",
        "E_TPSA",
    ],
    "software": ["Cactvs", "InChI", "Lexichem TK", "OEChem", "PubChem"],
    "source": [
        "OpenEye Scientific Software",
        "Xemistry GmbH",
        "iupac.org",
        "ncbi.nlm.nih.gov",
        "sioc-ccbg.ac.cn",
    ],
    "release": ["2025.04.14", "2025.06.30", "2025.09.15"],
}
_BUSINESS_FIELDS = {
    "molecule_id",
    "canonical_smiles",
    "isomeric_smiles",
    "inchi",
    "inchi_key",
    "standardized_canonical_smiles",
    "standardized_isomeric_smiles",
    "standardized_inchi",
    "standardized_inchi_key",
    "structure_parent_key",
}


def test_pubchem_semantic_registry_declares_pipeline_semantic_field_groups() -> None:
    assert set(_REGISTRY["scalar_identifier_fields"]) <= _BUSINESS_FIELDS


def test_pubchem_semantic_registry_tracks_iupac_and_smiles_variant_terms() -> None:
    names = set(_EXPECTED_PROPERTY_VOCAB["name"])

    assert set(_REGISTRY["iupac_name_variants"]) <= names
    assert set(_REGISTRY["smiles_name_variants"]) <= names


def test_pubchem_semantic_registry_tracks_property_urn_axes() -> None:
    assert set(_REGISTRY["property_urn_axes"]) == set(_EXPECTED_PROPERTY_VOCAB)
