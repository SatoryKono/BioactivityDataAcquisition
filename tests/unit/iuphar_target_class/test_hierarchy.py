"""TC-06 family graph, limits, and direct-layer mapping."""

from __future__ import annotations

import pytest

from iuphar_target_class.hierarchy import (
    FamilyNode,
    normalize_provider_class,
    validate_family_graph,
)
from iuphar_target_class.policy import GRAPH_MAX_DEPTH, GRAPH_MAX_VISITED_NODES

pytestmark = pytest.mark.unit


def _chain(edges: int) -> tuple[FamilyNode, ...]:
    nodes: list[FamilyNode] = []
    for index in range(edges + 1):
        parents = () if index == edges else (str(index + 1),)
        nodes.append(FamilyNode(str(index), parents, str(index)))
    return tuple(nodes)


def test_family_mapping_is_partial_and_unmapped_type_is_not_replaced() -> None:
    nodes = (FamilyNode("900", (), "900"),)
    mapped = normalize_provider_class(
        type_name="not-a-type",
        family_ids=("900",),
        nodes=nodes,
        type_to_class={},
        family_to_class={"900": "Receptor"},
        name="Voltage-gated ion channel",
        path_text="Ion Channel / foo",
    )
    assert mapped.annotation_status == "partial"
    assert mapped.proof == "отображение семейства"
    assert mapped.source == "iuphar_normalized"
    assert mapped.iuphar_class == "Receptor"
    assert mapped.paths[0].root_to_leaf == ("900",)
    assert mapped.paths[0].leaf_to_root == "900"
    unmapped = normalize_provider_class(
        type_name="GPCR",
        family_ids=("900",),
        nodes=nodes,
        type_to_class={},
        family_to_class={},
        name="Voltage-gated ion channel",
        path_text="Ion Channel / foo",
    )
    assert unmapped.annotation_status == "unmapped_type"
    assert unmapped.iuphar_class is None
    assert unmapped.iuphar_class != "Other Protein Target"


def test_gpcr_is_covered_by_the_type_mapping() -> None:
    result = normalize_provider_class(
        type_name="GPCR",
        family_ids=("1",),
        nodes=(FamilyNode("1", (), "1"),),
        type_to_class={"GPCR": "Receptor"},
        family_to_class={},
    )
    assert result.annotation_status == "available"
    assert result.iuphar_class == "Receptor"
    assert result.source == "iuphar_normalized"


def test_same_class_families_stay_and_different_classes_conflict() -> None:
    nodes = (
        FamilyNode("1", (), "1"),
        FamilyNode("2", (), "2"),
    )
    same = normalize_provider_class(
        type_name=None,
        family_ids=("1", "2"),
        nodes=nodes,
        type_to_class={},
        family_to_class={"1": "Enzyme", "2": "Enzyme"},
    )
    assert same.annotation_status == "partial"
    assert same.iuphar_class == "Enzyme"
    assert same.iuphar_class_candidates == ("Enzyme", "Enzyme")
    conflict = normalize_provider_class(
        type_name=None,
        family_ids=("1", "2"),
        nodes=nodes,
        type_to_class={},
        family_to_class={"1": "Enzyme", "2": "Transporter"},
    )
    assert conflict.annotation_status == "conflicting"
    assert conflict.iuphar_class is None
    assert conflict.iuphar_subclass is None
    assert conflict.iuphar_class_candidates == ("Enzyme", "Transporter")
    assert conflict.family_evidence == (("1", "Enzyme"), ("2", "Transporter"))


def test_cycle_self_loop_and_missing_parent_stop() -> None:
    cycle = validate_family_graph(
        (FamilyNode("a", ("b",), "a"), FamilyNode("b", ("a",), "b")),
        ("a",),
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=GRAPH_MAX_VISITED_NODES,
    )
    assert cycle is not None
    assert cycle.code == "graph_error"
    assert cycle.message == "цикл"
    loop = validate_family_graph(
        (FamilyNode("a", ("a",), "a"),),
        ("a",),
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=GRAPH_MAX_VISITED_NODES,
    )
    assert loop is not None
    assert loop.message == "self-loop"
    missing = validate_family_graph(
        (FamilyNode("a", ("gone",), "a"),),
        ("a",),
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=GRAPH_MAX_VISITED_NODES,
    )
    assert missing is not None
    assert missing.message == "отсутствующий родитель"


def test_duplicate_family_payloads_are_rejected() -> None:
    defect = validate_family_graph(
        (FamilyNode("a", (), "one"), FamilyNode("a", (), "two")),
        ("a",),
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=GRAPH_MAX_VISITED_NODES,
    )
    assert defect is not None
    assert defect.message == "повторяющийся идентификатор"


def test_same_payload_with_different_parents_is_order_independent() -> None:
    records = (
        (FamilyNode("leaf", (), "same"), FamilyNode("leaf", ("gone",), "same")),
        (FamilyNode("leaf", ("gone",), "same"), FamilyNode("leaf", (), "same")),
    )
    for nodes in records:
        result = normalize_provider_class(
            type_name=None,
            family_ids=("leaf",),
            nodes=nodes,
            type_to_class={},
            family_to_class={"leaf": "Enzyme"},
        )
        assert result.diagnostics[0].message == "повторяющийся идентификатор"
        assert result.iuphar_class is None
        assert result.paths == ()


def test_shared_ancestors_stop_at_the_visit_budget() -> None:
    nodes = (
        FamilyNode("leaf", ("a", "b"), "leaf"),
        FamilyNode("a", ("root",), "a"),
        FamilyNode("b", ("root",), "b"),
        FamilyNode("root", (), "root"),
    )
    result = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
        max_depth=8,
        max_visited_nodes=4,
    )
    assert result.diagnostics[0].message == "превышение лимита"
    assert result.iuphar_class is None
    assert result.annotation_status == "not_available"
    assert result.paths == ()


def test_depth_limit_and_one_past_it() -> None:
    at_limit = validate_family_graph(
        _chain(GRAPH_MAX_DEPTH),
        ("0",),
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=10_000,
    )
    assert at_limit is None
    past = normalize_provider_class(
        type_name=None,
        family_ids=("0",),
        nodes=_chain(GRAPH_MAX_DEPTH + 1),
        type_to_class={},
        family_to_class={"0": "Receptor"},
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=10_000,
    )
    assert past.diagnostics[0].message == "превышение лимита"
    assert past.iuphar_class is None
    assert past.annotation_status == "not_available"
    assert past.paths == ()


def test_visited_node_limit_and_one_past_it() -> None:
    at_limit = validate_family_graph(
        _chain(GRAPH_MAX_VISITED_NODES - 1),
        ("0",),
        max_depth=10_000,
        max_visited_nodes=GRAPH_MAX_VISITED_NODES,
    )
    assert at_limit is None
    past = normalize_provider_class(
        type_name="gpcr",
        family_ids=("0",),
        nodes=_chain(GRAPH_MAX_VISITED_NODES),
        type_to_class={"gpcr": "Ion Channel"},
        family_to_class={"0": "Receptor"},
        max_depth=10_000,
        max_visited_nodes=GRAPH_MAX_VISITED_NODES,
    )
    assert past.diagnostics[0].message == "превышение лимита"
    assert past.annotation_status == "partial"
    assert past.iuphar_class == "Ion Channel"
    assert "Receptor" not in past.iuphar_class_candidates


def test_root_to_leaf_path_keeps_the_migration_string() -> None:
    nodes = (
        FamilyNode("leaf", ("mid",), "leaf"),
        FamilyNode("mid", ("root",), "mid"),
        FamilyNode("root", (), "root"),
    )
    result = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={},
        family_to_class={"leaf": "Transporter"},
    )
    assert result.paths[0].root_to_leaf == ("root", "mid", "leaf")
    assert result.paths[0].leaf_to_root == "leaf → mid → root"


def test_two_parents_make_two_paths_when_the_schema_allows_them() -> None:
    nodes = (
        FamilyNode("leaf", ("left", "right"), "leaf"),
        FamilyNode("left", (), "left"),
        FamilyNode("right", (), "right"),
    )
    allowed = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
    )
    assert [item.root_to_leaf for item in allowed.paths] == [
        ("left", "leaf"),
        ("right", "leaf"),
    ]
    blocked = validate_family_graph(
        nodes,
        ("leaf",),
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=GRAPH_MAX_VISITED_NODES,
        multiple_parents_allowed=False,
    )
    assert blocked is not None
    assert blocked.message == "множественные родители"
