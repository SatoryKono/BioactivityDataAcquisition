"""Profile modules must import without unknown standard-profile keys."""

from __future__ import annotations

import importlib

import pytest

pytestmark = pytest.mark.unit

_PROFILE_MODULES = (
    "bioetl.domain.normalization.profiles.chembl_target_protein_classification",
    "bioetl.domain.normalization.profiles.chembl_tissue",
    "bioetl.domain.normalization.profiles.crossref_publication",
    "bioetl.domain.normalization.profiles.openalex_publication",
    "bioetl.domain.normalization.profiles.pubmed_publication",
    "bioetl.domain.normalization.profiles.pubchem_compound",
    "bioetl.domain.normalization.profiles.semanticscholar_publication",
    "bioetl.domain.normalization.profiles.uniprot_idmapping",
    "bioetl.domain.normalization.profiles.uniprot_protein",
)


@pytest.mark.parametrize("module_name", _PROFILE_MODULES)
def test_profile_module_imports(module_name: str) -> None:
    module = importlib.import_module(module_name)
    profiles = [
        value
        for name, value in vars(module).items()
        if name.endswith("_PROFILE") and not name.startswith("_")
    ]
    assert profiles
