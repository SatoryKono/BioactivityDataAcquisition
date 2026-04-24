"""Unit tests for normalization profile framework."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_operator,
)


def test_normalization_profile_exposes_hash_and_set_like_views() -> None:
    profile = NormalizationProfile(
        profile_name="test.entity",
        meta_fields=frozenset({"_meta"}),
        field_rules={
            "_meta": FieldRule("_meta", include_in_hash=False),
            "title": FieldRule("title"),
            "tags": FieldRule("tags", include_in_hash=True, set_like=True),
        },
    )

    assert profile.rule_for("title") is not None
    assert profile.hash_included_fields == frozenset({"title", "tags"})
    assert profile.hash_excluded_fields == frozenset({"_meta"})
    assert profile.set_like_fields == frozenset({"tags"})


def test_normalization_profile_detects_schema_coverage_gaps() -> None:
    profile = NormalizationProfile(
        profile_name="test.entity",
        field_rules={"title": FieldRule("title")},
    )

    with pytest.raises(ValueError, match="does not cover schema fields exactly"):
        profile.assert_covers_schema({"title", "missing"})


def test_field_rule_apply_does_not_treat_keyword_only_params_as_record_context() -> None:
    rule = FieldRule(
        "standard_relation",
        normalizer=lambda value: normalize_profile_operator(
            value,
            allowed_values=frozenset({"=", ">", "<"}),
        ),
    )

    assert rule.apply("=", record={"activity_id": "31864"}) == "="
