"""Tests for semantic-sensitive structured payload policy registry."""

from __future__ import annotations

from bioetl.domain.normalization.structured_payload_policies import (
    StructuredPayloadCollectionSemantics,
    StructuredPayloadRepresentation,
    semantic_sensitive_structured_payload_policies,
    structured_payload_policy,
)


def test_semantic_sensitive_payload_registry_declares_raw_sidecar_migration_policy() -> (
    None
):
    governed_fields = {
        ("openalex.publication", "grants"),
        ("openalex.publication", "primary_topic"),
        ("pubmed.publication", "affiliation_structured"),
        ("pubmed.publication", "authors_with_affiliations"),
        ("semanticscholar.publication", "author_h_indices"),
        ("semanticscholar.publication", "citation_contexts"),
        ("semanticscholar.publication", "publication_types"),
        ("semanticscholar.publication", "subject_fields"),
        ("uniprot.protein", "features_json"),
    }

    for profile_name, field_name in governed_fields:
        policy = structured_payload_policy(profile_name, field_name)

        assert policy is not None
        assert (
            policy.representation
            is StructuredPayloadRepresentation.CANONICAL_JSON_STRING
        )
        assert policy.requires_raw_sidecar_before_semantic_transform is True
        assert policy.raw_sidecar_field.endswith("_raw_json")
        assert policy.canonical_sidecar_field.endswith("_canonical_json")
        assert policy.raw_sidecar_field != policy.field_name
        assert policy.canonical_sidecar_field != policy.field_name


def test_semantic_sensitive_payload_registry_has_unique_keys() -> None:
    policies = semantic_sensitive_structured_payload_policies()
    keys = {(policy.profile_name, policy.field_name) for policy in policies}

    assert len(keys) == len(policies)


def test_semantic_sensitive_payload_registry_classifies_collection_semantics() -> None:
    expected_semantics = {
        (
            "openalex.publication",
            "grants",
        ): StructuredPayloadCollectionSemantics.UNORDERED_SET,
        (
            "openalex.publication",
            "primary_topic",
        ): StructuredPayloadCollectionSemantics.STRUCTURED_OBJECT,
        (
            "pubmed.publication",
            "affiliation_structured",
        ): StructuredPayloadCollectionSemantics.UNORDERED_SET,
        (
            "pubmed.publication",
            "authors_with_affiliations",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        (
            "semanticscholar.publication",
            "author_h_indices",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        (
            "semanticscholar.publication",
            "citation_contexts",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        (
            "semanticscholar.publication",
            "publication_types",
        ): StructuredPayloadCollectionSemantics.UNORDERED_SET,
        (
            "semanticscholar.publication",
            "subject_fields",
        ): StructuredPayloadCollectionSemantics.UNORDERED_SET,
        (
            "uniprot.protein",
            "features_json",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
    }

    for key, expected in expected_semantics.items():
        policy = structured_payload_policy(*key)

        assert policy is not None
        assert policy.collection_semantics is expected
