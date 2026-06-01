"""Backward-compatible re-export for ChEMBL semantic policy helpers."""

from __future__ import annotations

from bioetl.domain.normalization.profiles.chembl_policy_registry import (
    CHEMBL_CONTROLLED_VOCAB_CONFIG,
    CHEMBL_ONTOLOGY_POLICY_CONFIG,
    CHEMBL_REFERENCE_IDENTIFIER_CONFIG,
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
    PUBLICATION_CLASSIFICATION_CONFIG,
    ChemblControlledVocabularyFamily,
    ChemblOntologyPolicyFamily,
    ChemblPolicyRegistryData,
    ChemblPolicySurface,
    ChemblReferenceIdentifierFamily,
    ChemblStrictScalarFamily,
    chembl_boolean_family_fields,
    chembl_controlled_family_fields,
    chembl_flag_family_fields,
    chembl_ontology_family_fields,
    chembl_policy_surface,
    chembl_reference_identifier_family_fields,
    initialize_chembl_policy_registry,
)

__all__ = [
    "CHEMBL_CONTROLLED_VOCAB_CONFIG",
    "CHEMBL_ONTOLOGY_POLICY_CONFIG",
    "CHEMBL_REFERENCE_IDENTIFIER_CONFIG",
    "DEFAULT_CHEMBL_POLICY_REGISTRY_DATA",
    "PUBLICATION_CLASSIFICATION_CONFIG",
    "ChemblControlledVocabularyFamily",
    "ChemblOntologyPolicyFamily",
    "ChemblPolicyRegistryData",
    "ChemblPolicySurface",
    "ChemblReferenceIdentifierFamily",
    "ChemblStrictScalarFamily",
    "chembl_boolean_family_fields",
    "chembl_controlled_family_fields",
    "chembl_flag_family_fields",
    "chembl_ontology_family_fields",
    "chembl_policy_surface",
    "chembl_reference_identifier_family_fields",
    "initialize_chembl_policy_registry",
]
