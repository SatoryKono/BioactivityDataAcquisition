"""Snapshot classification filters reject ambiguity and preserve stable indexes."""

from __future__ import annotations
import pytest
from bioetl.domain.chembl.target_protein_classification import (
    build_target_component_indexes,
    resolve_target_ids,
    leaf_ids_from_value,
)
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassificationResolutionError,
)


pytestmark = pytest.mark.unit


def test_component_filter_resolves_all_linked_targets_in_stable_order():
    targets, components = build_target_component_indexes(
        [
            {"target_id": "T2", "component_ids": [3, 3, 0, True]},
            {"target_chembl_id": "T1", "primary_component_id": 3},
            {"target_id": "T3", "component_ids": [4]},
        ]
    )
    assert targets == {"T1": (3,), "T2": (3,), "T3": (4,)}
    assert resolve_target_ids(
        filter_ids=["3", "invalid"],
        filter_field="component_id",
        target_component_ids=targets,
        target_ids_by_component=components,
    ) == ("T1", "T2")
    with pytest.raises(ValueError, match="Unsupported"):
        resolve_target_ids(
            filter_ids=["3"],
            filter_field="unknown",
            target_component_ids=targets,
            target_ids_by_component=components,
        )


def test_leaf_json_must_be_canonical_and_positive():
    assert leaf_ids_from_value('[3, 3, 0, -1, true, "4"]') == (3, 4)
    with pytest.raises(ProteinClassificationResolutionError, match="canonical JSON"):
        leaf_ids_from_value("not JSON")
