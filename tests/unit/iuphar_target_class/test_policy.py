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


def test_stage1_parameters_stay_unset() -> None:
    parameters = policy_document()["parameters"]
    assert isinstance(parameters, dict)
    limits = parameters["graph_limits"]
    assert isinstance(limits, dict)
    assert limits["max_depth"] is None
    assert limits["max_visited_nodes"] is None
    assert parameters["missing_markers_version"] is None
    assert parameters["snapshot_coverage"] is None
    assert parameters["snapshot_species"] is None
    assert parameters["volume_test_seconds"] is None
    assert parameters["isoform_policy"] is None


def test_direct_ec_rule_is_rejected() -> None:
    broken = RuleRecord(
        rule_id="ec:1",
        family="ec",
        input_conditions="EC 1",
        output="Oxidoreductases",
        justification_source="план v1 r8 шаг D",
        version="plan-v1-r8",
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
