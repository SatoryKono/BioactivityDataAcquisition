"""Focused tests for structured UniProt comment facet helpers."""

from __future__ import annotations

import pytest

import json

from bioetl.application.pipelines.uniprot.extractors._comment_structured_facets import (
    _extract_alternative_products_family_raw,
    _extract_biophysicochemical_properties_raw,
    _extract_cofactors_raw,
    _extract_reaction_parts_raw,
    _extract_subcellular_locations_raw,
    _serialize_isoform_sections,
)


pytestmark = pytest.mark.unit


def test_extract_alternative_products_family_raw_collects_isoform_outputs() -> None:
    index = {
        "ALTERNATIVE PRODUCTS": [
            {
                "isoforms": [
                    {
                        "name": {"value": "Isoform A"},
                        "isoformIds": ["P12345-1"],
                        "synonyms": [{"value": "Variant 1"}],
                    },
                    "bad",
                ]
            }
        ]
    }

    products, count, sections = _extract_alternative_products_family_raw(index)

    assert count == 2
    assert products == [{"name": "Isoform A", "ids": ["P12345-1"]}]
    assert sections["isoform_names"] == ["Isoform A"]
    assert sections["isoform_ids"] == ["P12345-1"]
    assert sections["isoform_synonyms"] == ["Variant 1"]


def test_extract_reaction_and_subcellular_raw_helpers_filter_invalid_payloads() -> None:
    reaction_index = {
        "CATALYTIC ACTIVITY": [
            {"reaction": {"name": "Reaction A", "ecNumber": "1.1.1.1"}},
            {"reaction": "bad"},
        ]
    }
    location_index = {
        "SUBCELLULAR LOCATION": [
            {
                "subcellularLocations": [
                    {"location": {"value": "Cytoplasm"}},
                    {"location": {}},
                    "bad",
                ]
            }
        ]
    }

    reactions, ec_numbers = _extract_reaction_parts_raw(reaction_index)
    locations = _extract_subcellular_locations_raw(location_index)

    assert reactions == ["Reaction A"]
    assert ec_numbers == ["1.1.1.1"]
    assert locations == ["Cytoplasm"]


def test_extract_cofactors_and_biophys_raw_helpers_keep_supported_sections() -> None:
    cofactor_index = {
        "COFACTOR": [
            {
                "cofactors": [
                    {
                        "name": "Mg(2+)",
                        "cofactorCrossReference": {"id": "CHEBI:18420"},
                        "note": {"texts": [{"value": "Bind 1 magnesium ion."}]},
                    }
                ]
            }
        ]
    }
    biophys_index = {
        "BIOPHYSICOCHEMICAL PROPERTIES": [
            {
                "phDependence": {"texts": [{"value": "Optimum pH is 7.0"}]},
                "kineticParameters": {
                    "michaelisConstants": [
                        {"constant": 0.3, "unit": "mM", "substrate": "ATP"}
                    ]
                },
            }
        ]
    }

    cofactors = _extract_cofactors_raw(cofactor_index)
    biophys = _extract_biophysicochemical_properties_raw(biophys_index)

    assert cofactors == [
        {
            "name": "Mg(2+)",
            "chebi_id": "CHEBI:18420",
            "note": "Bind 1 magnesium ion.",
        }
    ]
    assert biophys["ph_dependence"] == ["Optimum pH is 7.0"]
    assert biophys["kinetic_parameters"]["km"] == [
        {"value": 0.3, "unit": "mM", "substrate": "ATP"}
    ]


def test_serialize_isoform_sections_returns_json_only_for_populated_sections() -> None:
    serialized = _serialize_isoform_sections(
        {
            "isoform_names": ["Isoform A"],
            "isoform_ids": [],
            "isoform_synonyms": ["Variant 1"],
        }
    )

    assert json.loads(serialized["isoform_names"] or "[]") == ["Isoform A"]
    assert serialized["isoform_ids"] is None
    assert json.loads(serialized["isoform_synonyms"] or "[]") == ["Variant 1"]
