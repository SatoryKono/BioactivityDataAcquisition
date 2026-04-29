"""Governance registry for semantic-sensitive structured payloads."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "StructuredPayloadRepresentation",
    "StructuredPayloadSemanticPolicy",
    "StructuredPayloadPolicy",
    "semantic_sensitive_structured_payload_policies",
    "structured_payload_policy",
]


class StructuredPayloadRepresentation(StrEnum):
    """Persisted representation used for a structured payload field today."""

    CANONICAL_JSON_STRING = "canonical_json_string"


class StructuredPayloadSemanticPolicy(StrEnum):
    """Forward-migration policy for semantic-sensitive structured payloads."""

    RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM = (
        "raw_json_plus_canonical_json_before_semantic_transform"
    )


@dataclass(frozen=True, slots=True)
class StructuredPayloadPolicy:
    """Contract for one semantic-sensitive structured payload surface."""

    profile_name: str
    field_name: str
    representation: StructuredPayloadRepresentation
    semantic_policy: StructuredPayloadSemanticPolicy
    rationale: str

    @property
    def requires_raw_sidecar_before_semantic_transform(self) -> bool:
        """Return whether future semantic transforms require a raw JSON sidecar."""
        return (
            self.semantic_policy
            is StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM
        )


_POLICIES: tuple[StructuredPayloadPolicy, ...] = (
    StructuredPayloadPolicy(
        profile_name="openalex.publication",
        field_name="grants",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        rationale="Grant objects carry funder/award semantics; future extraction must not overwrite the raw provider envelope.",
    ),
    StructuredPayloadPolicy(
        profile_name="openalex.publication",
        field_name="primary_topic",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        rationale="Primary topic is a structured reference object; ID canonicalization must preserve the provider object if semantics expand.",
    ),
    StructuredPayloadPolicy(
        profile_name="pubmed.publication",
        field_name="affiliation_structured",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        rationale="Structured affiliations may later split identifiers, text, and provenance; the raw provider form remains forensic evidence.",
    ),
    StructuredPayloadPolicy(
        profile_name="pubmed.publication",
        field_name="authors_with_affiliations",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        rationale="Author-affiliation payloads are ordered semantic objects; future transforms need raw and canonical companion fields.",
    ),
    StructuredPayloadPolicy(
        profile_name="uniprot.protein",
        field_name="features_json",
        representation=StructuredPayloadRepresentation.CANONICAL_JSON_STRING,
        semantic_policy=StructuredPayloadSemanticPolicy.RAW_JSON_PLUS_CANONICAL_JSON_BEFORE_SEMANTIC_TRANSFORM,
        rationale="UniProt features are forensic sequence annotations; derived feature projections must keep the raw feature envelope.",
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
