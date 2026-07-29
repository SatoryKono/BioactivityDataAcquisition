# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for normalization profile framework."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles import FieldRule, NormalizationProfile
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_operator,
)


pytestmark = pytest.mark.unit


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
    assert profile.profile_version == "1.0.0"
    assert profile.field_identity("title") is not None
    assert len(profile.identity.profile_hash) == 64


def test_normalization_profile_detects_schema_coverage_gaps() -> None:
    profile = NormalizationProfile(
        profile_name="test.entity",
        field_rules={"title": FieldRule("title")},
    )

    with pytest.raises(ValueError, match="does not cover schema fields exactly"):
        profile.assert_covers_schema({"title", "missing"})


def _operator_normalizer_without_record_param(value: object) -> object:
    """Named normalizer used to prove keyword-only record context is ignored."""
    return normalize_profile_operator(
        value,
        allowed_values=frozenset({"=", ">", "<"}),
    )


def test_field_rule_apply_does_not_treat_keyword_only_params_as_record_context() -> (
    None
):
    rule = FieldRule(
        "standard_relation",
        normalizer=_operator_normalizer_without_record_param,
    )

    assert rule.apply("=", record={"activity_id": "31864"}) == "="
    # Identity must also remain available for named callables (no lambda ban).
    assert "<lambda>" not in rule.identity.normalizer_ref


def test_field_rule_identity_is_stable_for_semantically_equal_rules() -> None:
    left = FieldRule("title")
    right = FieldRule("title")

    assert left.identity == right.identity


def test_normalization_profile_identity_changes_when_field_hash_policy_changes() -> (
    None
):
    left = NormalizationProfile(
        profile_name="test.entity",
        field_rules={"title": FieldRule("title", include_in_hash=True)},
    )
    right = NormalizationProfile(
        profile_name="test.entity",
        field_rules={"title": FieldRule("title", include_in_hash=False)},
    )

    assert left.identity.profile_hash != right.identity.profile_hash
