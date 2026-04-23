"""Shared ChEMBL semantic policy surfaces beyond strict enums."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

__all__ = [
    "CHEMBL_CONTROLLED_VOCAB_CONFIG",
    "CHEMBL_ONTOLOGY_POLICY_CONFIG",
    "PUBLICATION_CLASSIFICATION_CONFIG",
    "ChemblPolicySurface",
    "chembl_controlled_family_fields",
    "chembl_ontology_family_fields",
    "chembl_policy_surface",
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _load_yaml_config(relative_path: str) -> Mapping[str, Any]:
    payload = yaml.safe_load((_repo_root() / relative_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{relative_path} must decode to a mapping; got {type(payload)!r}")
    return payload


def _parse_chembl_field_ref(field_ref: str) -> tuple[str, str]:
    pipeline_name, field_name = field_ref.split(".", maxsplit=1)
    if not pipeline_name.startswith("chembl_"):
        raise ValueError(
            "Expected ChEMBL field ref in '<pipeline_name>.<field>' form with "
            f"'chembl_' prefix; got {field_ref!r}"
        )
    return pipeline_name.removeprefix("chembl_"), field_name


@cache
def _controlled_vocab_registry() -> Mapping[str, Any]:
    return _load_yaml_config(CHEMBL_CONTROLLED_VOCAB_CONFIG)


@cache
def _ontology_registry() -> Mapping[str, Any]:
    return _load_yaml_config(CHEMBL_ONTOLOGY_POLICY_CONFIG)


@cache
def _chembl_policy_surfaces() -> Mapping[tuple[str, str], ChemblPolicySurface]:
    surfaces: dict[tuple[str, str], ChemblPolicySurface] = {}

    controlled_vocabularies = _controlled_vocab_registry()["controlled_vocabularies"]
    for payload in controlled_vocabularies.values():
        invalid_value_mode = str(payload["invalid_value_mode"])
        for field_ref in payload["fields"]:
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category="controlled_vocabulary",
                registry_source=CHEMBL_CONTROLLED_VOCAB_CONFIG,
                invalid_value_mode=invalid_value_mode,
            )

    ontology_families = _ontology_registry()["families"]
    for payload in ontology_families.values():
        for field_ref in payload["fields"]:
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category="ontology_reference_identifier",
                registry_source=CHEMBL_ONTOLOGY_POLICY_CONFIG,
                invalid_value_mode="preserve_unknown_lexeme",
            )
        for field_ref in payload.get("code_label_fields", ()):
            entity, field_name = _parse_chembl_field_ref(str(field_ref))
            surfaces[(entity, field_name)] = ChemblPolicySurface(
                category="derived_vocabulary",
                registry_source=CHEMBL_ONTOLOGY_POLICY_CONFIG,
                invalid_value_mode="resolve_identifier_backed_label",
            )

    for field_name in (
        "publication_type_unified",
        "publication_subclass",
        "publication_class",
    ):
        surfaces[("publication", field_name)] = ChemblPolicySurface(
            category="derived_vocabulary",
            registry_source=PUBLICATION_CLASSIFICATION_CONFIG,
            invalid_value_mode="reject_unknown_taxonomy_value",
        )

    return surfaces


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
    return _chembl_policy_surfaces().get((entity, field))


@cache
def chembl_controlled_family_fields(
    family: str,
    *,
    entity: str | None = None,
) -> frozenset[str]:
    """Return field names governed by one shared controlled-vocabulary family."""
    controlled_vocabularies = _controlled_vocab_registry()["controlled_vocabularies"]
    payload = controlled_vocabularies[family]
    return _family_fields(fields=list(payload["fields"]), entity=entity)


@cache
def chembl_ontology_family_fields(
    family: str,
    *,
    entity: str | None = None,
    include_code_label_fields: bool = False,
) -> frozenset[str]:
    """Return field names governed by one shared ontology/reference-ID family."""
    families = _ontology_registry()["families"]
    payload = families[family]
    fields = list(payload["fields"])
    if include_code_label_fields:
        fields.extend(payload.get("code_label_fields", ()))
    return _family_fields(fields=fields, entity=entity)
