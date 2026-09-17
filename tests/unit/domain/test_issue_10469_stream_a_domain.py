"""Stream A domain coverage for #10469 (#10515 leftover helpers, #10519 heads)."""

from __future__ import annotations

from copy import copy, deepcopy
from dataclasses import MISSING
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from bioetl.domain.immutability import (
    FrozenDict,
    FrozenList,
    _immutable,
    deep_freeze_json,
    deep_thaw_json,
    freeze_fields,
)
from bioetl.domain.ports.quality.silver_dq_request import (
    SilverDQAnalyzeRequest,
    _record_silver_dq_field,
    coerce_silver_dq_analyze_request,
)
from bioetl.domain.types.gold_contracts_rejects import GoldRejectReasonCode
from bioetl.domain.types.gold_contracts_rules import (
    GoldBusinessRuleSpec,
    _as_numeric_bound,
    _decision_literal,
)

pytestmark = pytest.mark.unit


def test_gold_decision_literals_and_numeric_bounds() -> None:
    assert _decision_literal("pass") == "pass"
    assert _decision_literal("warn") == "warn"
    assert _decision_literal("fail") == "fail"
    assert _decision_literal("quarantine") == "quarantine"
    assert _decision_literal("other") is None
    assert _as_numeric_bound(True) is None
    assert _as_numeric_bound("1") is None
    assert _as_numeric_bound(1.5) == 1.5


def test_gold_rule_from_mapping_covers_errors_and_optional_fields() -> None:
    with pytest.raises(ValueError, match="condition must be a string"):
        GoldBusinessRuleSpec.from_mapping({"column": "x", "condition": 1})
    with pytest.raises(ValueError, match="values must be a list"):
        GoldBusinessRuleSpec.from_mapping(
            {"column": "x", "condition": "in", "values": "a,b"}
        )
    with pytest.raises(ValueError, match="severity"):
        GoldBusinessRuleSpec.from_mapping(
            {"column": "x", "condition": "present", "severity": "fatal"}
        )
    with pytest.raises(ValueError, match="decision"):
        GoldBusinessRuleSpec.from_mapping(
            {"column": "x", "condition": "present", "decision": 1}
        )
    with pytest.raises(ValueError, match="decision"):
        GoldBusinessRuleSpec.from_mapping(
            {"column": "x", "condition": "present", "decision": "skip"}
        )
    with pytest.raises(ValueError, match="minimum cannot exceed maximum"):
        GoldBusinessRuleSpec.from_mapping(
            {"column": "x", "condition": "range", "min": 10, "max": 1}
        )
    with pytest.raises(ValueError, match="gold_semantic_"):
        GoldBusinessRuleSpec(
            column="x",
            condition="present",
            reject_reason_code=GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE,
        )

    rule = GoldBusinessRuleSpec.from_mapping(
        {
            "column": "value",
            "condition": "in",
            "values": ["a", "b"],
            "severity": "warn",
            "decision": None,
            "pattern": " ^a ",
            "field": " value ",
            "layer": " ",
            "min": True,
            "max": False,
            "reject_reason_code": GoldRejectReasonCode.SEMANTIC_BUSINESS_EXCLUSION,
        }
    )
    assert rule.allowed_values == ("a", "b")
    assert rule.severity == "warn"
    assert rule.decision is None
    assert rule.layer == "gold"
    reason = rule.build_reject_reason(violations=None)
    assert reason.reason_code == GoldRejectReasonCode.SEMANTIC_BUSINESS_EXCLUSION
    assert GoldBusinessRuleSpec._parse_allowed_values(None) == ()
    assert GoldBusinessRuleSpec._validate_decision(None) is None
    assert GoldBusinessRuleSpec._validate_decision("pass") == "pass"
    with pytest.raises(ValueError, match="decision"):
        GoldBusinessRuleSpec._validate_decision("skip")
    with pytest.raises(ValueError, match="minimum cannot exceed maximum"):
        GoldBusinessRuleSpec(column="x", condition="range", minimum=10, maximum=1)



def test_frozen_containers_cover_copy_eq_hash_and_thaw() -> None:
    frozen_list = FrozenList([1, {"k": 2}])
    assert frozen_list[0] == 1
    assert list(frozen_list[1:]) == [{"k": 2}]
    assert frozen_list == [1, {"k": 2}]
    assert repr(frozen_list).startswith("FrozenList")
    assert frozen_list == FrozenList([1, {"k": 2}])
    assert frozen_list != "nope"
    assert hash(frozen_list) == hash(copy(frozen_list))
    assert deepcopy(frozen_list) is frozen_list
    thawed_list = deep_thaw_json(frozen_list)
    assert thawed_list == [1, {"k": 2}]

    frozen_dict = FrozenDict([("a", 1)], b=2)
    assert frozen_dict["a"] == 1
    assert len(frozen_dict) == 2
    assert frozen_dict.__deepcopy__({}) is frozen_dict
    assert deepcopy(frozen_dict) is frozen_dict
    assert dict(frozen_dict) == {"a": 1, "b": 2}
    assert frozen_dict == {"a": 1, "b": 2}
    assert hash(frozen_dict) == hash(copy(frozen_dict))
    assert repr(frozen_dict).startswith("FrozenDict")
    assert frozen_dict != 1
    assert FrozenDict({"a": 1}) == {"a": 1}
    with pytest.raises(TypeError, match="JSON object keys"):
        deep_freeze_json({1: "x"})
    assert deep_freeze_json(frozen_dict) is frozen_dict
    assert deep_thaw_json({"x": FrozenList([1])}) == {"x": [1]}
    assert deep_freeze_json((1, {2})) == (1, {2})
    assert deep_freeze_json({1, 2}) == frozenset({1, 2})

    class _Holder:
        payload: object

    holder = _Holder()
    holder.payload = {"n": [1]}
    freeze_fields(holder, ("payload",))
    assert isinstance(holder.payload, FrozenDict)
    with pytest.raises(TypeError, match="immutable"):
        _immutable()
    with pytest.raises(TypeError, match="JSON object keys"):
        FrozenDict({1: "x"})  # type: ignore[dict-item]


def test_coerce_silver_dq_analyze_request_legacy_and_errors() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    config = SimpleNamespace(name="dq")
    request = SilverDQAnalyzeRequest(
        data=[{"id": 1}],
        run_id="run-1",
        pipeline="chembl_activity",
        target_table="activity",
        source_batch_ids=["b1"],
        config=config,  # type: ignore[arg-type]
        timestamp=timestamp,
        primary_keys=["id"],
    )
    assert coerce_silver_dq_analyze_request(request) is request
    with pytest.raises(TypeError, match="legacy args"):
        coerce_silver_dq_analyze_request(request, args=(1,))
    with pytest.raises(TypeError, match="legacy args"):
        coerce_silver_dq_analyze_request(request, kwargs={"data": []})

    built = coerce_silver_dq_analyze_request(
        kwargs={
            "data": [{"id": 1}],
            "run_id": "run-2",
            "pipeline": "chembl_activity",
            "target_table": "activity",
            "source_batch_ids": ["b1"],
            "config": config,
            "timestamp": timestamp,
            "primary_keys": ["id"],
        }
    )
    assert built.run_id == "run-2"
    assert built.soft_fail_threshold == 0.05

    built_from_args = coerce_silver_dq_analyze_request(
        [{"id": 1}],
        kwargs={
            "run_id": "run-3",
            "pipeline": "chembl_activity",
            "target_table": "activity",
            "source_batch_ids": ["b1"],
            "config": config,
            "timestamp": timestamp,
            "primary_keys": ["id"],
        },
    )
    assert built_from_args.run_id == "run-3"

    with pytest.raises(TypeError, match="too many positional"):
        coerce_silver_dq_analyze_request(
            args=tuple(range(20)),
        )
    with pytest.raises(TypeError, match="multiple values"):
        coerce_silver_dq_analyze_request(
            [{"id": 1}],
            kwargs={"data": [{"id": 2}]},
        )
    with pytest.raises(TypeError, match="unexpected keyword"):
        coerce_silver_dq_analyze_request(
            kwargs={"unknown": 1, "data": []},
        )
    with pytest.raises(TypeError, match="missing required"):
        coerce_silver_dq_analyze_request(kwargs={"data": []})

    positional: list[str] = []
    required: list[str] = []
    defaults: dict[str, object] = {}
    _record_silver_dq_field(
        SimpleNamespace(name="tags", default=MISSING, default_factory=list),  # type: ignore[arg-type]
        positional=positional,
        required=required,
        defaults=defaults,
    )
    assert defaults["tags"] == []
    assert FrozenDict() == {}


def test_observability_pipeline_labels_collapse_unbounded_values() -> None:
    from bioetl.domain.observability_contract import (
        build_observability_contract_payload,
        is_observability_contract_valid,
        normalize_observability_pipeline_label,
    )

    assert normalize_observability_pipeline_label(r"E:\pipelines\chembl_activity__v1_2_3") == (
        "chembl_activity"
    )
    assert (
        normalize_observability_pipeline_label("550e8400-e29b-41d4-a716-446655440000")
        == "unknown"
    )
    assert (
        normalize_observability_pipeline_label("sha256:" + ("ab" * 16)) == "unknown"
    )
    assert normalize_observability_pipeline_label("///") == "unknown"
    payload = build_observability_contract_payload(
        event_name="run_started",
        context={"severity": "error"},
        default_provider="chembl",
        default_pipeline="chembl_activity",
        default_run_id="run-1",
        default_severity="info",
    )
    assert payload.metric_labels["pipeline"] == "chembl_activity"
    assert payload.metric_labels["error_type"] == "unknown"
    assert is_observability_contract_valid(payload.context)

