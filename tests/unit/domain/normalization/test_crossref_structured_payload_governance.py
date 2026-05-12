"""Governance checks for CrossRef structured publication payloads."""

from __future__ import annotations

from bioetl.domain.normalization.publication_structured_fields import (
    CollectionSemantics,
    FieldRepresentation,
    publication_structured_field_policy,
)

_CROSSREF_PUBLICATION_CONFIG = {
    "author_details": {
        "representation": "canonical_json_string",
        "collection_semantics": "ordered_sequence",
        "raw_sidecar_strategy": "intentionally_not_persisted_after_pii_hash",
        "pii_mode": "hashed_personal_fields_only",
    },
    "references": {
        "representation": "canonical_json_string",
        "collection_semantics": "ordered_sequence",
        "raw_sidecar_strategy": "canonical_json_only",
    },
}


def test_crossref_structured_payload_registry_explicitly_governs_canonical_only_fields() -> (
    None
):
    fields = _CROSSREF_PUBLICATION_CONFIG

    for field_name in ("author_details", "references"):
        policy = publication_structured_field_policy("crossref.publication", field_name)

        assert policy is not None
        assert policy.representation is FieldRepresentation.CANONICAL_JSON_STRING
        assert policy.collection_semantics is CollectionSemantics.ORDERED_SEQUENCE
        assert policy.raw_sidecar_field is None
        assert fields[field_name]["representation"] == "canonical_json_string"
        assert fields[field_name]["collection_semantics"] == "ordered_sequence"


def test_crossref_author_details_governance_records_hashed_pii_reason() -> None:
    author_details = _CROSSREF_PUBLICATION_CONFIG["author_details"]

    assert (
        author_details["raw_sidecar_strategy"]
        == "intentionally_not_persisted_after_pii_hash"
    )
    assert author_details["pii_mode"] == "hashed_personal_fields_only"


def test_crossref_references_governance_records_canonical_only_reason() -> None:
    references = _CROSSREF_PUBLICATION_CONFIG["references"]

    assert references["raw_sidecar_strategy"] == "canonical_json_only"
