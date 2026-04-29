"""Tests for publication structured-field governance registry."""

from __future__ import annotations

from bioetl.domain.normalization.publication_structured_fields import (
    CollectionSemantics,
    FieldRepresentation,
    publication_structured_field_policies,
    publication_structured_field_policy,
)


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
