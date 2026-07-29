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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Tests for publication structured-field governance registry."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.publication_structured_fields import (
    CollectionSemantics,
    FieldRepresentation,
    publication_structured_field_policies,
    publication_structured_field_policy,
)
from bioetl.domain.normalization.reference_ids import reference_identifier_family
from bioetl.domain.normalization.profiles import (
    CROSSREF_PUBLICATION_PROFILE,
    OPENALEX_PUBLICATION_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
)

pytestmark = pytest.mark.unit

_PUBLICATION_PROFILES = (
    CROSSREF_PUBLICATION_PROFILE,
    OPENALEX_PUBLICATION_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
)


def _profile_structured_fields() -> set[tuple[str, str]]:
    structured_fields: set[tuple[str, str]] = set()
    for profile in _PUBLICATION_PROFILES:
        for field_name, rule in profile.field_rules.items():
            notes = (rule.notes or "").casefold()
            if rule.set_like or "json" in notes:
                structured_fields.add((profile.profile_name, field_name))
    return structured_fields


def test_publication_structured_field_registry_declares_identifier_arrays() -> None:
    policy = publication_structured_field_policy(
        "openalex.publication",
        "author_openalex_ids",
    )

    assert policy is not None
    assert policy.representation is FieldRepresentation.CANONICAL_JSON_STRING
    assert policy.collection_semantics is CollectionSemantics.UNORDERED_SET
    assert policy.identifier_family == "openalex_author"
    assert policy.hash_ordering == "set_like"


def test_publication_structured_field_registry_declares_raw_sidecars() -> None:
    policy = publication_structured_field_policy(
        "pubmed.publication",
        "publication_types",
    )

    assert policy is not None
    assert policy.raw_sidecar_field == "publication_type"
    assert policy.collection_semantics is CollectionSemantics.UNORDERED_SET


def test_publication_structured_field_registry_has_unique_keys() -> None:
    policies = publication_structured_field_policies()
    keys = {(policy.profile_name, policy.field_name) for policy in policies}

    assert len(keys) == len(policies)


def test_publication_structured_field_registry_covers_profile_structured_fields() -> (
    None
):
    registry_keys = {
        (policy.profile_name, policy.field_name)
        for policy in publication_structured_field_policies()
    }

    assert _profile_structured_fields() <= registry_keys


def test_publication_structured_field_registry_matches_profile_hash_ordering() -> None:
    policies_by_key = {
        (policy.profile_name, policy.field_name): policy
        for policy in publication_structured_field_policies()
    }

    for profile in _PUBLICATION_PROFILES:
        for field_name, rule in profile.field_rules.items():
            policy = policies_by_key.get((profile.profile_name, field_name))
            if policy is None:
                continue

            expected = (
                CollectionSemantics.UNORDERED_SET
                if rule.set_like
                else CollectionSemantics.ORDERED_SEQUENCE
            )
            assert policy.collection_semantics is expected


def test_publication_structured_field_identifier_families_are_registered() -> None:
    for policy in publication_structured_field_policies():
        if policy.identifier_family is None:
            continue

        assert reference_identifier_family(policy.identifier_family).name == (
            policy.identifier_family
        )


def test_publication_structured_field_policy_returns_none_for_unknown_field() -> None:
    policy = publication_structured_field_policy(
        "unknown.profile",
        "unknown_field",
    )
    assert policy is None


def test_field_representation_enum_values() -> None:
    assert FieldRepresentation.CANONICAL_JSON_STRING == "canonical_json_string"
    assert FieldRepresentation.SCALAR_STRING == "scalar_string"


def test_collection_semantics_enum_values() -> None:
    assert CollectionSemantics.ORDERED_SEQUENCE == "ordered_sequence"
    assert CollectionSemantics.UNORDERED_SET == "unordered_set"
    assert CollectionSemantics.RAW_PROVIDER_VALUE == "raw_provider_value"


def test_hash_ordering_property() -> None:
    policy = publication_structured_field_policy(
        "crossref.publication",
        "authors",
    )
    assert policy is not None
    assert policy.hash_ordering == "order_sensitive"

    policy_set = publication_structured_field_policy(
        "crossref.publication",
        "author_orcids",
    )
    assert policy_set is not None
    assert policy_set.hash_ordering == "set_like"
