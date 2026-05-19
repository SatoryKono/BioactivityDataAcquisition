"""Governance registry for semantic-sensitive structured payloads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "StructuredPayloadCollectionSemantics",
    "StructuredPayloadPolicy",
    "StructuredPayloadRepresentation",
    "StructuredPayloadSemanticPolicy",
    "semantic_sensitive_structured_payload_policies",
    "structured_payload_policy",
]


class StructuredPayloadRepresentation(StrEnum):
    """Persisted representation used for a structured payload field today."""

    CANONICAL_JSON_STRING = "canonical_json_string"


class StructuredPayloadCollectionSemantics(StrEnum):
    """Ordering semantics for semantic-sensitive structured JSON payloads."""

    ORDERED_SEQUENCE = "ordered_sequence"
    UNORDERED_SET = "unordered_set"
    STRUCTURED_OBJECT = "structured_object"


class StructuredPayloadSemanticPolicy(StrEnum):
    """Forward-migration policy for semantic-sensitive structured payloads."""

    RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM = (
        "raw_json_plus_canonical_json_before_semantic_transform"
    )
    CANONICAL_JSON_BIBLIOGRAPHIC_EVIDENCE = "canonical_json_bibliographic_evidence"
    HASHED_PII_CANONICAL_JSON_ONLY = "hashed_pii_canonical_json_only"
    CANONICAL_JSON_COMMENT_PROJECTION = "canonical_json_comment_projection"


@dataclass(frozen=True, slots=True)
class StructuredPayloadPolicy:
    """Contract for one semantic-sensitive structured payload surface."""

    profile_name: str
    field_name: str
    representation: StructuredPayloadRepresentation
    collection_semantics: StructuredPayloadCollectionSemantics
    semantic_policy: StructuredPayloadSemanticPolicy
    raw_sidecar_field: str | None
    canonical_sidecar_field: str | None
    rationale: str
    controlled_vocabulary_source: str | None = None

    @property
    def requires_raw_sidecar_before_semantic_transform(self) -> bool:
        """Return whether future semantic transforms require a raw JSON sidecar."""
        return (
            self.semantic_policy
            is StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM
        )

    @property
    def uses_canonical_json_only(self) -> bool:
        """Return whether the persisted field itself is the ratified evidence surface."""
        return not self.requires_raw_sidecar_before_semantic_transform


_SEMANTICSCHOLAR_PROFILE = "semanticscholar.publication"

_POLICIES: tuple[StructuredPayloadPolicy, ...] = (
    StructuredPayloadPolicy(
        profile_name="crossref.publication",
        field_name="author_details",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.HASHED_PII_CANONICAL_JSON_ONLY,
        raw_sidecar_field=None,
        canonical_sidecar_field="author_details",
        rationale=(
            "CrossRef author-detail payloads already persist a hashed-PII-safe "
            "canonical JSON evidence surface; no separate raw companion is shipped."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name="crossref.publication",
        field_name="references",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.CANONICAL_JSON_BIBLIOGRAPHIC_EVIDENCE,
        raw_sidecar_field=None,
        canonical_sidecar_field="references",
        rationale=(
            "CrossRef bibliographic reference objects are persisted as the ratified "
            "canonical JSON evidence surface without a dedicated raw sidecar."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name="openalex.publication",
        field_name="grants",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.UNORDERED_SET,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="grants_raw_json",
        canonical_sidecar_field="grants_canonical_json",
        rationale=(
            "Grant objects carry funder/award semantics; future extraction must "
            "not overwrite the raw provider envelope."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name="openalex.publication",
        field_name="primary_topic",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.STRUCTURED_OBJECT,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="primary_topic_raw_json",
        canonical_sidecar_field="primary_topic_canonical_json",
        rationale=(
            "Primary topic is a structured reference object; ID canonicalization "
            "must preserve the provider object if semantics expand."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name="pubmed.publication",
        field_name="affiliation_structured",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.UNORDERED_SET,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="affiliation_structured_raw_json",
        canonical_sidecar_field="affiliation_structured_canonical_json",
        rationale=(
            "Structured affiliations may later split identifiers, text, and "
            "provenance; the raw provider form remains forensic evidence."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name="pubmed.publication",
        field_name="authors_with_affiliations",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="authors_with_affiliations_raw_json",
        canonical_sidecar_field="authors_with_affiliations_canonical_json",
        rationale=(
            "Author-affiliation payloads are ordered semantic objects; future "
            "transforms need raw and canonical companion fields."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name=_SEMANTICSCHOLAR_PROFILE,
        field_name="author_h_indices",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="author_h_indices_raw_json",
        canonical_sidecar_field="author_h_indices_canonical_json",
        rationale=(
            "Author h-index values are positionally aligned to the author list; "
            "canonical JSON cannot replace the raw provider ordering evidence."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name=_SEMANTICSCHOLAR_PROFILE,
        field_name="citation_contexts",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="citation_contexts_raw_json",
        canonical_sidecar_field="citation_contexts_canonical_json",
        rationale=(
            "Citation context snippets are provider-ordered textual evidence; "
            "semantic extraction must retain the raw snippet payload."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name=_SEMANTICSCHOLAR_PROFILE,
        field_name="publication_types",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.UNORDERED_SET,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="publication_types_raw_json",
        canonical_sidecar_field="publication_types_canonical_json",
        rationale=(
            "Publication type labels are set-like classification evidence; "
            "canonical terms must not erase raw provider labels."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name=_SEMANTICSCHOLAR_PROFILE,
        field_name="subject_fields",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.UNORDERED_SET,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="subject_fields_raw_json",
        canonical_sidecar_field="subject_fields_canonical_json",
        rationale=(
            "Subject fields are set-like classification evidence; downstream "
            "taxonomy mapping needs canonical JSON plus the raw provider labels."
        ),
    ),
    StructuredPayloadPolicy(
        profile_name="uniprot.protein",
        field_name="alternative_products",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="alternative_products_raw_json",
        canonical_sidecar_field="alternative_products_canonical_json",
        rationale=(
            "Alternative-product comment payloads encode isoform semantics that may "
            "later split into dedicated entities; retain raw provider comments plus "
            "deterministic canonical companions before any semantic promotion."
        ),
        controlled_vocabulary_source="configs/vocab/uniprot_semantic_payloads.yaml",
    ),
    StructuredPayloadPolicy(
        profile_name="uniprot.protein",
        field_name="biophysicochemical_properties",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="biophysicochemical_properties_raw_json",
        canonical_sidecar_field="biophysicochemical_properties_canonical_json",
        rationale=(
            "Biophysicochemical-property comments contain nested measurement and "
            "note semantics; retain raw comment envelopes plus canonical companions "
            "before future semantic extraction expands the contract."
        ),
        controlled_vocabulary_source="configs/vocab/uniprot_semantic_payloads.yaml",
    ),
    StructuredPayloadPolicy(
        profile_name="uniprot.protein",
        field_name="cofactors",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.UNORDERED_SET,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="cofactors_raw_json",
        canonical_sidecar_field="cofactors_canonical_json",
        rationale=(
            "Cofactor comments mix identifiers and free-text notes; preserve the raw "
            "provider envelope plus canonical set-like companions before semantic "
            "splits or vocabulary enrichment."
        ),
        controlled_vocabulary_source="configs/vocab/uniprot_semantic_payloads.yaml",
    ),
    StructuredPayloadPolicy(
        profile_name="uniprot.protein",
        field_name="features_json",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="features_raw_json",
        canonical_sidecar_field="features_canonical_json",
        rationale=(
            "UniProt features are forensic sequence annotations; derived feature "
            "projections must keep the raw feature envelope."
        ),
        controlled_vocabulary_source="configs/vocab/uniprot_semantic_payloads.yaml",
    ),
    StructuredPayloadPolicy(
        profile_name="uniprot.protein",
        field_name="reactions",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        collection_semantics=StructuredPayloadCollectionSemantics.ORDERED_SEQUENCE,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        raw_sidecar_field="reactions_raw_json",
        canonical_sidecar_field="reactions_canonical_json",
        rationale=(
            "Catalytic-activity comments drive derived reaction fields; preserve raw "
            "provider comments plus canonical companions before expanding reaction "
            "semantics or downstream derived entities."
        ),
        controlled_vocabulary_source="configs/vocab/uniprot_semantic_payloads.yaml",
    ),
)

_POLICY_BY_FIELD = {
    (policy.profile_name, policy.field_name): policy for policy in _POLICIES
}


def semantic_sensitive_structured_payload_policies() -> tuple[
    StructuredPayloadPolicy, ...
]:
    """Return governed semantic-sensitive structured payload policies."""
    return _POLICIES


def structured_payload_policy(
    profile_name: str,
    field_name: str,
) -> StructuredPayloadPolicy | None:
    """Return one structured payload policy, if governed."""
    return _POLICY_BY_FIELD.get((profile_name, field_name))
