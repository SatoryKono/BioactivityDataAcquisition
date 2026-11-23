"""TC-02 policy: class rules, unknown types, and unset parameters."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iuphar_target_class.policy import (
    WORKING_CLASSES,
    RuleRecord,
    all_rules,
    assign_mapped_class,
    compare_subclasses,
    policy_document,
    publish_policy,
    validate_rules,
)
from iuphar_target_class.stage0.io import canonical_json_bytes

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[3]
POLICY_PATH = REPO / "data" / "iuphar_target_class" / "policy" / "policy.json"


def test_every_class_has_a_source_and_ec_rules_are_not_direct() -> None:
    document = policy_document()
    rules = document["class_dictionary"]
    assert isinstance(rules, list)
    assert [item["output"] for item in rules] == list(WORKING_CLASSES)
    for item in rules:
        assert item["justification_source"]
        assert item["input_conditions"]
        assert item["marks_direct_layer"] is False
    local = document["local_rules"]
    assert isinstance(local, list)
    ec_or_prediction = [
        item for item in local if item["family"] in {"ec", "l1_l2", "free_text"}
    ]
    assert ec_or_prediction
    assert all(item["marks_direct_layer"] is False for item in ec_or_prediction)


def test_unknown_type_is_not_replaced_and_family_mapping_is_partial() -> None:
    unmapped = assign_mapped_class(
        type_name="GPCR",
        family_ids=("900",),
        type_to_class={},
        family_to_class={},
        name="Voltage-gated ion channel",
        path_text="Ion Channel / foo",
    )
    assert unmapped.status == "unmapped_type"
    assert unmapped.iuphar_class is None
    assert unmapped.iuphar_class != "Other Protein Target"
    mapped = assign_mapped_class(
        type_name="not-a-type",
        family_ids=("900",),
        type_to_class={},
        family_to_class={"900": "Receptor"},
    )
    assert mapped.status == "partial"
    assert mapped.proof == "family_mapping"
    assert mapped.iuphar_class == "Receptor"


def test_offline_not_run_does_not_block_early_stages() -> None:
    contract = policy_document()["api_contract"]
    assert isinstance(contract, dict)
    saved = contract["saved_responses"]
    assert isinstance(saved, dict)
    assert saved["targets"] == "NOT_RUN"
    assert saved["reason"]
    operational = contract["operational_check"]
    assert isinstance(operational, dict)
    assert operational["status"] == "NOT_RUN"
    assert operational["blocks_stages_0_to_3"] is False


def test_only_approved_stage1_parameters_are_set() -> None:
    parameters = policy_document()["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["missing_markers_version"] is None
    assert parameters["snapshot_coverage"]
    assert parameters["snapshot_species"] == [9606, 10090, 10116]
    assert parameters["snapshot_coverage_status"] == "утверждено"
    assert parameters["isoform_policy"] is None


def test_volume_test_seconds_is_approved() -> None:
    parameters = policy_document()["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["volume_test_seconds"] == 300
    assert parameters["volume_test_time_status"] == "утверждено"


def test_recorded_graph_and_http_limits() -> None:
    parameters = policy_document()["parameters"]
    assert isinstance(parameters, dict)
    limits = parameters["graph_limits"]
    assert isinstance(limits, dict)
    assert limits["max_depth"] == 8
    assert limits["max_visited_nodes"] == 128
    assert limits["status"] == "утверждено"
    adapter = policy_document()["http_adapter"]
    assert isinstance(adapter, dict)
    assert adapter["timeout_sec"] == 15
    assert adapter["read_timeout_multiplier"] == 2
    assert adapter["max_retries"] == 3
    assert adapter["retry_base_delay"] == 1
    assert adapter["retry_max_delay"] == 30
    assert adapter["requests_per_second"] == 1
    assert adapter["burst"] == 1
    assert adapter["failure_threshold"] == 5
    assert adapter["recovery_timeout"] == 60
    assert adapter["operational_check"] == "NOT_RUN"
    assert adapter["status"] == "утверждено"


def test_direct_ec_rule_is_rejected() -> None:
    broken = RuleRecord(
        rule_id="ec:1",
        family="ec",
        input_conditions="EC 1",
        output="Oxidoreductases",
        justification_source="план v1 r8 шаг D",
        version="plan-v1-r9",
        limits="local",
        marks_direct_layer=True,
    )
    with pytest.raises(ValueError, match="must not be marked direct"):
        validate_rules((broken,))


def test_subclass_outside_vocabulary_is_a_contract_defect() -> None:
    assert (
        compare_subclasses(
            direct_subclass="alpha",
            local_subclass="alpha",
            direct_vocabulary=frozenset(),
            local_vocabulary=frozenset(),
            same_pairs=frozenset(),
            class_subclass_pairs=frozenset(),
        )
        == "contract_defect"
    )
    assert (
        compare_subclasses(
            direct_subclass="alpha",
            local_subclass="beta",
            direct_vocabulary=frozenset({"alpha"}),
            local_vocabulary=frozenset({"beta"}),
            same_pairs=frozenset(),
            class_subclass_pairs=frozenset(),
        )
        == "incompatible"
    )


@pytest.mark.parametrize(
    ("direct_subclass", "local_subclass", "expected"),
    [
        ("unknown", None, "contract_defect"),
        (None, "unknown", "contract_defect"),
        ("alpha", None, "empty"),
        (None, "beta", "empty"),
        (None, None, "empty"),
    ],
)
def test_missing_peer_does_not_hide_an_invalid_subclass(
    direct_subclass: str | None, local_subclass: str | None, expected: str
) -> None:
    assert (
        compare_subclasses(
            direct_subclass=direct_subclass,
            local_subclass=local_subclass,
            direct_vocabulary=frozenset({"alpha"}),
            local_vocabulary=frozenset({"beta"}),
            same_pairs=frozenset(),
            class_subclass_pairs=frozenset(),
        )
        == expected
    )


def test_committed_policy_matches_rebuild() -> None:
    assert POLICY_PATH.read_bytes() == canonical_json_bytes(policy_document())


def test_publish_policy_writes_inside_root(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    output = root / "policy"
    output.mkdir(parents=True)
    publish_policy(output, root=root)
    assert (
        json.loads((output / "policy.json").read_text(encoding="utf-8"))["stage_status"]
        == "recorded_without_biological_acceptance"
    )
    validate_rules(all_rules())


def test_approved_release_rules_are_versioned_and_do_not_claim_acceptance() -> None:
    policy = policy_document()
    mappings = policy["direct_mappings"]
    assert isinstance(mappings, dict)
    assert mappings["release"] == "2026.3.1"
    assert mappings["snapshot_completeness_certified"] is False
    assert policy["biological_accuracy_accepted"] is False
    assert mappings["graph_only_type"] == "grouping"
    type_rules = mappings["types"]
    family_rules = mappings["families"]
    assert sum(len(rule["source_types"]) for rule in type_rules) == 9
    family_ids = [
        family_id for rule in family_rules for family_id in rule["family_ids"]
    ]
    assert len(family_ids) == len(set(family_ids)) == 744
    assert "694" not in family_ids
    for rule in [*type_rules, *family_rules]:
        assert rule["version"] == "2026.3.1"
        assert rule["marks_direct_layer"] is True
        assert (
            rule["input_conditions"] and rule["limits"] and rule["justification_source"]
        )
