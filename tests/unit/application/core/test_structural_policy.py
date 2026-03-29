"""Unit tests for schema-aware structural policy."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.core.base_transformer.structural_policy import (
    build_structural_policy,
)
from bioetl.domain.config import DQConfig
from bioetl.domain.filtering import SilverFilterConfig
from bioetl.domain.schemas.chembl.activity import ActivitySchema


@pytest.mark.unit
def test_structural_policy_quarantines_missing_required_nonnullable_field() -> None:
    policy = build_structural_policy(
        domain_config=SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=("src_id",)),
            dq=DQConfig(),
        ),
        pandera_silver_schema=ActivitySchema,
    )

    outcome = policy.apply({"activity_id": "A1", "_dq_warn": False, "_dq_error": False})

    assert outcome.should_quarantine is True
    assert outcome.details is not None
    assert outcome.details["reason_code"] == "required_field_missing"
    assert outcome.details["field"] == "src_id"
    assert outcome.details["optional_sources"] == ["silver_required_fields"]


@pytest.mark.unit
def test_structural_policy_coerces_valid_integer_strings() -> None:
    policy = build_structural_policy(
        domain_config=SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=("src_id",)),
            dq=DQConfig(),
        ),
        pandera_silver_schema=ActivitySchema,
    )

    outcome = policy.apply(
        {
            "activity_id": "A1",
            "src_id": "42",
            "_dq_warn": False,
            "_dq_error": False,
        }
    )

    assert outcome.should_quarantine is False
    assert outcome.record["src_id"] == 42


@pytest.mark.unit
def test_structural_policy_quarantines_required_type_mismatch() -> None:
    policy = build_structural_policy(
        domain_config=SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=("src_id",)),
            dq=DQConfig(),
        ),
        pandera_silver_schema=ActivitySchema,
    )

    outcome = policy.apply(
        {
            "activity_id": "A1",
            "src_id": "bad-int",
            "_dq_warn": False,
            "_dq_error": False,
        }
    )

    assert outcome.should_quarantine is True
    assert outcome.details is not None
    assert outcome.details["reason_code"] == "required_field_type_mismatch"
    assert outcome.details["field"] == "src_id"


@pytest.mark.unit
def test_structural_policy_nullifies_nullable_type_mismatch_with_warning() -> None:
    policy = build_structural_policy(
        domain_config=SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=()),
            dq=DQConfig(),
        ),
        pandera_silver_schema=ActivitySchema,
    )

    outcome = policy.apply(
        {
            "activity_id": "A1",
            "manual_curation_flag": "bad-float",
            "_dq_warn": False,
            "_dq_error": False,
        }
    )

    assert outcome.should_quarantine is False
    assert outcome.record["manual_curation_flag"] is None
    assert outcome.record["_dq_warn"] is True
    assert len(outcome.events) == 1
    assert outcome.events[0].level == "warning"
    assert outcome.events[0].event == "silver_structural_type_coerced_to_null"


@pytest.mark.unit
def test_structural_policy_quarantines_optional_nonnullable_type_mismatch() -> None:
    policy = build_structural_policy(
        domain_config=SimpleNamespace(
            silver_filters=SilverFilterConfig(required_fields=()),
            dq=DQConfig(),
        ),
        pandera_silver_schema=ActivitySchema,
    )

    outcome = policy.apply(
        {
            "activity_id": "A1",
            "record_id": "bad-int",
            "_dq_warn": False,
            "_dq_error": False,
        }
    )

    assert outcome.should_quarantine is True
    assert outcome.details is not None
    assert outcome.details["reason_code"] == "optional_nonnullable_field_type_mismatch"
    assert outcome.details["field"] == "record_id"
    assert outcome.details["optional_sources"] == ["default_optional"]
    assert outcome.details["proposed_normalized_outcome"] is None
    assert outcome.details["dq_warn"] is True
    assert outcome.details["dq_error"] is True
    assert [event.level for event in outcome.events] == ["warning", "error"]
