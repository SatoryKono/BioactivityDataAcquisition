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


@pytest.mark.parametrize("kind", ["type", "family"])
@pytest.mark.parametrize("foreign", ["Oxidoreductases", "typo", ""])
def test_fixture_mapping_rejects_foreign_classes(kind: str, foreign: str) -> None:
    with pytest.raises(ValueError, match="outside the class dictionary"):
        ApprovedMapping(
            type_to_class=(("GPCR", foreign),) if kind == "type" else (),
            family_to_class=(("fam", foreign),) if kind == "family" else (),
        )


@pytest.mark.parametrize(
    "unrelated",
    [
        (_node("other", "missing"),),
        (_node("other", "other"),),
        (_node("other", data="a"), _node("other", data="b")),
        (_node("other", "second"), _node("second", "other")),
    ],
)
def test_unrelated_defect_does_not_change_this_targets_class(
    unrelated: tuple[FamilyNode, ...],
) -> None:
    nodes = (_node("leaf", "root"), _node("root"), *unrelated)
    result = normalize_provider_class(
        _annotation("GPCR", ("leaf",)),
        nodes,
        ApprovedMapping(type_to_class=(("GPCR", _RECEPTOR),)),
    )
    assert result.iuphar_annotation_status == "available"
    assert result.iuphar_class == _RECEPTOR
    assert result.defects == ()
    assert validate_family_graph(nodes)


def test_reachable_duplicate_is_not_hidden_by_target_filtering() -> None:
    result = build_family_paths(
        (_node("leaf", "root"), _node("leaf"), _node("root")),
        family_ids=("leaf",),
    )
    assert result.paths == ()
    assert result.defects[0].defect == "повторяющийся идентификатор"


def test_overrides_cannot_increase_approved_limits() -> None:
    depth = build_family_paths(_chain(9), family_ids=("n0",), max_depth=9)
    visited = build_family_paths(
        _star(128), family_ids=("child",), max_visited_nodes=129
    )
    assert depth.paths == visited.paths == ()
    assert depth.defects[0].limit_key == "max_depth"
    assert visited.defects[0].limit_key == "max_visited_nodes"
    assert build_family_paths(_chain(3), family_ids=("n0",), max_depth=2).defects


def test_no_family_ids_do_not_validate_other_targets() -> None:
    result = normalize_provider_class(
        _annotation("GPCR"),
        (_node("other", "missing"),),
        ApprovedMapping(type_to_class=(("GPCR", _RECEPTOR),)),
    )
    assert result.iuphar_class == _RECEPTOR
    assert result.defects == ()


def _layered_graph(width: int, layers: int) -> tuple[FamilyNode, ...]:
    nodes: list[FamilyNode] = []
    for level in range(layers):
        parents = (
            tuple(f"l{level + 1}n{i}" for i in range(width))
            if level + 1 < layers
            else ()
        )
        nodes.extend(FamilyNode(f"l{level}n{i}", parents) for i in range(width))
    return (FamilyNode("leaf", tuple(f"l0n{i}" for i in range(width))), *nodes)


def test_valid_exponential_graph_keeps_paths_lazy_without_new_limits() -> None:
    import tracemalloc

    nodes = _layered_graph(8, 7)
    tracemalloc.start()
    try:
        assert validate_family_graph(nodes, family_ids=("leaf",)) == ()
        walk = build_family_paths(nodes, family_ids=("leaf",))
        assert walk.defects == ()
        assert len(walk.paths) == 8**7
        assert walk.paths[0].root_to_leaf[-1] == "leaf"
        assert walk.paths[-1].root_to_leaf[0] == "l6n7"
        assert len(walk.paths[:3]) == 3
        result = normalize_provider_class(
            _annotation("GPCR", ("leaf",)),
            nodes,
            ApprovedMapping(type_to_class=(("GPCR", _RECEPTOR),)),
        )
        assert result.iuphar_class == _RECEPTOR
        _current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 4 * 1024 * 1024


def test_lazy_path_sequence_preserves_every_path_and_order() -> None:
    from itertools import product

    walk = build_family_paths(_layered_graph(2, 3), family_ids=("leaf",))
    expected = tuple(
        ("leaf", *(f"l{level}n{index}" for level, index in enumerate(choices)))
        for choices in product(range(2), repeat=3)
    )
    assert tuple(tuple(reversed(path.root_to_leaf)) for path in walk.paths) == expected
    assert tuple(walk.paths) == walk.paths
    assert tuple(walk.paths[::-1]) == tuple(reversed(tuple(walk.paths)))
    with pytest.raises(IndexError):
        _ = walk.paths[len(walk.paths)]
    with pytest.raises(IndexError):
        _ = walk.paths[-len(walk.paths) - 1]


def test_shared_ancestor_depth_is_checked_for_every_start() -> None:
    nodes = (*_chain(8), FamilyNode("extra", ("n0",)))
    walk = build_family_paths(nodes, family_ids=("n0", "extra"))
    assert walk.paths == ()
    assert walk.defects[0].limit_key == "max_depth"


def test_ancestor_path_is_not_an_approved_direct_family_mapping() -> None:
    nodes = (_node("leaf", "root"), _node("root"))
    mapping = ApprovedMapping(family_to_class=(("root", _ENZYME),))
    descendant = normalize_provider_class(_annotation(None, ("leaf",)), nodes, mapping)
    direct = normalize_provider_class(_annotation(None, ("root",)), nodes, mapping)
    assert descendant.iuphar_annotation_status == "unmapped_type"
    assert descendant.iuphar_class is None
    assert direct.iuphar_annotation_status == "partial"
    assert direct.iuphar_class == _ENZYME
    assert build_family_paths(nodes, family_ids=("leaf",)).paths[0].root_to_leaf == (
        "root",
        "leaf",
    )


def test_lazy_paths_match_a_small_independent_dag_oracle() -> None:
    import random

    rng = random.Random(13149)
    for _case in range(100):
        count = rng.randint(1, 8)
        nodes = tuple(
            FamilyNode(
                str(index),
                tuple(
                    str(parent)
                    for parent in range(index + 1, count)
                    if rng.random() < 0.5
                ),
            )
            for index in range(count)
        )
        by_id = {node.family_id: node for node in nodes}
        starts = tuple(str(rng.randrange(count)) for _ in range(rng.randint(1, 3)))

        def enumerate_paths(
            path: tuple[str, ...], graph: dict[str, FamilyNode] = by_id
        ) -> list[tuple[str, ...]]:
            parents = graph[path[-1]].parent_ids
            if not parents:
                return [path]
            return [
                result
                for parent in parents
                for result in enumerate_paths((*path, parent))
            ]

        expected = sorted(
            path for start in starts for path in enumerate_paths((start,))
        )
        walk = build_family_paths(nodes, family_ids=starts)
        assert walk.defects == ()
        actual = [tuple(reversed(path.root_to_leaf)) for path in walk.paths]
        assert actual == expected
        assert len(walk.paths) == len(expected)
        for index, path in enumerate(expected):
            assert tuple(reversed(walk.paths[index].root_to_leaf)) == path


def test_duplicate_edges_and_starts_keep_global_sorted_multiplicity() -> None:
    nodes = (
        _node("leaf", "a", "a"),
        _node("a", "b", "c", "c"),
        _node("b"),
        _node("c"),
    )
    paths = build_family_paths(nodes, family_ids=("leaf", "leaf")).paths
    expected = [("leaf", "a", "b")] * 4 + [("leaf", "a", "c")] * 8
    assert [tuple(reversed(path.root_to_leaf)) for path in paths] == expected
    assert len(paths) == len(expected)
    assert [
        tuple(reversed(paths[index].root_to_leaf)) for index in range(len(paths))
    ] == expected
