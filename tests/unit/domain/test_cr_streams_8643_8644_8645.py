# pyright: reportArgumentType=false
"""Focused behavior tests for CR stream residuals #8643/#8644/#8645."""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from bioetl.domain.behavior._dq_serializer_html._renderers import (
    _render_raw_data_card,
    status_color_class,
)
from bioetl.domain.behavior.staged_enforcement import (
    EnforcementPolicy,
    EnforcementStage,
)
from bioetl.domain.behavior.validation_helpers import validate_data
from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.value_objects import ActivityType

pytestmark = pytest.mark.unit


def test_enforcement_policy_defaults_keep_soft_fail_reachable() -> None:
    policy = EnforcementPolicy(
        check_name="x",
        current_stage=EnforcementStage.SOFT_FAIL,
    )
    assert policy.warning_threshold < policy.failure_threshold
    assert policy.get_effective_stage(0.0) == EnforcementStage.OBSERVE
    assert policy.get_effective_stage(0.6) == EnforcementStage.SOFT_FAIL
    assert policy.get_effective_stage(0.9) == EnforcementStage.HARD_FAIL


def test_enforcement_policy_rejects_inverted_thresholds() -> None:
    with pytest.raises(ValueError, match="warning_threshold must be strictly below"):
        EnforcementPolicy(
            check_name="x",
            current_stage=EnforcementStage.OBSERVE,
            failure_threshold=0.2,
            warning_threshold=0.5,
        )


def test_validate_data_rejects_empty_frozenset() -> None:
    with pytest.raises(ValueError, match="Data is empty"):
        validate_data(frozenset())


def test_value_validator_percent_inhibition_before_unit_path() -> None:
    validator = ValueValidator()
    ok, err = validator.validate_activity_value(
        50.0, ActivityType.PERCENT_INHIBITION, unit="nM"
    )
    assert ok is True
    assert err is None
    bad, err2 = validator.validate_activity_value(
        150.0, ActivityType.PERCENT_INHIBITION, unit="nM"
    )
    assert bad is False
    assert err2 is not None


def test_value_validator_rejects_non_finite_concentration_bounds() -> None:
    validator = ValueValidator()
    with pytest.raises(ValueError, match="finite"):
        validator.set_concentration_range("nM", math.nan, 10.0)
    with pytest.raises(ValueError, match="finite"):
        validator.set_concentration_range("nM", 0.0, math.inf)


def test_status_color_class_uses_warn_selector() -> None:
    assert status_color_class("warn") == "warn"
    assert status_color_class("warning") == "warn"


def test_render_raw_data_card_fail_soft_on_non_serializable() -> None:
    html = _render_raw_data_card({"value": {1, 2, 3}})
    assert "raw_data_not_serializable" in html or "Raw Report Data" in html


def test_enforcement_policy_rejects_out_of_range_thresholds() -> None:
    with pytest.raises(ValueError, match="warning_threshold"):
        EnforcementPolicy(
            check_name="x",
            current_stage=EnforcementStage.SOFT_FAIL,
            warning_threshold=-0.1,
            failure_threshold=0.8,
        )
    with pytest.raises(ValueError, match="failure_threshold"):
        EnforcementPolicy(
            check_name="x",
            current_stage=EnforcementStage.SOFT_FAIL,
            warning_threshold=0.5,
            failure_threshold=1.1,
        )


def test_conditional_required_incomplete_raises_validation_error() -> None:
    from bioetl.domain.behavior._dq_rule_evaluators_cross import (
        _conditional_required_rule_violated,
    )
    from bioetl.domain.exceptions import ValidationError

    rule = SimpleNamespace(trigger_field=None, required_field="x")
    with pytest.raises(ValidationError, match="conditional_required"):
        _conditional_required_rule_violated({"x": 1}, rule, present_count=1)
