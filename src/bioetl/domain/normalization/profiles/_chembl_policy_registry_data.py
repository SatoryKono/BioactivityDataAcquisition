"""Published immutable ChEMBL semantic-policy payloads for normalization."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEFAULT_CHEMBL_POLICY_REGISTRY_DATA",
    "ChemblControlledVocabularyFamily",
    "ChemblOntologyPolicyFamily",
    "ChemblPolicyRegistryData",
    "ChemblReferenceIdentifierFamily",
    "ChemblStrictScalarFamily",
]


@dataclass(frozen=True, slots=True)
class ChemblControlledVocabularyFamily:
    """Immutable controlled-vocabulary policy for one ChEMBL family."""

    family_name: str
    invalid_value_mode: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChemblStrictScalarFamily:
    """Immutable strict scalar family for boolean-like and 0/1 flag fields."""

    family_name: str
    invalid_value_mode: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChemblOntologyPolicyFamily:
    """Immutable ontology/reference policy for one ChEMBL family."""

    family_name: str
    fields: tuple[str, ...]
    companion_governance: str = "full_companion_bundle"
    code_label_fields: tuple[str, ...] = ()
    iri_fields: tuple[str, ...] = ()
    mapping_status_fields: tuple[str, ...] = ()
    version_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChemblReferenceIdentifierFamily:
    """Immutable reference-identifier policy for one ChEMBL family."""

    family_name: str
    reference_family: str
    invalid_value_mode: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChemblPolicyRegistryData:
    """Immutable semantic-policy payload consumed by domain normalization."""

    strict_boolean_families: tuple[ChemblStrictScalarFamily, ...]
    strict_flag_families: tuple[ChemblStrictScalarFamily, ...]
    controlled_vocabularies: tuple[ChemblControlledVocabularyFamily, ...]
    ontology_families: tuple[ChemblOntologyPolicyFamily, ...]
    publication_classification_fields: tuple[str, ...]
    reference_identifier_families: tuple[ChemblReferenceIdentifierFamily, ...] = ()


from bioetl.domain.normalization.profiles._chembl_policy_registry_defaults import (  # noqa: E402
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
)
