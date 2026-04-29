"""Registry for publication structured-field representation semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "CollectionSemantics",
    "FieldRepresentation",
    "PublicationStructuredFieldPolicy",
    "publication_structured_field_policies",
    "publication_structured_field_policy",
]


class FieldRepresentation(StrEnum):
    """Persisted representation for a structured publication field."""

    CANONICAL_JSON_STRING = "canonical_json_string"
    SCALAR_STRING = "scalar_string"


class CollectionSemantics(StrEnum):
    """Semantic ordering contract for collection-like publication fields."""

    ORDERED_SEQUENCE = "ordered_sequence"
    UNORDERED_SET = "unordered_set"
    RAW_PROVIDER_VALUE = "raw_provider_value"


@dataclass(frozen=True, slots=True)
class PublicationStructuredFieldPolicy:
    """Governance record for one publication structured field."""

    profile_name: str
    field_name: str
    representation: FieldRepresentation
    collection_semantics: CollectionSemantics
    identifier_family: str | None = None
    raw_sidecar_field: str | None = None

    @property
    def hash_ordering(self) -> str:
        """Return the content-hash ordering label for generated evidence."""
        if self.collection_semantics is CollectionSemantics.UNORDERED_SET:
            return "set_like"
        if self.collection_semantics is CollectionSemantics.ORDERED_SEQUENCE:
            return "order_sensitive"
        return "raw_provider_value"


_POLICIES: tuple[PublicationStructuredFieldPolicy, ...] = (
    PublicationStructuredFieldPolicy(
        "crossref.publication",
        "author_orcids",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="orcid",
    ),
    PublicationStructuredFieldPolicy(
        "crossref.publication",
        "issn_list",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="issn",
    ),
    PublicationStructuredFieldPolicy(
        "openalex.publication",
        "author_openalex_ids",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="openalex_author",
    ),
    PublicationStructuredFieldPolicy(
        "openalex.publication",
        "author_orcids",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="orcid",
    ),
    PublicationStructuredFieldPolicy(
        "openalex.publication",
        "institution_ids",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="openalex_institution",
    ),
    PublicationStructuredFieldPolicy(
        "openalex.publication",
        "ror_ids",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="ror",
    ),
    PublicationStructuredFieldPolicy(
        "pubmed.publication",
        "author_orcids",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="orcid",
    ),
    PublicationStructuredFieldPolicy(
        "pubmed.publication",
        "publication_type_list",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        raw_sidecar_field="publication_type",
    ),
    PublicationStructuredFieldPolicy(
        "pubmed.publication",
        "publication_types",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        raw_sidecar_field="publication_type",
    ),
    PublicationStructuredFieldPolicy(
        "semanticscholar.publication",
        "author_orcids",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="orcid",
    ),
    PublicationStructuredFieldPolicy(
        "semanticscholar.publication",
        "author_s2_ids",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        identifier_family="semantic_scholar_author",
    ),
    PublicationStructuredFieldPolicy(
        "semanticscholar.publication",
        "publication_types",
        FieldRepresentation.CANONICAL_JSON_STRING,
        CollectionSemantics.UNORDERED_SET,
        raw_sidecar_field="publication_type",
    ),
)

_POLICY_BY_FIELD = {
    (policy.profile_name, policy.field_name): policy for policy in _POLICIES
}


def publication_structured_field_policies() -> tuple[PublicationStructuredFieldPolicy, ...]:
    """Return all governed publication structured-field policies."""
    return _POLICIES


def publication_structured_field_policy(
    profile_name: str,
    field_name: str,
) -> PublicationStructuredFieldPolicy | None:
    """Return the policy for one profile field, if explicitly governed."""
    return _POLICY_BY_FIELD.get((profile_name, field_name))
