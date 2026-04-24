"""Shared ChEMBL semantic policy surfaces beyond strict enums.

The domain module consumes immutable policy payloads and stays free from
filesystem/config parsing. Runtime bootstrap may optionally inject a policy
payload loaded from published config files, while tests can provide in-memory
data directly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from bioetl.domain.normalization.profiles._chembl_policy_registry_data import (
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
    ChemblControlledVocabularyFamily,
    ChemblOntologyPolicyFamily,
    ChemblPolicyRegistryData,
)

__all__ = [
    "CHEMBL_CONTROLLED_VOCAB_CONFIG",
    "CHEMBL_ONTOLOGY_POLICY_CONFIG",
    "DEFAULT_CHEMBL_POLICY_REGISTRY_DATA",
    "PUBLICATION_CLASSIFICATION_CONFIG",
    "ChemblControlledVocabularyFamily",
    "ChemblOntologyPolicyFamily",
    "ChemblPolicyRegistryData",
    "ChemblPolicySurface",
    "chembl_controlled_family_fields",
    "chembl_ontology_family_fields",
    "chembl_policy_surface",
    "initialize_chembl_policy_registry",
]

CHEMBL_CONTROLLED_VOCAB_CONFIG = "configs/vocab/chembl_controlled.yaml"
CHEMBL_ONTOLOGY_POLICY_CONFIG = "configs/vocab/chembl_ontology.yaml"
PUBLICATION_CLASSIFICATION_CONFIG = "configs/enums/publication_type_classification.csv"


@dataclass(frozen=True, slots=True)
class ChemblPolicySurface:
    """Code-visible semantic category and registry source for one ChEMBL field."""

    category: str
    registry_source: str
    invalid_value_mode: str


_CONTROLLED_VOCABULARIES: Mapping[str, ChemblControlledVocabularyFamily] = (
    MappingProxyType({})
)
_ONTOLOGY_FAMILIES: Mapping[str, ChemblOntologyPolicyFamily] = MappingProxyType({})
_POLICY_SURFACES: Mapping[tuple[str, str], ChemblPolicySurface] = MappingProxyType({})


def _parse_chembl_field_ref(field_ref: str) -> tuple[str, str]:
    pipeline_name, field_name = field_ref.split(".", maxsplit=1)
    if not pipeline_name.startswith("chembl_"):
        raise ValueError(
            "Expected ChEMBL field ref in '<pipeline_name>.<field>' form with "
            f"'chembl_' prefix; got {field_ref!r}"
        )
    return pipeline_name.removeprefix("chembl_"), field_name


def _build_policy_surfaces(
    data: ChemblPolicyRegistryData,
) -> Mapping[tuple[str, str], ChemblPolicySurface]:
    surfaces: dict[tuple[str, str], ChemblPolicySurface] = {}

    for controlled_family in data.controlled_vocabularies:
        for field_ref in controlled_family.fields:
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category="controlled_vocabulary",
                registry_source=CHEMBL_CONTROLLED_VOCAB_CONFIG,
                invalid_value_mode=controlled_family.invalid_value_mode,
            )

    for ontology_family in data.ontology_families:
        for field_ref in ontology_family.fields:
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category="ontology_reference_identifier",
                registry_source=CHEMBL_ONTOLOGY_POLICY_CONFIG,
                invalid_value_mode="preserve_unknown_lexeme",
            )
        for field_ref in ontology_family.code_label_fields:
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category="derived_vocabulary",
                registry_source=CHEMBL_ONTOLOGY_POLICY_CONFIG,
                invalid_value_mode="resolve_identifier_backed_label",
            )

    for field_name in data.publication_classification_fields:
        surfaces[("publication", field_name)] = ChemblPolicySurface(
            category="derived_vocabulary",
            registry_source=PUBLICATION_CLASSIFICATION_CONFIG,
            invalid_value_mode="reject_unknown_taxonomy_value",
        )

    return MappingProxyType(surfaces)


def initialize_chembl_policy_registry(data: ChemblPolicyRegistryData) -> None:
    """Inject immutable policy data into the domain registry runtime state."""
    global _CONTROLLED_VOCABULARIES, _ONTOLOGY_FAMILIES, _POLICY_SURFACES

    _CONTROLLED_VOCABULARIES = MappingProxyType(
        {family.family_name: family for family in data.controlled_vocabularies}
    )
    _ONTOLOGY_FAMILIES = MappingProxyType(
        {family.family_name: family for family in data.ontology_families}
    )
    _POLICY_SURFACES = _build_policy_surfaces(data)


def _family_fields(
    *,
    fields: list[str],
    entity: str | None,
) -> frozenset[str]:
    return frozenset(
        field_name
        for known_entity, field_name in (
            _parse_chembl_field_ref(str(field_ref)) for field_ref in fields
        )
        if entity is None or known_entity == entity
    )


def chembl_policy_surface(entity: str, field: str) -> ChemblPolicySurface | None:
    """Return the shared ChEMBL policy surface for one field when defined."""
    return _POLICY_SURFACES.get((entity, field))


def chembl_controlled_family_fields(
    family: str,
    *,
    entity: str | None = None,
) -> frozenset[str]:
    """Return field names governed by one shared controlled-vocabulary family."""
    payload = _CONTROLLED_VOCABULARIES[family]
    return _family_fields(fields=list(payload.fields), entity=entity)


def chembl_ontology_family_fields(
    family: str,
    *,
    entity: str | None = None,
    include_code_label_fields: bool = False,
) -> frozenset[str]:
    """Return field names governed by one shared ontology/reference-ID family."""
    payload = _ONTOLOGY_FAMILIES[family]
    fields = list(payload.fields)
    if include_code_label_fields:
        fields.extend(payload.code_label_fields)
    return _family_fields(fields=fields, entity=entity)


initialize_chembl_policy_registry(DEFAULT_CHEMBL_POLICY_REGISTRY_DATA)
