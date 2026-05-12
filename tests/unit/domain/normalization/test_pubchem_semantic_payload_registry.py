"""Governance checks for PubChem semantic payload registry."""

from __future__ import annotations

from pathlib import Path

import yaml

_REGISTRY = yaml.safe_load(
    Path("configs/vocab/pubchem_semantic_payloads.yaml").read_text(encoding="utf-8")
)["compound"]
_EXPECTED_PROPERTY_VOCAB = yaml.safe_load(
    Path("tests/fixtures/normalization/pubchem_property_vocab_expected.yaml").read_text(
        encoding="utf-8"
    )
)
_PIPELINE_CONFIG = yaml.safe_load(
    Path("configs/entities/pubchem/compound.yaml").read_text(encoding="utf-8")
)
_BUSINESS_FIELDS = set(_PIPELINE_CONFIG["schema"]["column_groups"][1]["fields"])


def test_pubchem_semantic_registry_declares_pipeline_semantic_field_groups() -> None:
    assert set(_REGISTRY["scalar_identifier_fields"]) <= _BUSINESS_FIELDS


def test_pubchem_semantic_registry_tracks_iupac_and_smiles_variant_terms() -> None:
    names = set(_EXPECTED_PROPERTY_VOCAB["name"])

    assert set(_REGISTRY["iupac_name_variants"]) <= names
    assert set(_REGISTRY["smiles_name_variants"]) <= names


def test_pubchem_semantic_registry_tracks_property_urn_axes() -> None:
    assert set(_REGISTRY["property_urn_axes"]) == set(_EXPECTED_PROPERTY_VOCAB)
