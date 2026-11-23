"""TC-06 family graph, limits, and direct-layer mapping."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from iuphar_target_class.hierarchy import (
    FamilyNode,
    assign_mapped_subclass,
    build_family_paths,
    normalize_approved_provider_class,
    normalize_provider_class,
    validate_family_graph,
)
from iuphar_target_class.policy import GRAPH_MAX_DEPTH, GRAPH_MAX_VISITED_NODES
from iuphar_target_class.rf008_qualification import evaluate_categories

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[3]
RF005_MATRIX = REPO / "data" / "iuphar_target_class" / "rf005" / "coverage_matrix.json"
RF005_RECEIPT = (
    REPO / "data" / "iuphar_target_class" / "rf005" / "coverage_matrix.sha256.json"
)


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


def test_same_payload_with_different_parents_merges_order_independently() -> None:
    """RF-005: union parent sets by family ID; do not keep only the first row."""
    left = (
        FamilyNode("leaf", ("a",), "enzyme"),
        FamilyNode("leaf", ("b",), "enzyme"),
        FamilyNode("a", (), "grouping"),
        FamilyNode("b", (), "grouping"),
    )
    right = (
        FamilyNode("leaf", ("b",), "enzyme"),
        FamilyNode("leaf", ("a",), "enzyme"),
        FamilyNode("b", (), "grouping"),
        FamilyNode("a", (), "grouping"),
    )
    expected = [("a", "leaf"), ("b", "leaf")]
    for nodes in (left, right):
        result = normalize_provider_class(
            type_name=None,
            family_ids=("leaf",),
            nodes=nodes,
            type_to_class={},
            family_to_class={"leaf": "Enzyme"},
            family_to_subclass={"leaf": "Enzymes"},
        )
        assert result.diagnostics == ()
        assert result.iuphar_class == "Enzyme"
        assert result.iuphar_subclass == "Enzymes"
        assert [item.root_to_leaf for item in result.paths] == expected


def test_conflicting_payloads_for_same_family_still_fail() -> None:
    result = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=(
            FamilyNode("leaf", ("a",), "enzyme"),
            FamilyNode("leaf", ("b",), "transporter"),
            FamilyNode("a", (), "grouping"),
            FamilyNode("b", (), "grouping"),
        ),
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
    )
    assert result.diagnostics[0].message == "повторяющийся идентификатор"
    assert result.iuphar_class is None
    assert result.paths == ()


def test_public_path_builder_rejects_a_cycle_and_a_missing_parent() -> None:
    cycle = build_family_paths(
        (FamilyNode("a", ("b",), "a"), FamilyNode("b", ("a",), "b")),
        ("a",),
    )
    assert not isinstance(cycle, tuple)
    assert cycle.message == "цикл"
    loop = build_family_paths((FamilyNode("a", ("a",), "a"),), ("a",))
    assert not isinstance(loop, tuple)
    assert loop.message == "self-loop"
    missing = build_family_paths((FamilyNode("a", ("gone",), "a"),), ("a",))
    assert not isinstance(missing, tuple)
    assert missing.message == "отсутствующий родитель"


def test_unmapped_type_on_a_broken_graph_is_not_partial() -> None:
    result = normalize_provider_class(
        type_name="unknown-type",
        family_ids=("leaf",),
        nodes=(FamilyNode("leaf", ("gone",), "leaf"),),
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
    )
    assert result.diagnostics[0].message == "отсутствующий родитель"
    assert result.annotation_status == "not_available"
    assert result.iuphar_class is None
    assert result.source is None


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


def test_unrequested_deep_branch_blocks_admission_in_either_id_order() -> None:
    deep = _chain(GRAPH_MAX_DEPTH + 1)
    shallow = (FamilyNode("ok", (), "ok"),)
    forward = validate_family_graph(
        (*deep, *shallow),
        ("ok",),
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=10_000,
    )
    reverse = validate_family_graph(
        (*tuple(reversed(deep)), *shallow),
        ("ok",),
        max_depth=GRAPH_MAX_DEPTH,
        max_visited_nodes=10_000,
    )
    assert forward is not None and reverse is not None
    assert forward.message == reverse.message == "превышение лимита"


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


def test_approved_real_release_classifies_gpcr_and_distinguishes_grouping() -> None:
    gpcr = normalize_approved_provider_class(
        release="2026.3.1",
        type_name="GPCR",
        family_ids=("1",),
    )
    assert gpcr.annotation_status == "available"
    assert gpcr.iuphar_class == "Receptor"
    assert gpcr.iuphar_subclass == "G protein-coupled receptors"
    assert gpcr.family_evidence == (("1", "Receptor"),)
    assert gpcr.paths and all("694" in path.root_to_leaf for path in gpcr.paths)
    fallback = normalize_approved_provider_class(
        release="2026.3.1",
        type_name=None,
        family_ids=("1",),
    )
    assert fallback.annotation_status == "partial"
    assert fallback.proof == "отображение семейства"
    assert fallback.source == "iuphar_normalized"
    assert fallback.iuphar_class == "Receptor"
    assert fallback.iuphar_subclass == "G protein-coupled receptors"
    group = normalize_approved_provider_class(
        release="2026.3.1",
        type_name="grouping",
        family_ids=("694",),
    )
    assert group.annotation_status == "unmapped_type"
    assert group.iuphar_class is None
    assert group.iuphar_subclass is None
    assert group.family_evidence == ()


def test_approved_multi_parent_family_keeps_every_path() -> None:
    result = normalize_approved_provider_class(
        release="2026.3.1",
        type_name=None,
        family_ids=("254",),
    )
    assert result.annotation_status == "partial"
    assert result.iuphar_class == "Enzyme"
    assert result.iuphar_subclass == "Enzymes"
    paths = [item.root_to_leaf for item in result.paths]
    assert paths == sorted(paths)
    assert len(paths) == 2
    assert all(path[-1] == "254" for path in paths)
    assert {"239", "865"} == {path[-2] for path in paths}


def test_family_subclass_fallback_requires_matching_family_class() -> None:
    """Family subclass is kept only when its family class matches iuphar_class."""
    compatible = assign_mapped_subclass(
        type_name="enzyme",
        family_ids=("900",),
        type_to_subclass={},
        family_to_subclass={"900": "Enzymes"},
        iuphar_class="Enzyme",
        family_to_class={"900": "Enzyme"},
    )
    assert compatible == "Enzymes"
    mismatched = assign_mapped_subclass(
        type_name="enzyme",
        family_ids=("1",),
        type_to_subclass={},
        family_to_subclass={"1": "G protein-coupled receptors"},
        iuphar_class="Enzyme",
        family_to_class={"1": "Receptor"},
    )
    assert mismatched is None
    via_normalize = normalize_provider_class(
        type_name="enzyme",
        family_ids=("1",),
        nodes=(FamilyNode("1", (), "gpcr"),),
        type_to_class={"enzyme": "Enzyme"},
        family_to_class={"1": "Receptor"},
        type_to_subclass={},
        family_to_subclass={"1": "G protein-coupled receptors"},
    )
    assert via_normalize.iuphar_class == "Enzyme"
    assert via_normalize.iuphar_subclass is None


def test_synthetic_family_ids_stay_outside_official_paths() -> None:
    mixed = normalize_provider_class(
        type_name="gpcr",
        family_ids=("1", "local:x"),
        nodes=(FamilyNode("1", (), "gpcr"),),
        type_to_class={"gpcr": "Receptor"},
        family_to_class={"1": "Receptor"},
        type_to_subclass={"gpcr": "G protein-coupled receptors"},
        family_to_subclass={"1": "G protein-coupled receptors"},
    )
    assert mixed.iuphar_class == "Receptor"
    assert mixed.iuphar_subclass == "G protein-coupled receptors"
    assert [item.root_to_leaf for item in mixed.paths] == [("1",)]
    assert (
        mixed.diagnostics[0].message
        == "синтетический идентификатор в официальном графе"
    )
    only_local = normalize_provider_class(
        type_name=None,
        family_ids=("local:x",),
        nodes=(),
        type_to_class={},
        family_to_class={},
    )
    assert only_local.annotation_status == "not_available"
    assert only_local.iuphar_class is None
    assert only_local.paths == ()
    assert (
        only_local.diagnostics[0].message
        == "синтетический идентификатор в официальном графе"
    )
    typed_local = normalize_provider_class(
        type_name="gpcr",
        family_ids=("local:x",),
        nodes=(),
        type_to_class={"gpcr": "Receptor"},
        family_to_class={},
        type_to_subclass={"gpcr": "G protein-coupled receptors"},
    )
    assert typed_local.annotation_status == "partial"
    assert typed_local.iuphar_class == "Receptor"
    assert typed_local.iuphar_subclass == "G protein-coupled receptors"
    assert typed_local.proof == "type"
    assert typed_local.paths == ()
    assert typed_local.diagnostics[0].level == "error"
    assert (
        typed_local.diagnostics[0].message
        == "синтетический идентификатор в официальном графе"
    )


def test_local_nodes_dropped_before_official_graph_validation() -> None:
    """Codex P2: local records in nodes must not reject an intact official walk."""
    result = normalize_provider_class(
        type_name=None,
        family_ids=("1", "local:x"),
        nodes=(
            FamilyNode("1", (), "enzyme"),
            FamilyNode("local:x", ("1",), "enzyme"),
        ),
        type_to_class={},
        family_to_class={"1": "Enzyme"},
        family_to_subclass={"1": "Enzymes"},
    )
    assert result.annotation_status == "partial"
    assert result.iuphar_class == "Enzyme"
    assert result.iuphar_subclass == "Enzymes"
    assert [item.root_to_leaf for item in result.paths] == [("1",)]
    assert result.diagnostics[0].level == "warning"
    assert (
        result.diagnostics[0].message
        == "синтетический идентификатор в официальном графе"
    )
    broken = normalize_provider_class(
        type_name=None,
        family_ids=("1",),
        nodes=(FamilyNode("1", ("local:x",), "enzyme"),),
        type_to_class={},
        family_to_class={"1": "Enzyme"},
    )
    assert broken.annotation_status == "not_available"
    assert broken.iuphar_class is None
    assert broken.paths == ()
    assert broken.diagnostics[0].level == "error"
    assert (
        broken.diagnostics[0].message
        == "синтетический идентификатор в официальном графе"
    )


def test_approved_mapping_is_rejected_for_a_different_release() -> None:
    with pytest.raises(ValueError, match="does not match approved mapping"):
        normalize_approved_provider_class(
            release="2026.3.2",
            type_name="gpcr",
            family_ids=("1",),
        )


def test_conflicting_family_evidence_is_not_hidden_by_a_known_type() -> None:
    conflict = normalize_provider_class(
        type_name="gpcr",
        family_ids=("1", "2"),
        nodes=(FamilyNode("1", (), "one"), FamilyNode("2", (), "two")),
        type_to_class={"gpcr": "Receptor"},
        family_to_class={"1": "Receptor", "2": "Ion Channel"},
    )
    assert conflict.annotation_status == "conflicting"
    assert conflict.iuphar_class is None
    assert conflict.iuphar_subclass is None
    assert conflict.family_evidence == (("1", "Receptor"), ("2", "Ion Channel"))


def test_rf005_coverage_matrix_keeps_family_only_and_receipt() -> None:
    payload = RF005_MATRIX.read_bytes()
    receipt = json.loads(RF005_RECEIPT.read_text(encoding="utf-8"))
    assert hashlib.sha256(payload).hexdigest() == receipt["sha256"]
    document = json.loads(payload.decode("utf-8"))
    assert document["artifact"] == "iuphar_rf005_coverage_matrix"
    assert document["annotation_capability"] == "family_only"
    assert document["biological_accuracy_accepted"] is False
    assert "source_unavailable" in document["source_unavailable_policy"]
    assert document["family_graph"]["multi_parent_rows"] >= 1
    assert (
        "G protein-coupled receptors"
        in document["object_types"]["approved_type_to_subclass"].values()
    )


def test_rf008_direct_class_and_graph_defects_follow_the_dictionary() -> None:
    report = evaluate_categories(
        ("direct_type", "partial_source", "multi_parent", "cycle", "missing_node")
    )
    assert report["unexplained_error_count"] == 0
    cases = report["cases"]
    assert isinstance(cases, list)
    by_id = {str(item["case_id"]): item for item in cases if isinstance(item, dict)}
    assert by_id["direct-type-gpcr"]["disposition"] == "verified"
    assert by_id["direct-type-gpcr"]["observed"]["iuphar_class"] == "Receptor"
    assert by_id["graph-partial-family"]["observed"]["annotation_status"] == "partial"
    assert by_id["graph-cycle"]["observed"]["iuphar_class"] is None
    assert by_id["graph-missing-node"]["observed"]["paths_empty"] is True
    assert by_id["graph-multi-parent"]["disposition"] == "verified"
    evidence = by_id["graph-multi-parent"]["evidence"]
    observed = by_id["graph-multi-parent"]["observed"]
    assert isinstance(evidence, dict)
    assert isinstance(observed, dict)
    parents = evidence["parents"]
    branches = observed["root_to_leaf_paths"]
    assert isinstance(parents, list)
    assert isinstance(branches, list)
    leaf = str(evidence["family_id"])
    assert observed["branch_count"] == len(parents) == len(branches)
    assert len(branches) > 1
    assert all(isinstance(path, list) and path[-1] == leaf for path in branches)
    assert {path[-2] for path in branches} == {str(parent) for parent in parents}
