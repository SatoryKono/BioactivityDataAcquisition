"""Tests for shared ChEMBL controlled-vocabulary and ontology policy surfaces."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.normalization.profiles._chembl_policy_registry import (
    CHEMBL_CONTROLLED_VOCAB_CONFIG,
    CHEMBL_ONTOLOGY_POLICY_CONFIG,
    PUBLICATION_CLASSIFICATION_CONFIG,
    chembl_controlled_family_fields,
    chembl_ontology_family_fields,
    chembl_policy_surface,
)


def _load_yaml(path: str) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_chembl_policy_surface_points_to_externalized_registry_sources() -> None:
    units = chembl_policy_surface("activity", "units")
    bao_format = chembl_policy_surface("activity", "bao_format")
    publication_class = chembl_policy_surface("publication", "publication_class")

    assert units is not None
    assert units.category == "controlled_vocabulary"
    assert units.registry_source == CHEMBL_CONTROLLED_VOCAB_CONFIG

    assert bao_format is not None
    assert bao_format.category == "ontology_reference_identifier"
    assert bao_format.registry_source == CHEMBL_ONTOLOGY_POLICY_CONFIG

    assert publication_class is not None
    assert publication_class.category == "derived_vocabulary"
    assert publication_class.registry_source == PUBLICATION_CLASSIFICATION_CONFIG


def test_chembl_policy_registry_configs_cover_declared_policy_fields() -> None:
    controlled = _load_yaml(CHEMBL_CONTROLLED_VOCAB_CONFIG)
    ontology = _load_yaml(CHEMBL_ONTOLOGY_POLICY_CONFIG)

    controlled_fields = {
        field
        for policy in controlled["controlled_vocabularies"].values()
        for field in policy["fields"]
    }
    ontology_fields = {
        field
        for policy in ontology["families"].values()
        for field in policy["fields"]
    }

    assert "chembl_activity.units" in controlled_fields
    assert "chembl_assay_parameters.type" in controlled_fields
    assert "chembl_activity.bao_format" in ontology_fields
    assert "chembl_cell_line.cellosaurus_id" in ontology_fields
    assert "chembl_cell_line.clo_id" in ontology_fields


def test_chembl_policy_registry_exposes_profile_authoring_field_sets() -> None:
    assert chembl_controlled_family_fields("units", entity="activity") == frozenset(
        {"units", "qudt_units"}
    )
    assert chembl_controlled_family_fields(
        "units", entity="assay_parameters"
    ) == frozenset({"units", "standard_units"})
    assert chembl_controlled_family_fields(
        "operators", entity="assay_parameters"
    ) == frozenset({"relation"})
    assert chembl_ontology_family_fields("bao", entity="activity") == frozenset(
        {"bao_endpoint", "bao_format"}
    )
    assert chembl_ontology_family_fields("clo", entity="cell_line") == frozenset(
        {"clo_id"}
    )


def test_chembl_policy_surface_returns_none_for_ungoverned_free_text_fields() -> None:
    assert chembl_policy_surface("target", "organism") is None
