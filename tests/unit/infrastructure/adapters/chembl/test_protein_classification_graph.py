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


def test_graph_keeps_full_path_when_hierarchy_exceeds_legacy_l5_projection() -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=[
            {
                "protein_class_id": level,
                "parent_id": level - 1 if level > 1 else None,
                "class_level": level,
                "pref_name": f"Level {level}",
            }
            for level in range(1, 8)
        ],
        target_component_rows=[
            {
                "component_id": 111,
                "protein_classification_ids": "[7]",
            }
        ],
    )

    hierarchy = graph.get_component_classifications(111)[0]

    assert hierarchy.level_ids == (1, 2, 3, 4, 5)
    assert hierarchy.path_ids == (1, 2, 3, 4, 5, 6, 7)
    assert hierarchy.path_names == (
        "Level 1",
        "Level 2",
        "Level 3",
        "Level 4",
        "Level 5",
        "Level 6",
        "Level 7",
    )
    assert hierarchy.depth == 6
    assert hierarchy.root_id == 1


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


def test_graph_returns_cached_hierarchy_for_same_leaf() -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=[
            {"protein_class_id": 1, "class_level": 1, "pref_name": "Root"},
            {"protein_class_id": 2, "parent_id": 1, "class_level": 2},
        ],
        target_component_rows=[
            {"component_id": 303, "protein_classification_ids": "[2]"}
        ],
    )

    first = graph.get_component_classifications(303)[0]
    second = graph.get_component_classifications(303)[0]

    assert first is second


def test_graph_rejects_non_positive_component_id() -> None:
    graph = ChEMBLProteinClassificationGraph(nodes={}, component_leaf_ids={})

    with pytest.raises(
        ProteinClassificationResolutionError,
        match="component_id must be positive",
    ):
        graph.get_component_classifications(0)


def test_graph_detects_replacement_cycle() -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=[
            {"protein_class_id": 1, "class_level": 1, "replaced_by": 2},
            {"protein_class_id": 2, "class_level": 1, "replaced_by": 1},
        ],
        target_component_rows=[
            {"component_id": 404, "protein_classification_ids": "[1]"}
        ],
    )

    with pytest.raises(ProteinClassificationResolutionError, match="replaced_by cycle"):
        graph.get_component_classifications(404)


def test_graph_ignores_invalid_node_rows_and_non_list_forensic_payloads() -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=[
            {"protein_class_id": 0, "class_level": 1},
            {"protein_class_id": True, "class_level": 1},
            {"protein_class_id": "9", "class_level": 1, "pref_name": "Valid"},
        ],
        target_component_rows=[
            {
                "component_id": 505,
                "protein_classification_ids": "[]",
                "protein_classifications": '{"protein_classification_id": 9}',
            }
        ],
    )

    assert graph.get_component_classifications(505) == ()


@pytest.mark.parametrize(
    ("field_name", "value", "message"),
    [
        (
            "protein_classification_ids",
            "{bad json",
            "protein_classification_ids must be canonical JSON",
        ),
        (
            "protein_classifications",
            "{bad json",
            "protein_classifications must be canonical JSON",
        ),
    ],
)
def test_graph_rejects_malformed_json_payloads(
    field_name: str,
    value: object,
    message: str,
) -> None:
    target_row: dict[str, object] = {"component_id": 606}
    target_row[field_name] = value
    if field_name != "protein_classification_ids":
        target_row["protein_classification_ids"] = "[]"

    with pytest.raises(ProteinClassificationResolutionError, match=message):
        ChEMBLProteinClassificationGraph.from_rows(
            protein_class_rows=[],
            target_component_rows=[target_row],
        )


@pytest.mark.parametrize(
    ("protein_class_rows", "leaf_ids", "message"),
    [
        (
            [{"protein_class_id": 8, "class_level": None}],
            "[8]",
            "missing class_level",
        ),
        (
            [{"protein_class_id": 8, "class_level": 11}],
            "[8]",
            "exceeds supported provider range",
        ),
        (
            [
                {"protein_class_id": 1, "class_level": 1},
                {"protein_class_id": 3, "class_level": 3, "parent_id": 1},
            ],
            "[3]",
            "broken protein classification chain",
        ),
    ],
)
def test_graph_rejects_additional_invalid_level_shapes(
    protein_class_rows: list[dict[str, object]],
    leaf_ids: str,
    message: str,
) -> None:
    graph = ChEMBLProteinClassificationGraph.from_rows(
        protein_class_rows=protein_class_rows,
        target_component_rows=[
            {"component_id": 707, "protein_classification_ids": leaf_ids}
        ],
    )

    with pytest.raises(ProteinClassificationResolutionError, match=message):
        graph.get_component_classifications(707)


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
