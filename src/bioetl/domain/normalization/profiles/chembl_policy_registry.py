# pyright: reportConstantRedefinition=false
# Optional dependency probe flags reassigned after try/import (PD2-7).
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

from bioetl.domain.normalization.profiles._chembl_policy_family_mapping import (
    family_mapping_by_name,
)
from bioetl.domain.normalization.profiles.chembl_policy_registry_data import (
    DEFAULT_CHEMBL_POLICY_REGISTRY_DATA,
    ChemblControlledVocabularyFamily,
    ChemblOntologyPolicyFamily,
    ChemblPolicyRegistryData,
    ChemblReferenceIdentifierFamily,
    ChemblStrictScalarFamily,
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

CHEMBL_CONTROLLED_VOCAB_CONFIG = "configs/vocab/chembl_controlled.yaml"
CHEMBL_ONTOLOGY_POLICY_CONFIG = "configs/vocab/chembl_ontology.yaml"
CHEMBL_REFERENCE_IDENTIFIER_CONFIG = "configs/vocab/chembl_reference_identifiers.yaml"
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
_STRICT_BOOLEAN_FAMILIES: Mapping[str, ChemblStrictScalarFamily] = MappingProxyType({})
_STRICT_FLAG_FAMILIES: Mapping[str, ChemblStrictScalarFamily] = MappingProxyType({})
_ONTOLOGY_FAMILIES: Mapping[str, ChemblOntologyPolicyFamily] = MappingProxyType({})
_REFERENCE_IDENTIFIER_FAMILIES: Mapping[str, ChemblReferenceIdentifierFamily] = (
    MappingProxyType({})
)
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
    _add_strict_scalar_surfaces(
        surfaces, data.strict_boolean_families, "strict_boolean"
    )
    _add_strict_scalar_surfaces(surfaces, data.strict_flag_families, "strict_flag")
    _add_controlled_vocabulary_surfaces(surfaces, data)
    _add_ontology_surfaces(surfaces, data)
    _add_reference_identifier_surfaces(surfaces, data)
    _add_publication_classification_surfaces(surfaces, data)
    return MappingProxyType(surfaces)


def _add_strict_scalar_surfaces(
    surfaces: dict[tuple[str, str], ChemblPolicySurface],
    families: tuple[ChemblStrictScalarFamily, ...],
    category: str,
) -> None:
    for family in families:
        for field_ref in family.fields:
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category=category,
                registry_source=CHEMBL_CONTROLLED_VOCAB_CONFIG,
                invalid_value_mode=family.invalid_value_mode,
            )


def _add_controlled_vocabulary_surfaces(
    surfaces: dict[tuple[str, str], ChemblPolicySurface],
    data: ChemblPolicyRegistryData,
) -> None:
    for controlled_family in data.controlled_vocabularies:
        for field_ref in controlled_family.fields:
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category="controlled_vocabulary",
                registry_source=CHEMBL_CONTROLLED_VOCAB_CONFIG,
                invalid_value_mode=controlled_family.invalid_value_mode,
            )


def _add_ontology_surfaces(
    surfaces: dict[tuple[str, str], ChemblPolicySurface],
    data: ChemblPolicyRegistryData,
) -> None:
    for ontology_family in data.ontology_families:
        _register_ontology_family_fields(
            surfaces,
            ontology_family.fields,
            category="ontology_reference_identifier",
            invalid_value_mode="preserve_unknown_lexeme",
        )
        _register_ontology_family_fields(
            surfaces,
            ontology_family.code_label_fields,
            category="derived_vocabulary",
            invalid_value_mode="resolve_identifier_backed_label",
        )
        _register_ontology_family_fields(
            surfaces,
            ontology_family.iri_fields,
            category="ontology_reference_identifier",
            invalid_value_mode="resolve_identifier_backed_iri",
        )
        _register_ontology_family_fields(
            surfaces,
            ontology_family.mapping_status_fields,
            category="ontology_reference_metadata",
            invalid_value_mode="resolve_identifier_backed_mapping_status",
        )
        _register_ontology_family_fields(
            surfaces,
            ontology_family.version_fields,
            category="ontology_reference_metadata",
            invalid_value_mode="resolve_identifier_backed_version",
        )


def _register_ontology_family_fields(
    surfaces: dict[tuple[str, str], ChemblPolicySurface],
    field_refs: tuple[str, ...],
    *,
    category: str,
    invalid_value_mode: str,
) -> None:
    for field_ref in field_refs:
        entity, field_name = _parse_chembl_field_ref(str(field_ref))
        surfaces[(entity, field_name)] = ChemblPolicySurface(
            category=category,
            registry_source=CHEMBL_ONTOLOGY_POLICY_CONFIG,
            invalid_value_mode=invalid_value_mode,
        )


def _add_publication_classification_surfaces(
    surfaces: dict[tuple[str, str], ChemblPolicySurface],
    data: ChemblPolicyRegistryData,
) -> None:
    for field_name in data.publication_classification_fields:
        surfaces[("publication", field_name)] = ChemblPolicySurface(
            category="derived_vocabulary",
            registry_source=PUBLICATION_CLASSIFICATION_CONFIG,
            invalid_value_mode="reject_unknown_taxonomy_value",
        )


def _add_reference_identifier_surfaces(
    surfaces: dict[tuple[str, str], ChemblPolicySurface],
    data: ChemblPolicyRegistryData,
) -> None:
    for reference_family in data.reference_identifier_families:
        for field_ref in reference_family.fields:
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category="reference_identifier",
                registry_source=CHEMBL_REFERENCE_IDENTIFIER_CONFIG,
                invalid_value_mode=reference_family.invalid_value_mode,
            )


def initialize_chembl_policy_registry(data: ChemblPolicyRegistryData) -> None:
    """Inject immutable policy data into the domain registry runtime state."""
    global _CONTROLLED_VOCABULARIES, _ONTOLOGY_FAMILIES, _POLICY_SURFACES
    global _REFERENCE_IDENTIFIER_FAMILIES, _STRICT_BOOLEAN_FAMILIES
    global _STRICT_FLAG_FAMILIES

    _STRICT_BOOLEAN_FAMILIES = family_mapping_by_name(data.strict_boolean_families)
    _STRICT_FLAG_FAMILIES = family_mapping_by_name(data.strict_flag_families)
    _CONTROLLED_VOCABULARIES = family_mapping_by_name(data.controlled_vocabularies)
    _ONTOLOGY_FAMILIES = family_mapping_by_name(data.ontology_families)
    _REFERENCE_IDENTIFIER_FAMILIES = family_mapping_by_name(
        data.reference_identifier_families
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


def chembl_boolean_family_fields(
    family: str,
    *,
    entity: str | None = None,
) -> frozenset[str]:
    """Return field names governed by one shared strict-boolean family."""
    payload = _STRICT_BOOLEAN_FAMILIES[family]
    return _family_fields(fields=list(payload.fields), entity=entity)


def chembl_flag_family_fields(
    family: str,
    *,
    entity: str | None = None,
) -> frozenset[str]:
    """Return field names governed by one shared strict-flag family."""
    payload = _STRICT_FLAG_FAMILIES[family]
    return _family_fields(fields=list(payload.fields), entity=entity)


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


def chembl_reference_identifier_family_fields(
    family: str,
    *,
    entity: str | None = None,
) -> frozenset[str]:
    """Return field names governed by one shared ChEMBL reference-ID family."""
    payload = _REFERENCE_IDENTIFIER_FAMILIES[family]
    return _family_fields(fields=list(payload.fields), entity=entity)


initialize_chembl_policy_registry(DEFAULT_CHEMBL_POLICY_REGISTRY_DATA)
