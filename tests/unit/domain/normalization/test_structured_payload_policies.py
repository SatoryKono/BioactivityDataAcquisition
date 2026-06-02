"""Tests for semantic-sensitive structured payload policy registry."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.structured_payload_policies import (
    StructuredPayloadCollectionSemantics,
    StructuredPayloadSemanticPolicy,
    StructuredPayloadRepresentation,
    semantic_sensitive_structured_payload_policies,
    structured_payload_policy,
)


pytestmark = pytest.mark.unit


def test_semantic_sensitive_payload_registry_declares_reviewed_policy_shapes() -> None:
    raw_sidecar_fields = {
        ("crossref.publication", "author_details"),
        ("crossref.publication", "references"),
        ("openalex.publication", "grants"),
        ("openalex.publication", "primary_topic"),
        ("pubmed.publication", "affiliation_structured"),
        ("pubmed.publication", "authors_with_affiliations"),
        ("semanticscholar.publication", "author_h_indices"),
        ("semanticscholar.publication", "citation_contexts"),
        ("semanticscholar.publication", "publication_types"),
        ("semanticscholar.publication", "subject_fields"),
        ("uniprot.protein", "alternative_products"),
        ("uniprot.protein", "biophysicochemical_properties"),
        ("uniprot.protein", "cofactors"),
        ("uniprot.protein", "features_json"),
        ("uniprot.protein", "reactions"),
    }
    canonical_only_fields: set[tuple[str, str]] = set()

    for profile_name, field_name in raw_sidecar_fields | canonical_only_fields:
        policy = structured_payload_policy(profile_name, field_name)

        assert policy is not None
        assert (
            policy.representation
            is StructuredPayloadRepresentation.CANONICAL_JSON_STRING
        )

        if (profile_name, field_name) in raw_sidecar_fields:
            assert policy.requires_raw_sidecar_before_semantic_transform is True
            assert policy.raw_sidecar_field is not None
            assert policy.raw_sidecar_field.endswith("_raw_json")
            assert policy.canonical_sidecar_field is not None
            assert policy.canonical_sidecar_field.endswith("_canonical_json")
            assert policy.raw_sidecar_field != policy.field_name
            assert policy.canonical_sidecar_field != policy.field_name
        else:
            assert policy.uses_canonical_json_only is True
            assert policy.raw_sidecar_field is None
            assert policy.canonical_sidecar_field == policy.field_name


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
            "crossref.publication",
            "author_details",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        (
            "crossref.publication",
            "references",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
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
            "alternative_products",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        (
            "uniprot.protein",
            "biophysicochemical_properties",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        (
            "uniprot.protein",
            "cofactors",
        ): StructuredPayloadCollectionSemantics.UNORDERED_SET,
        (
            "uniprot.protein",
            "features_json",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        (
            "uniprot.protein",
            "reactions",
        ): StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
    }

    for key, expected in expected_semantics.items():
        policy = structured_payload_policy(*key)

        assert policy is not None
        assert policy.collection_semantics is expected


def test_semantic_sensitive_payload_registry_exposes_canonical_only_semantic_modes() -> (
    None
):
    crossref_references = structured_payload_policy(
        "crossref.publication", "references"
    )
    assert crossref_references is not None
    assert (
        crossref_references.semantic_policy
        is StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM
    )

    crossref_author_details = structured_payload_policy(
        "crossref.publication",
        "author_details",
    )
    assert crossref_author_details is not None
    assert (
        crossref_author_details.semantic_policy
        is StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM
    )

    uniprot_alternative_products = structured_payload_policy(
        "uniprot.protein",
        "alternative_products",
    )
    assert uniprot_alternative_products is not None
    assert (
        uniprot_alternative_products.semantic_policy
        is StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM
    )
