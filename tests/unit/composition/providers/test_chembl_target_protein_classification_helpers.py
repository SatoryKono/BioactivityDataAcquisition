"""Unit tests for ChEMBL target protein-classification helper functions."""

from __future__ import annotations

import json

import pytest

from bioetl.composition.providers import (
    _chembl_target_protein_classification_helpers as helpers,
)
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassificationResolutionError,
)


pytestmark = pytest.mark.unit


def test_target_and_component_helpers_normalize_mixed_payloads() -> None:
    assert helpers.target_id_from_record({"target_id": " CHEMBL1 "}) == "CHEMBL1"
    assert helpers.target_id_from_record({"target_chembl_id": " CHEMBL2 "}) == "CHEMBL2"
    assert helpers.target_id_from_record({"target_id": " "}) is None

    component_ids = helpers.component_ids_from_target_record(
        {
            "target_components": '[{"component_id": "10"}, {"component_id": 11}]',
            "component_ids": '[11, 12.0, 0, false, "bad"]',
            "primary_component_id": "13",
        }
    )
    assert component_ids == (10, 11, 12, 13)

    target_ids = helpers.target_ids_from_component_record(
        {
            "targets": [
                {"target_id": "CHEMBL1"},
                {"target_chembl_id": " CHEMBL2 "},
                {"target_id": "CHEMBL1"},
                "not-a-target",
            ]
        }
    )
    assert target_ids == ("CHEMBL1", "CHEMBL2")


def test_leaf_id_helpers_accept_json_objects_and_reject_bad_json() -> None:
    assert helpers.leaf_ids_from_value('[1, "2", 2, 3.0, 3.5, 0, false]') == (
        1,
        2,
        3,
    )
    assert helpers.leaf_ids_from_value("  ") == ()
    assert helpers.leaf_ids_from_value({"not": "iterable-leaves"}) == ()
    assert helpers.leaf_ids_from_classification_objects(
        [
            {"protein_classification_id": "4"},
            {"protein_class_id": 5.0},
            {"leaf_id": "6"},
            {"leaf_id": "6"},
            {"leaf_id": 0},
            "not-a-mapping",
        ]
    ) == (4, 5, 6)
    assert helpers.leaf_ids_from_component_row(
        {"protein_classifications": [{"protein_classification_id": "7"}]}
    ) == (7,)

    with pytest.raises(ProteinClassificationResolutionError):
        helpers.leaf_ids_from_value("[bad")
    with pytest.raises(ProteinClassificationResolutionError):
        helpers.component_ids_from_target_record({"component_ids": "[bad"})


def test_scalar_helpers_and_canonical_json_are_deterministic() -> None:
    assert helpers.coerce_positive_int(None) is None
    assert helpers.coerce_positive_int(True) is None
    assert helpers.coerce_positive_int(0) is None
    assert helpers.coerce_positive_int(2.5) is None
    assert helpers.coerce_positive_int(" 42 ") == 42
    assert helpers.coerce_positive_int("not-int") is None
    assert helpers.coerce_text(123) == "123"
    assert helpers.coerce_text("  ") is None
    assert helpers.canonical_json({"b": 2, "a": [1]}) == json.dumps(
        {"a": [1], "b": 2},
        sort_keys=True,
        separators=(",", ":"),
    )
