"""Tests for ChEMBL activity ontology companion field resolution."""

from __future__ import annotations

from bioetl.domain.normalization.chembl import (
    resolve_activity_ontology_companion_fields,
)


def test_resolve_activity_ontology_companion_fields_maps_known_tokens() -> None:
    companions = resolve_activity_ontology_companion_fields(
        bao_endpoint="bao:0000190",
        bao_format="BAO_0000218",
        uo_units="uo:0000065",
        qudt_units="nanomolar",
    )

    assert companions.bao_endpoint_iri == (
        "http://purl.obolibrary.org/obo/BAO_0000190"
    )
    assert companions.bao_endpoint_mapping_status == "mapped"
    assert companions.bao_format_iri == "http://purl.obolibrary.org/obo/BAO_0000218"
    assert companions.bao_format_mapping_status == "mapped"
    assert companions.bao_ontology_version == "2.8.18a"
    assert companions.uo_unit_iri == "http://purl.obolibrary.org/obo/UO_0000065"
    assert companions.uo_unit_mapping_status == "mapped"
    assert companions.uo_ontology_version == "2026-01-16"
    assert companions.qudt_unit_iri == "http://qudt.org/vocab/unit/NanoMOL-PER-L"
    assert companions.qudt_unit_mapping_status == "mapped"
    assert companions.qudt_ontology_version == "3.2.1"


def test_resolve_activity_ontology_companion_fields_maps_legacy_qudt_uri() -> None:
    companions = resolve_activity_ontology_companion_fields(
        bao_endpoint=None,
        bao_format=None,
        uo_units=None,
        qudt_units="http://www.openphacts.org/units/Nanomolar",
    )

    assert companions.bao_endpoint_mapping_status == "missing"
    assert companions.bao_format_mapping_status == "missing"
    assert companions.bao_ontology_version is None
    assert companions.uo_unit_mapping_status == "missing"
    assert companions.uo_ontology_version is None
    assert companions.qudt_unit_iri == "http://qudt.org/vocab/unit/NanoMOL-PER-L"
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
