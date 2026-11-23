"""TC-06 family graph, limits, and direct-layer mapping."""

from __future__ import annotations

import pytest

from iuphar_target_class.gtopdb_2026_3_1 import (
    ARCHIVE_SHA256,
    SQL_SHA256,
    TARGETS_CSV_SHA256,
)
from iuphar_target_class.hierarchy import (
    CoverageExclusion,
    FamilyNode,
    SpeciesVariant,
    admit_approved_release,
    admit_family_graph,
    build_family_paths,
    coverage_matrix,
    normalize_approved_provider_class,
    normalize_provider_class,
    official_material_provenance,
    qualified_absence,
    validate_family_graph,
)
from iuphar_target_class.policy import GRAPH_MAX_DEPTH, GRAPH_MAX_VISITED_NODES
from iuphar_target_class.rf008_qualification import evaluate_categories

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
    assert defect.message == "противоречивая запись"


def test_same_payload_with_different_parents_is_order_independent() -> None:
    orders = (
        (
            FamilyNode("leaf", ("right",), "same"),
            FamilyNode("leaf", ("left",), "same"),
        ),
        (
            FamilyNode("leaf", ("left",), "same"),
            FamilyNode("leaf", ("right",), "same"),
        ),
    )
    parents = (
        FamilyNode("left", (), "left"),
        FamilyNode("right", (), "right"),
    )
    paths = [("left", "leaf"), ("right", "leaf")]
    for rows in orders:
        result = normalize_provider_class(
            type_name=None,
            family_ids=("leaf",),
            nodes=(*rows, *parents),
            type_to_class={},
            family_to_class={"leaf": "Enzyme"},
        )
        assert result.diagnostics == ()
        assert result.iuphar_class == "Enzyme"
        assert [item.root_to_leaf for item in result.paths] == paths
    missing_orders = (
        (FamilyNode("leaf", (), "same"), FamilyNode("leaf", ("gone",), "same")),
        (FamilyNode("leaf", ("gone",), "same"), FamilyNode("leaf", (), "same")),
    )
    for nodes in missing_orders:
        blocked = normalize_provider_class(
            type_name=None,
            family_ids=("leaf",),
            nodes=nodes,
            type_to_class={},
            family_to_class={"leaf": "Enzyme"},
        )
        assert blocked.diagnostics[0].message == "отсутствующий родитель"
        assert blocked.iuphar_class is None
        assert blocked.paths == ()


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
    assert gpcr.iuphar_subclass is None
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
    group = normalize_approved_provider_class(
        release="2026.3.1",
        type_name="grouping",
        family_ids=("694",),
    )
    assert group.annotation_status == "unmapped_type"
    assert group.iuphar_class is None
    assert group.family_evidence == ()


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


def test_subclass_dictionary_stays_partial_and_does_not_read_path_text() -> None:
    nodes = (
        FamilyNode("leaf", ("root",), "leaf"),
        FamilyNode("root", (), "root"),
    )
    mapped = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
        family_to_subclass={"leaf": "Kinase", "root": "Ignored"},
        name="kinase",
        path_text="Kinase / foo",
    )
    assert mapped.annotation_status == "partial"
    assert mapped.iuphar_class == "Enzyme"
    assert mapped.iuphar_subclass == "Kinase"
    assert mapped.iuphar_subclass_candidates == ("Kinase",)
    assert mapped.type_origin is None
    assert mapped.class_origin == "family_mapping"
    assert mapped.subclass_origin == "subclass_dictionary"
    assert mapped.annotation_capability == "family_only"
    assert mapped.absence_status == "source_unavailable"
    assert mapped.proof == "отображение семейства"
    unnamed = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
        name="kinase",
        path_text="Kinase / foo",
    )
    assert unnamed.iuphar_subclass is None
    assert unnamed.subclass_origin is None
    blank = normalize_provider_class(
        type_name="gpcr",
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={"gpcr": "Receptor"},
        family_to_class={"leaf": "Enzyme"},
        family_to_subclass={"leaf": "  ", "root": ""},
    )
    assert blank.annotation_status == "available"
    assert blank.iuphar_subclass is None
    assert blank.iuphar_subclass_candidates == ()
    partial_blank = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
        family_to_subclass={"leaf": ""},
    )
    assert partial_blank.annotation_status == "partial"
    assert partial_blank.iuphar_subclass is None
    kept = normalize_provider_class(
        type_name="gpcr",
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={"gpcr": "Receptor"},
        family_to_class={"leaf": "Enzyme"},
        family_to_subclass={"leaf": " Kinase ", "root": " "},
    )
    assert kept.annotation_status == "available"
    assert kept.iuphar_subclass == "Kinase"
    typed = normalize_provider_class(
        type_name="gpcr",
        family_ids=("leaf",),
        nodes=nodes,
        type_to_class={"gpcr": "Receptor"},
        family_to_class={"leaf": "Receptor"},
        family_to_subclass={"leaf": "Kinase"},
    )
    assert typed.annotation_status == "available"
    assert typed.iuphar_class == "Receptor"
    assert typed.iuphar_subclass == "Kinase"
    assert typed.type_origin == "type_mapping"
    assert typed.class_origin == "type_mapping"
    assert typed.subclass_origin == "subclass_dictionary"
    assert typed.annotation_capability == "family_only"


def test_disagreeing_subclasses_do_not_drop_the_agreed_class() -> None:
    result = normalize_provider_class(
        type_name=None,
        family_ids=("1", "2"),
        nodes=(FamilyNode("1", (), "one"), FamilyNode("2", (), "two")),
        type_to_class={},
        family_to_class={"1": "Enzyme", "2": "Enzyme"},
        family_to_subclass={"1": "Kinase", "2": "Protease"},
    )
    assert result.annotation_status == "partial"
    assert result.iuphar_class == "Enzyme"
    assert result.iuphar_subclass is None
    assert result.iuphar_subclass_candidates == ("Kinase", "Protease")
    assert result.class_origin == "family_mapping"
    assert result.subclass_origin == "subclass_dictionary"
    assert result.annotation_capability == "family_only"


def test_legacy_and_local_ids_stay_outside_official_paths() -> None:
    nodes = (
        FamilyNode("leaf", ("local:1", "root"), "leaf"),
        FamilyNode("root", (), "root"),
        FamilyNode("local:1", ("legacy:9",), "synth"),
        FamilyNode("legacy:9", (), "old"),
    )
    result = normalize_provider_class(
        type_name=None,
        family_ids=("leaf", "local:1"),
        nodes=nodes,
        type_to_class={},
        family_to_class={"leaf": "Enzyme", "local:1": "Ion Channel"},
        family_to_subclass={"local:1": "Secret", "leaf": "Kinase"},
    )
    assert result.diagnostics == ()
    assert result.iuphar_class == "Enzyme"
    assert result.iuphar_subclass == "Kinase"
    assert result.family_evidence == (("leaf", "Enzyme"),)
    assert [item.root_to_leaf for item in result.paths] == [("root", "leaf")]
    assert ("leaf", "local:1", "synthetic_local") in result.detached_edges
    assert ("local:1", "legacy:9", "legacy") in result.detached_edges
    assert result.separated_ids == (("local:1", "synthetic_local"),)
    assert result.annotation_capability == "family_only"


def test_cycle_or_missing_parent_blocks_snapshot_admission() -> None:
    cycle_nodes = (
        FamilyNode("ok", (), "ok"),
        FamilyNode("a", ("b",), "a"),
        FamilyNode("b", ("a",), "b"),
    )
    cycle = admit_family_graph(cycle_nodes, ("ok",))
    assert cycle.admitted is False
    assert cycle.diagnostics[0].message == "цикл"
    assert cycle.annotation_capability == "family_only"
    assert cycle.absence_status == "source_unavailable"
    missing = admit_family_graph((FamilyNode("a", ("gone",), "a"),), ("a",))
    assert missing.admitted is False
    assert missing.diagnostics[0].message == "отсутствующий родитель"
    legacy_cycle = (
        FamilyNode("leaf", (), "leaf"),
        FamilyNode("legacy:a", ("legacy:b",), "a"),
        FamilyNode("legacy:b", ("legacy:a",), "b"),
    )
    blocked = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=legacy_cycle,
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
    )
    assert blocked.diagnostics[0].message == "цикл"
    assert blocked.iuphar_class is None
    assert blocked.iuphar_subclass is None


def test_cut_path_does_not_keep_a_dictionary_subclass() -> None:
    result = normalize_provider_class(
        type_name=None,
        family_ids=("leaf",),
        nodes=(FamilyNode("leaf", ("gone",), "leaf"),),
        type_to_class={},
        family_to_class={"leaf": "Enzyme"},
        family_to_subclass={"leaf": "Kinase"},
    )
    assert result.diagnostics[0].message == "отсутствующий родитель"
    assert result.iuphar_subclass is None
    assert result.subclass_origin is None
    assert result.annotation_capability == "family_only"


def test_species_rows_keep_taxa_and_ambiguous_uniprot() -> None:
    provenance = official_material_provenance("2026.3.1")
    exclusions = (CoverageExclusion("3", "10090", "нет видовой аннотации"),)
    first = (
        SpeciesVariant("2", "9606", ("P2", "P1"), "enzyme", "full"),
        SpeciesVariant("1", "10116", ("P1",), "gpcr", "family_only"),
        SpeciesVariant("1", "9606", ("P1",), "gpcr", "family_only"),
        SpeciesVariant("1", "9606", ("P1",), "gpcr", "family_only"),
    )
    matrix_a = coverage_matrix(
        first, exclusions, release="2026.3.1", provenance=provenance
    )
    matrix_b = coverage_matrix(
        tuple(reversed(first)),
        exclusions,
        release="2026.3.1",
        provenance=tuple(reversed(provenance)),
        completeness_qualified=True,
    )
    assert matrix_a == matrix_b
    assert [f"{item.target_id}:{item.taxon_id}" for item in matrix_a.variants] == [
        "1:10116",
        "1:9606",
        "2:9606",
    ]
    assert matrix_a.variants[2].uniprot_ids == ("P1", "P2")
    assert {item.annotation for item in matrix_a.variants} == {"family_only"}
    assert matrix_a.annotation_capability == "family_only"
    assert matrix_a.absence_status == "source_unavailable"
    assert matrix_a.ambiguous_uniprot == (("P1", ("1", "2")),)
    assert matrix_a.exclusions[0].reason == "нет видовой аннотации"
    assert ("targets_csv_sha256", TARGETS_CSV_SHA256) in matrix_a.provenance
    assert matrix_a.counts == (
        ("10116", "gpcr", "family_only", 1),
        ("9606", "enzyme", "family_only", 1),
        ("9606", "gpcr", "family_only", 1),
    )


def test_family_only_absence_is_not_a_qualified_not_found() -> None:
    assert qualified_absence("family_only", completeness_qualified=True) == (
        "source_unavailable"
    )
    assert qualified_absence("complete", completeness_qualified=False) == (
        "source_unavailable"
    )
    assert qualified_absence("complete", completeness_qualified=True) == "not_found"


def test_approved_release_keeps_both_paths_and_pinned_hashes() -> None:
    provenance = dict(official_material_provenance("2026.3.1"))
    assert provenance["targets_csv_sha256"] == TARGETS_CSV_SHA256
    assert provenance["archive_sha256"] == ARCHIVE_SHA256
    assert provenance["sql_sha256"] == SQL_SHA256
    admission = admit_approved_release("2026.3.1", ("953",))
    assert admission.admitted is True
    assert admission.diagnostics == ()
    assert admission.annotation_capability == "family_only"
    assert admission.absence_status == "source_unavailable"
    mapped = normalize_approved_provider_class(
        release="2026.3.1",
        type_name=None,
        family_ids=("953",),
        family_to_subclass={"953": "Catalytic"},
    )
    assert [item.root_to_leaf for item in mapped.paths] == [
        ("688", "862", "953"),
        ("864", "954", "953"),
    ]
    assert mapped.annotation_status == "partial"
    assert mapped.iuphar_class == "Receptor"
    assert mapped.iuphar_subclass == "Catalytic"
    assert mapped.class_origin == "family_mapping"
    assert mapped.subclass_origin == "subclass_dictionary"
    assert mapped.annotation_capability == "family_only"
    assert mapped.absence_status == "source_unavailable"


def _numbered_chain(
    length: int, *, root_id_first: bool
) -> tuple[tuple[FamilyNode, ...], str]:
    labels = [f"{index:02d}" for index in range(length)]
    ordered = labels if root_id_first else list(reversed(labels))
    nodes = tuple(
        FamilyNode(
            family_id,
            () if index == 0 else (ordered[index - 1],),
            family_id,
        )
        for index, family_id in enumerate(ordered)
    )
    return nodes, ordered[0]


@pytest.mark.parametrize("root_id_first", [True, False])
def test_unrequested_deep_branch_blocks_admission_in_either_id_order(
    root_id_first: bool,
) -> None:
    nodes, root = _numbered_chain(10, root_id_first=root_id_first)
    blocked = admit_family_graph(
        nodes,
        (root,),
        max_depth=8,
        max_visited_nodes=10_000,
    )
    assert blocked.admitted is False
    assert blocked.diagnostics[0].message == "превышение лимита"
    assert blocked.annotation_capability == "family_only"
    allowed_nodes, allowed_root = _numbered_chain(9, root_id_first=root_id_first)
    allowed = admit_family_graph(
        allowed_nodes,
        (allowed_root,),
        max_depth=8,
        max_visited_nodes=10_000,
    )
    assert allowed.admitted is True
    assert allowed.diagnostics == ()


def test_unrelated_request_blocks_a_deeper_chain_in_either_naming() -> None:
    forward = (
        FamilyNode("a", (), "root"),
        FamilyNode("b", ("a",), "mid"),
        FamilyNode("c", ("b",), "leaf"),
        FamilyNode("ok", (), "other"),
    )
    reverse = (
        FamilyNode("c", (), "root"),
        FamilyNode("b", ("c",), "mid"),
        FamilyNode("a", ("b",), "leaf"),
        FamilyNode("ok", (), "other"),
    )
    for nodes in (forward, reverse):
        blocked = admit_family_graph(
            nodes,
            ("ok",),
            max_depth=1,
            max_visited_nodes=10_000,
        )
        assert blocked.admitted is False
        assert blocked.diagnostics[0].message == "превышение лимита"


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
