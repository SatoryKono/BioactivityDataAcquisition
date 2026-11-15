"""TC-06 family graph and direct layer, using the approved graph limits."""

from __future__ import annotations

import pytest

from iuphar_target_class.hierarchy import (
    LIMIT_EXCEEDED,
    ApprovedMapping,
    FamilyNode,
    build_family_paths,
    graph_limits,
    normalize_provider_class,
    validate_family_graph,
)
from iuphar_target_class.models import ProviderAnnotation
from iuphar_target_class.policy import policy_document

pytestmark = pytest.mark.unit

_ENZYME = "Enzyme"
_RECEPTOR = "Receptor"
_OTHER = "Other Protein Target"


def _node(family_id: str, *parents: str, data: str = "") -> FamilyNode:
    return FamilyNode(family_id, parents, data)


def _chain(length: int) -> tuple[FamilyNode, ...]:
    nodes: list[FamilyNode] = []
    for index in range(length):
        parent = () if index == length - 1 else (f"n{index + 1}",)
        nodes.append(FamilyNode(f"n{index}", parent))
    return tuple(nodes)


def _star(parent_count: int) -> tuple[FamilyNode, ...]:
    parents = tuple(f"p{index}" for index in range(parent_count))
    return (FamilyNode("child", parents), *(FamilyNode(parent) for parent in parents))


def _annotation(
    type_raw: str | None,
    family_ids: tuple[str, ...] = (),
    raw_payload: str | None = None,
) -> ProviderAnnotation:
    return ProviderAnnotation("T1", type_raw, family_ids, None, "human", raw_payload)


def test_approved_graph_limits_are_depth_8_and_visited_128() -> None:
    assert graph_limits() == (8, 128)
    limits = policy_document()["parameters"]["graph_limits"]
    assert limits["keys"] == ["max_depth", "max_visited_nodes"]
    assert limits["max_depth"] == 8
    assert limits["max_visited_nodes"] == 128
    assert policy_document()["direct_mappings"]["families"] == []
    assert policy_document()["direct_mappings"]["types"] == []


def test_depth_at_limit_is_ok_and_one_past_is_graph_error() -> None:
    depth, _visited = graph_limits()
    inside = build_family_paths(_chain(depth), family_ids=("n0",))
    assert inside.defects == ()
    assert len(inside.paths) == 1
    assert len(inside.paths[0].root_to_leaf) == depth
    outside = build_family_paths(_chain(depth + 1), family_ids=("n0",))
    assert outside.paths == ()
    assert len(outside.defects) == 1
    assert outside.defects[0].defect == LIMIT_EXCEEDED
    assert outside.defects[0].limit_key == "max_depth"


def test_visited_at_limit_is_ok_and_one_past_is_graph_error() -> None:
    _depth, visited = graph_limits()
    inside = validate_family_graph(_star(visited - 1), family_ids=("child",))
    assert inside == ()
    outside = build_family_paths(_star(visited), family_ids=("child",))
    assert outside.paths == ()
    assert len(outside.defects) == 1
    assert outside.defects[0].defect == LIMIT_EXCEEDED
    assert outside.defects[0].limit_key == "max_visited_nodes"
    assert (
        max(len(path.root_to_leaf) for path in build_family_paths(_star(1)).paths) == 2
    )


def test_multiple_parents_cycle_self_loop_missing_and_duplicate() -> None:
    linked = build_family_paths(
        (_node("leaf", "left", "right"), _node("left"), _node("right")),
        family_ids=("leaf",),
    )
    assert linked.defects == ()
    assert tuple(path.root_to_leaf for path in linked.paths) == (
        ("left", "leaf"),
        ("right", "leaf"),
    )
    assert linked.paths[0].legacy_leaf_to_root == "leaf → left"
    refused = validate_family_graph(
        (_node("leaf", "left", "right"), _node("left"), _node("right")),
        multiple_parents_allowed=False,
    )
    assert refused[0].defect == "множественные связи"
    cycle = validate_family_graph((_node("a", "b"), _node("b", "a")), family_ids=("a",))
    assert cycle[0].defect == "цикл"
    loop = validate_family_graph((_node("a", "a"),), family_ids=("a",))
    assert loop[0].defect == "самоссылка"
    missing = validate_family_graph((_node("a", "gone"),), family_ids=("a",))
    assert missing[0].defect == "отсутствующий родитель"
    assert missing[0].family_id == "gone"
    duplicate = validate_family_graph(
        (_node("a", data="one"), _node("a", data="two")),
        family_ids=("a",),
    )
    assert duplicate[0].defect == "повторяющийся идентификатор"
    same = validate_family_graph((_node("a", data="one"), _node("a", data="one")))
    assert same == ()


def test_graph_error_keeps_no_class_from_a_partial_hierarchy() -> None:
    _depth, _visited = graph_limits()
    nodes = _chain(_depth + 1)
    mapping = ApprovedMapping(type_to_class=(("GPCR", _RECEPTOR),))
    with_type = normalize_provider_class(_annotation("GPCR", ("n0",)), nodes, mapping)
    assert with_type.iuphar_annotation_status == "partial"
    assert with_type.iuphar_class is None
    assert with_type.iuphar_subclass is None
    assert with_type.iuphar_class_candidates == ()
    assert with_type.diagnostics[0].code == "graph_error"
    assert with_type.diagnostics[0].message == LIMIT_EXCEEDED
    without_type = normalize_provider_class(_annotation(None, ("n0",)), nodes, mapping)
    assert without_type.iuphar_annotation_status == "not_available"
    assert without_type.iuphar_class is None


def test_normalizable_type_uses_the_fixture_mapping() -> None:
    mapping = ApprovedMapping(type_to_class=(("GPCR", _RECEPTOR),))
    result = normalize_provider_class(
        _annotation("GPCR", ("fam",)),
        (_node("fam"),),
        mapping,
    )
    assert result.iuphar_annotation_status == "available"
    assert result.iuphar_class == _RECEPTOR
    assert result.source == "iuphar_normalized"
    assert result.family_candidates == ()


def test_family_mapping_is_partial_and_unmapped_type_stays_unmapped() -> None:
    nodes = (_node("fam", data=_RECEPTOR),)
    mapping = ApprovedMapping(family_to_class=(("fam", _ENZYME),))
    mapped = normalize_provider_class(
        _annotation("not-a-type", ("fam",), raw_payload="Receptor path"),
        nodes,
        mapping,
    )
    assert mapped.iuphar_annotation_status == "partial"
    assert mapped.iuphar_class == _ENZYME
    assert mapped.iuphar_subclass is None
    assert mapped.source == "iuphar_normalized"
    assert mapped.partial_basis == "отображение семейства"
    assert mapped.family_candidates[0].evidence == "отображение семейства"
    unmapped = normalize_provider_class(
        _annotation("GPCR", ("fam",), raw_payload="Receptor"),
        nodes,
        ApprovedMapping(),
    )
    assert unmapped.iuphar_annotation_status == "unmapped_type"
    assert unmapped.iuphar_class is None
    assert unmapped.iuphar_class != _RECEPTOR
    assert unmapped.iuphar_class != _OTHER
    intact = normalize_provider_class(
        _annotation("not-a-type", ("fam",)),
        nodes,
        ApprovedMapping(),
    )
    assert intact.iuphar_annotation_status == "unmapped_type"


def test_same_class_families_are_kept_and_different_classes_conflict() -> None:
    nodes = (_node("fam-a"), _node("fam-b"))
    same = normalize_provider_class(
        _annotation(None, ("fam-a", "fam-b")),
        nodes,
        ApprovedMapping(family_to_class=(("fam-a", _ENZYME), ("fam-b", _ENZYME))),
    )
    assert same.iuphar_annotation_status == "partial"
    assert same.iuphar_class == _ENZYME
    assert same.iuphar_class_candidates == (_ENZYME, _ENZYME)
    assert tuple(item.family_id for item in same.family_candidates) == (
        "fam-a",
        "fam-b",
    )
    conflict = normalize_provider_class(
        _annotation("not-a-type", ("fam-a", "fam-b")),
        nodes,
        ApprovedMapping(family_to_class=(("fam-a", _ENZYME), ("fam-b", _RECEPTOR))),
    )
    assert conflict.iuphar_annotation_status == "conflicting"
    assert conflict.iuphar_class is None
    assert conflict.iuphar_subclass is None
    assert conflict.iuphar_class_candidates == (_ENZYME, _RECEPTOR)
    assert tuple(item.evidence for item in conflict.family_candidates) == (
        "отображение семейства",
        "отображение семейства",
    )


def test_caller_cannot_raise_the_approved_graph_limits() -> None:
    depth, visited = graph_limits()
    raised_depth = build_family_paths(
        _chain(depth + 1),
        family_ids=("n0",),
        max_depth=depth + 1,
    )
    assert raised_depth.paths == ()
    assert raised_depth.defects[0].limit_key == "max_depth"
    stricter = build_family_paths(_chain(2), family_ids=("n0",), max_depth=2)
    assert stricter.defects == ()
    past_stricter = build_family_paths(_chain(3), family_ids=("n0",), max_depth=2)
    assert past_stricter.defects[0].limit_key == "max_depth"
    raised_visited = validate_family_graph(
        _star(visited),
        family_ids=("child",),
        max_visited_nodes=visited + 1,
    )
    assert raised_visited[0].limit_key == "max_visited_nodes"


def test_mapping_outside_the_working_classes_is_rejected() -> None:
    nodes = (_node("fam"),)
    with pytest.raises(ValueError, match="class dictionary"):
        normalize_provider_class(
            _annotation("GPCR", ("fam",)),
            nodes,
            ApprovedMapping(type_to_class=(("GPCR", "typo"),)),
        )
    with pytest.raises(ValueError, match="class dictionary"):
        normalize_provider_class(
            _annotation(None, ("fam",)),
            nodes,
            ApprovedMapping(family_to_class=(("fam", "Oxidoreductases"),)),
        )


def test_unrelated_branch_does_not_cancel_the_selected_family() -> None:
    nodes = (_node("good"), _node("unrelated", "missing"))
    mapping = ApprovedMapping(type_to_class=(("GPCR", _RECEPTOR),))
    result = normalize_provider_class(
        _annotation("GPCR", ("good",)),
        nodes,
        mapping,
    )
    assert result.iuphar_annotation_status == "available"
    assert result.iuphar_class == _RECEPTOR
    assert validate_family_graph(nodes, family_ids=("good",)) == ()
    whole = validate_family_graph(nodes)
    assert whole[0].defect == "отсутствующий родитель"
    reached = validate_family_graph((_node("good", "missing"),), family_ids=("good",))
    assert reached[0].defect == "отсутствующий родитель"
    assert reached[0].family_id == "missing"


def test_dense_ancestor_graph_does_not_block_a_mapped_type() -> None:
    layers = 7
    width = 4
    nodes: list[FamilyNode] = []
    for level in range(layers):
        for index in range(width):
            if level == layers - 1:
                parents: tuple[str, ...] = ()
            else:
                parents = tuple(f"f{level + 1}-{slot}" for slot in range(width))
            nodes.append(FamilyNode(f"f{level}-{index}", parents))
    leaf = "f0-0"
    stored = tuple(nodes)
    assert validate_family_graph(stored, family_ids=(leaf,)) == ()
    result = normalize_provider_class(
        _annotation("GPCR", (leaf,)),
        stored,
        ApprovedMapping(type_to_class=(("GPCR", _RECEPTOR),)),
    )
    assert result.iuphar_annotation_status == "available"
    assert result.iuphar_class == _RECEPTOR
