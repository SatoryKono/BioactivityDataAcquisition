"""Owner, shard, and manifest-check contracts for the nodeid inventory."""

from __future__ import annotations

import pytest

from scripts.engineering.qa.build_pytest_nodeid_inventory import (
    CollectedNode,
    LaneRule,
    ShardScope,
    _check_payloads,
    _load_mapping,
    _problems,
    build_inventory,
    build_record,
    collect_pytest_args,
    decide_owner,
    expand_shard_names,
    glob_match,
    lane_matches,
    load_lane_rules,
)

pytestmark = pytest.mark.unit

_MATRIX = "configs/quality/test_matrix.yaml"
_SHARDS = "configs/quality/pytest_shards.yaml"
_PASSPORT = "tests/unit/scripts/docs/passports/test_passport_projector.py"


def _node(nodeid: str, file_name: str, markers: tuple[str, ...] = ()) -> CollectedNode:
    return CollectedNode(nodeid, file_name, "Function", markers, ())


def test_collection_keeps_generated_artifact_tests() -> None:
    assert collect_pytest_args(("tests",)) == [
        "--collect-only",
        "-p",
        "no:cacheprovider",
        "--artifact-selection=all",
        "tests",
    ]


def test_duplicate_nodeids_are_counted_once() -> None:
    node = _node("tests/unit/test_a.py::test_a", "tests/unit/test_a.py")
    inventory = build_inventory((node, node), (), source_commit="abc")
    assert inventory["duplicate_nodeids"] == ["tests/unit/test_a.py::test_a"]
    assert _problems(inventory) == ["duplicate nodeids: 1"]


def test_check_ignores_source_commit_and_compares_the_rest() -> None:
    rules = (LaneRule("unit-fast", ("tests/unit/",), (), ""),)
    node = _node("tests/unit/test_a.py::test_a", "tests/unit/test_a.py")
    inventory = build_inventory((node,), rules, source_commit="a" * 40)
    refreshed = dict(inventory)
    refreshed["source_commit"] = "b" * 40
    assert _check_payloads(inventory, refreshed) == 0
    refreshed["count"] = 0
    assert _check_payloads(inventory, refreshed) == 1


def test_tests_outside_configured_lanes_are_full_only() -> None:
    rules = (LaneRule("unit-fast", ("tests/unit/",), (), "not slow"),)
    node = _node(
        "tests/benchmarks/test_a.py::test_a",
        "tests/benchmarks/test_a.py",
        ("benchmark",),
    )
    record = build_record(node, rules)
    assert record["canonical_owner"] == "FullOnly"
    assert record["execution_policy"] == "full-only-residual"
    assert record["overlap_rationale"] == "outside configured lanes"
    assert decide_owner(("unit-fast", "memory")).canonical_owner == "unowned"


def test_sharded_lane_uses_shard_paths_not_the_broad_prefix() -> None:
    rule = LaneRule(
        "unit-parallel-safe",
        ("tests/unit/",),
        (),
        "not slow",
        (ShardScope(("tests/unit/domain/",), (), ()),),
    )
    assert lane_matches(rule, "tests/unit/domain/test_a.py", set())
    assert not lane_matches(rule, "tests/unit/scripts/test_a.py", set())
    assert not lane_matches(rule, "tests/unit/domain/test_a.py", {"slow"})


def test_shard_ignore_glob_excludes_matching_files() -> None:
    rule = LaneRule(
        "architecture",
        ("tests/architecture/",),
        (),
        "",
        (
            ShardScope(
                ("tests/architecture/",),
                (),
                ("tests/architecture/test_[d-z]*.py",),
            ),
        ),
    )
    assert lane_matches(rule, "tests/architecture/test_adapter.py", set())
    assert not lane_matches(rule, "tests/architecture/test_docs.py", set())
    assert glob_match(
        "tests/architecture/nested/test_closeout.py",
        "tests/architecture/**/*closeout*.py",
    )


def test_shard_aliases_expand_without_cycles() -> None:
    aliases = {"fast": ("a", "b"), "a": ("s1",)}
    assert expand_shard_names(("fast", "s1"), aliases) == ("s1", "b")
    with pytest.raises(ValueError, match="cycle"):
        expand_shard_names(("a",), {"a": ("b",), "b": ("a",)})


def test_live_parallel_lane_does_not_claim_script_tests() -> None:
    rules = load_lane_rules(_load_mapping(_MATRIX), _load_mapping(_SHARDS))
    parallel = next(rule for rule in rules if rule.name == "unit-parallel-safe")
    tooling = next(rule for rule in rules if rule.name == "unit-scripts-tooling")
    umbrella = next(rule for rule in rules if rule.name == "coverage-verify")
    assert parallel.shard_scopes
    assert umbrella.shard_scopes == ()
    assert not lane_matches(parallel, _PASSPORT, set())
    assert lane_matches(tooling, _PASSPORT, set())
