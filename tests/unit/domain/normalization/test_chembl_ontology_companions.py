"""Tests for ChEMBL activity ontology companion field resolution."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.chembl import (
    resolve_activity_ontology_companion_fields,
    resolve_obo_ontology_companion_field,
)

pytestmark = pytest.mark.unit

LEGACY_QUDT_UNIT_URI = "http" + "://www.openphacts.org/units/Nanomolar"
EXPECTED_BAO_ENDPOINT_IRI = "https://purl.obolibrary.org/obo/BAO_0000190"
EXPECTED_BAO_FORMAT_IRI = "https://purl.obolibrary.org/obo/BAO_0000218"
EXPECTED_UO_UNIT_IRI = "https://purl.obolibrary.org/obo/UO_0000065"
EXPECTED_QUDT_UNIT_IRI = "https://qudt.org/vocab/unit/NanoMOL-PER-L"


def test_resolve_activity_ontology_companion_fields_maps_known_tokens() -> None:
    companions = resolve_activity_ontology_companion_fields(
        bao_endpoint="bao:0000190",
        bao_format="BAO_0000218",
        uo_units="uo:0000065",
        qudt_units="nanomolar",
    )

    assert companions.bao_endpoint_iri == EXPECTED_BAO_ENDPOINT_IRI
    assert companions.bao_endpoint_mapping_status == "mapped"
    assert companions.bao_format_iri == EXPECTED_BAO_FORMAT_IRI
    assert companions.bao_format_mapping_status == "mapped"
    assert companions.bao_ontology_version == "2.8.18a"
    assert companions.uo_unit_iri == EXPECTED_UO_UNIT_IRI
    assert companions.uo_unit_mapping_status == "mapped"
    assert companions.uo_ontology_version == "2026-01-16"
    assert companions.qudt_unit_iri == EXPECTED_QUDT_UNIT_IRI
    assert companions.qudt_unit_mapping_status == "mapped"
    assert companions.qudt_ontology_version == "3.2.1"


def test_resolve_activity_ontology_companion_fields_maps_legacy_qudt_uri() -> None:
    companions = resolve_activity_ontology_companion_fields(
        bao_endpoint=None,
        bao_format=None,
        uo_units=None,
        qudt_units=LEGACY_QUDT_UNIT_URI,
    )

    assert companions.bao_endpoint_mapping_status == "missing"
    assert companions.bao_format_mapping_status == "missing"
    assert companions.bao_ontology_version is None
    assert companions.uo_unit_mapping_status == "missing"
    assert companions.uo_ontology_version is None
    assert companions.qudt_unit_iri == EXPECTED_QUDT_UNIT_IRI
    assert companions.qudt_unit_mapping_status == "mapped"
    assert companions.qudt_ontology_version == "3.2.1"


def test_resolve_activity_ontology_companion_fields_preserves_unmapped_status() -> None:
    companions = resolve_activity_ontology_companion_fields(
        bao_endpoint="not-bao",
        bao_format="still-not-bao",
        uo_units="relative potency",
        qudt_units="unknown-unit",
    )

    assert companions.bao_endpoint_iri is None
    assert companions.bao_endpoint_mapping_status == "unmapped"
    assert companions.bao_format_iri is None
    assert companions.bao_format_mapping_status == "unmapped"
    assert companions.bao_ontology_version == "2.8.18a"
    assert companions.uo_unit_iri is None
    assert companions.uo_unit_mapping_status == "unmapped"
    assert companions.uo_ontology_version == "2026-01-16"
    assert companions.qudt_unit_iri is None
    assert companions.qudt_unit_mapping_status == "unmapped"
    assert companions.qudt_ontology_version == "3.2.1"


def test_resolve_obo_ontology_companion_field_maps_colon_form() -> None:
    result = resolve_obo_ontology_companion_field(
        "bto:0000068",
        canonical_prefix="BTO_",
        ontology_version="2026-01-16",
    )

    assert result.iri == "https://purl.obolibrary.org/obo/BTO_0000068"
    assert result.status == "mapped"
    assert result.ontology_version == "2026-01-16"


def test_resolve_obo_ontology_companion_field_classifies_missing_and_unmapped() -> None:
    missing = resolve_obo_ontology_companion_field(
        None,
        canonical_prefix="EFO_",
        ontology_version="2026-01-16",
    )
    unmapped = resolve_obo_ontology_companion_field(
        "not-efo",
        canonical_prefix="EFO_",
        ontology_version="2026-01-16",
    )

    assert missing.iri is None
    assert missing.status == "missing"
    assert missing.ontology_version is None
    assert unmapped.iri is None
    assert unmapped.status == "unmapped"
    assert unmapped.ontology_version == "2026-01-16"
