# pyright: reportArgumentType=false
"""Focused tests for CR stream residuals #8643/#8644/#8645."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.behavior.staged_enforcement import (
    EnforcementPolicy,
    EnforcementStage,
)
from bioetl.domain.behavior.validation_helpers import validate_data
from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.behavior._dq_serializer_html._renderers import (
    _render_raw_data_card,
    status_color_class,
)
from bioetl.domain.composite.result_enrichment import EnrichmentResult, EnrichmentStatus
from bioetl.domain.composite.result_merge import MergeResult
from bioetl.domain.composite.result_seed_dependency import DependencyResult, SeedResult
from bioetl.domain.config.base_provider import BaseProviderConfig
from bioetl.domain.composite.aggregation import (
    AggregationConfig,
    AggregationFieldSpec,
    AggregationFunction,
)
from bioetl.domain.config.runtime import RuntimeConfig
from bioetl.domain.types import RunType
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


def test_base_provider_config_hides_api_key_in_repr() -> None:
    cfg = BaseProviderConfig(base_url="https://example.com", api_key="secret-key")
    text = repr(cfg)
    assert "secret-key" not in text


def test_seed_and_dependency_results_reject_negative_counters() -> None:
    with pytest.raises(ValueError, match="records_extracted"):
        SeedResult(pipeline_name="p", records_extracted=-1)
    with pytest.raises(ValueError, match="duration_seconds"):
        DependencyResult(pipeline_name="p", duration_seconds=math.nan)


def test_merge_result_rejects_negative_and_inconsistent_counts() -> None:
    with pytest.raises(ValueError, match="records_merged"):
        MergeResult(records_merged=-1)
    with pytest.raises(ValueError, match="records_fully_enriched"):
        MergeResult(records_merged=1, records_enriched=1, records_fully_enriched=2)


def test_enrichment_result_bounds_errored_and_finite_duration() -> None:
    with pytest.raises(ValueError, match="records_errored"):
        EnrichmentResult(
            enricher_name="p",
            status=EnrichmentStatus.SUCCESS,
            records_input=1,
            records_errored=2,
        )
    with pytest.raises(ValueError, match="duration_seconds"):
        EnrichmentResult(
            enricher_name="p",
            status=EnrichmentStatus.SUCCESS,
            records_input=1,
            duration_seconds=math.inf,
        )


def test_aggregation_rejects_rhs_operators_and_bad_fields_type() -> None:
    with pytest.raises(ValueError, match="additional operators"):
        AggregationFieldSpec(
            source_field="v",
            agg_function=AggregationFunction.COUNT,
            filter_condition="x == 1 AND y == 2",
        )
    with pytest.raises(ValueError, match="sequence"):
        AggregationConfig(
            group_by="g",
            fields="not-a-sequence",  # type: ignore[arg-type]
        )


def test_runtime_lock_ttl_positive() -> None:
    with pytest.raises(ValueError, match="lock_ttl"):
        RuntimeConfig(run_type=RunType.REBUILD, lock_ttl=0)
