"""Tests for the ChEMBL protein classification graph adapter."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassificationResolutionError,
)
from bioetl.infrastructure.adapters.chembl.protein_classification_graph import (
    ChEMBLProteinClassificationGraph,
)


pytestmark = pytest.mark.unit


def test_graph_treats_chembl_root_parent_zero_as_absent_parent() -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=[
            {
                "protein_class_id": 1,
                "parent_id": 0,
                "class_level": 1,
                "pref_name": "Enzyme",
                "protein_class_desc": "Root",
            },
            {
                "protein_class_id": 646,
                "parent_id": 1,
                "class_level": 2,
                "pref_name": "Hydrolase",
                "protein_class_desc": "enzyme hydrolase",
            },
        ],
        target_component_rows=[
            {
                "component_id": 434,
                "protein_classification_ids": "[646]",
            }
        ],
    )

    hierarchies = graph.get_component_classifications(434)

    assert len(hierarchies) == 1
    assert hierarchies[0].leaf_id == 646
    assert hierarchies[0].level_ids == (1, 646, None, None, None)


def test_graph_resolves_multiple_classifications_with_replaced_by_redirect() -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=[
            {
                "protein_class_id": 1,
                "class_level": 1,
                "pref_name": "Enzyme",
                "protein_class_desc": "Root",
            },
            {
                "protein_class_id": 2,
                "parent_id": 1,
                "class_level": 2,
                "pref_name": "Kinase",
            },
            {
                "protein_class_id": 3,
                "parent_id": 2,
                "class_level": 3,
                "pref_name": "Protein kinase",
            },
            {
                "protein_class_id": 99,
                "class_level": 3,
                "replaced_by": 3,
            },
            {
                "protein_class_id": 10,
                "class_level": 1,
                "pref_name": "Membrane receptor",
            },
        ],
        target_component_rows=[
            {
                "component_id": 101,
                "protein_classification_ids": "[99,10,99]",
            }
        ],
    )

    hierarchies = graph.get_component_classifications(101)

    assert [hierarchy.leaf_id for hierarchy in hierarchies] == [3, 10]
    assert hierarchies[0].level_ids == (1, 2, 3, None, None)
    assert hierarchies[0].l1.name == "Enzyme"
    assert hierarchies[1].level_ids == (10, None, None, None, None)


def test_graph_uses_forensic_classifications_when_flat_ids_are_missing() -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=[
            {
                "protein_class_id": 7,
                "class_level": 1,
                "pref_name": "Transporter",
            },
        ],
        target_component_rows=[
            {
                "component_id": 202,
                "protein_classifications": (
                    '[{"protein_classification_id": 7},'
                    '{"protein_classification_id": 7}]'
                ),
            }
        ],
    )

    assert [item.leaf_id for item in graph.get_component_classifications(202)] == [7]


@pytest.mark.parametrize(
    "protein_class_rows, leaf_ids, message",
    [
        (
            [
                {"protein_class_id": 1, "class_level": 1, "parent_id": 2},
                {"protein_class_id": 2, "class_level": 2, "parent_id": 1},
            ],
            "[1]",
            "parent cycle",
        ),
        (
            [{"protein_class_id": 4, "class_level": 4, "parent_id": 2}],
            "[4]",
            "missing protein classification node 2",
        ),
        (
            [{"protein_class_id": 5, "class_level": 0}],
            "[5]",
            "class_level must be >= 1",
        ),
    ],
)
def test_graph_quarantines_invalid_hierarchy_shapes(
    protein_class_rows: list[dict[str, object]],
    leaf_ids: str,
    message: str,
) -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=protein_class_rows,
        target_component_rows=[
            {"component_id": 303, "protein_classification_ids": leaf_ids}
        ],
    )

    with pytest.raises(ProteinClassificationResolutionError, match=message):
        graph.get_component_classifications(303)
