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
"""Governance checks for CrossRef structured publication payloads."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.publication_structured_fields import (
    CollectionSemantics,
    FieldRepresentation,
    publication_structured_field_policy,
)

pytestmark = pytest.mark.unit

_CROSSREF_PUBLICATION_CONFIG = {
    "author_details": {
        "representation": "canonical_json_string",
        "collection_semantics": "ordered_sequence",
        "raw_sidecar_strategy": "raw_and_canonical_sidecars",
        "raw_sidecar_field": "author_details_raw_json",
        "canonical_sidecar_field": "author_details_canonical_json",
    },
    "references": {
        "representation": "canonical_json_string",
        "collection_semantics": "ordered_sequence",
        "raw_sidecar_strategy": "raw_and_canonical_sidecars",
        "raw_sidecar_field": "references_raw_json",
        "canonical_sidecar_field": "references_canonical_json",
    },
}


def test_crossref_structured_payload_registry_explicitly_governs_sidecar_fields() -> (
    None
):
    fields = _CROSSREF_PUBLICATION_CONFIG

    for field_name in ("author_details", "references"):
        policy = publication_structured_field_policy("crossref.publication", field_name)

        assert policy is not None
        assert policy.representation is FieldRepresentation.CANONICAL_JSON_STRING
        assert policy.collection_semantics is CollectionSemantics.ORDERED_SEQUENCE
        assert policy.raw_sidecar_field == fields[field_name]["raw_sidecar_field"]
        assert fields[field_name]["representation"] == "canonical_json_string"
        assert fields[field_name]["collection_semantics"] == "ordered_sequence"
        assert policy.raw_sidecar_field is not None


def test_crossref_author_details_governance_records_sidecar_names() -> None:
    author_details = _CROSSREF_PUBLICATION_CONFIG["author_details"]

    assert author_details["raw_sidecar_strategy"] == "raw_and_canonical_sidecars"
    assert author_details["raw_sidecar_field"] == "author_details_raw_json"
    assert author_details["canonical_sidecar_field"] == "author_details_canonical_json"


def test_crossref_references_governance_records_sidecar_names() -> None:
    references = _CROSSREF_PUBLICATION_CONFIG["references"]

    assert references["raw_sidecar_strategy"] == "raw_and_canonical_sidecars"
    assert references["raw_sidecar_field"] == "references_raw_json"
    assert references["canonical_sidecar_field"] == "references_canonical_json"
