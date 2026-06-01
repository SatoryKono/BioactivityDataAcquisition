"""Backward-compatible re-export for ChEMBL policy registry payloads."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.chembl_policy_registry_data import (
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
    ChemblControlledVocabularyFamily,
    ChemblOntologyPolicyFamily,
    ChemblPolicyRegistryData,
    ChemblReferenceIdentifierFamily,
    ChemblStrictScalarFamily,
)

__all__ = [
    "DEFAULT_CHEMBL_POLICY_REGISTRY_DATA",
    "ChemblControlledVocabularyFamily",
    "ChemblOntologyPolicyFamily",
    "ChemblPolicyRegistryData",
    "ChemblReferenceIdentifierFamily",
    "ChemblStrictScalarFamily",
]
