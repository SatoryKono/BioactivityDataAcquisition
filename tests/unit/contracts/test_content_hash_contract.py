"""Contract tests for content-hash normalization and exclusion rules."""

from __future__ import annotations

import pytest

from datetime import datetime

from bioetl.domain.behavior import EntityIdentityGenerator
from bioetl.domain.normalization.profiles import (
    OPENALEX_PUBLICATION_PROFILE,
    PUBMED_PUBLICATION_PROFILE,
    SEMANTICSCHOLAR_PUBLICATION_PROFILE,
    UNIPROT_PROTEIN_PROFILE,
)
from bioetl.domain.transformations import generate_content_hash


pytestmark = pytest.mark.unit

def test_content_hash_normalization_contract() -> None:
    """Hash MUST be stable across normalization-equivalent values."""
    service = EntityIdentityGenerator()

    record_a = {
        "name": "  Alpha  ",
        "score": 3.141592653589793,
        "measured_at": datetime(2025, 1, 1, 10, 0, 0),
    }
    record_b = {
        "name": "Alpha",
        "score": 3.1415926536,
        "measured_at": datetime(2025, 1, 1, 10, 0, 0),
    }

    assert service.compute_content_hash(
        "chembl", record_a
    ) == service.compute_content_hash("chembl", record_b)


def test_content_hash_v1_date_policy_collapses_same_calendar_day() -> None:
    """Legacy v1_date policy MUST collapse datetimes to calendar day only."""
    service = EntityIdentityGenerator()

    record_a = {
        "name": "Alpha",
        "measured_at": datetime(2025, 1, 1, 10, 0, 0),
    }
    record_b = {
        "name": "Alpha",
        "measured_at": datetime(2025, 1, 1, 22, 15, 0),
    }

    assert service.compute_content_hash(
        "chembl", record_a, datetime_policy="v1_date"
    ) == service.compute_content_hash("chembl", record_b, datetime_policy="v1_date")


def test_content_hash_excludes_meta_and_dq_prefix_contract() -> None:
    """Meta fields and _dq_* fields MUST NOT influence content hash."""
    service = EntityIdentityGenerator()

    base = {"activity_id": "A1", "value": 10}
    with_meta = {
        **base,
        "_run_id": "run-1",
        "_ingestion_ts": "2026-01-01T00:00:00Z",
        "_dq_custom_check": "warn",
    }

    assert service.compute_content_hash("chembl", base) == service.compute_content_hash(
        "chembl", with_meta
    )


def test_content_hash_excludes_occurrence_only_source_batch_id_contract() -> None:
    """Occurrence-only BatchID lineage metadata MUST NOT alter semantic identity."""
    service = EntityIdentityGenerator()

    base = {"activity_id": "A1", "value": 10}
    with_batch_a = {
        **base,
        "_source_batch_id": "11111111-1111-1111-1111-111111111111",
    }
    with_batch_b = {
        **base,
        "_source_batch_id": "22222222-2222-2222-2222-222222222222",
    }

    assert service.compute_content_hash(
        "chembl", with_batch_a
    ) == service.compute_content_hash("chembl", with_batch_b)


def test_content_hash_service_matches_canonical_transform_contract() -> None:
    """EntityIdentityGenerator MUST delegate to the canonical transformation path."""
    service = EntityIdentityGenerator()
    record = {
        "activity_id": "A1",
        "value": 10,
        "comment": "  stable  ",
        "nested": {"b": 2, "a": 1},
        "_run_id": "run-1",
    }

    assert service.compute_content_hash("chembl", record) == generate_content_hash(
        record, "chembl"
    )


def test_content_hash_future_meta_field_contract() -> None:
    """Future underscore-prefixed technical fields MUST NOT alter content hash."""
    service = EntityIdentityGenerator()

    base = {"activity_id": "A1", "value": 10}
    with_future_meta = {
        **base,
        "_future_meta_field": "v2",
        "_new_runtime_flag": True,
    }

    assert service.compute_content_hash("chembl", base) == service.compute_content_hash(
        "chembl", with_future_meta
    )


def test_content_hash_schema_include_exclude_contract() -> None:
    """Schema include/exclude policy MUST be applied by EntityIdentityGenerator."""
    service = EntityIdentityGenerator(
        content_hash_include_fields={"activity_id", "value", "ignore_me"},
        content_hash_exclude_fields={"ignore_me"},
    )

    record_v1 = {
        "activity_id": "A1",
        "value": 10,
        "comment": "v1",
        "ignore_me": "foo",
    }
    record_v2 = {
        "activity_id": "A1",
        "value": 10,
        "comment": "v2",
        "ignore_me": "bar",
    }

    assert service.compute_content_hash(
        "chembl", record_v1
    ) == service.compute_content_hash("chembl", record_v2)


def test_openalex_grants_raw_json_sidecar_does_not_change_semantic_content_hash() -> (
    None
):
    record_a = {
        "openalex_id": "W1",
        "title": "Example",
        "grants": '[{"funder":"A"},{"funder":"B"}]',
        "grants_canonical_json": '[{"funder":"A"},{"funder":"B"}]',
        "grants_raw_json": '[{"funder":"A"},{"funder":"B"}]',
    }
    record_b = {
        **record_a,
        "grants_raw_json": '[{"funder":"B"},{"funder":"A"}]',
    }

    assert generate_content_hash(
        record_a,
        "openalex",
        include_fields=set(OPENALEX_PUBLICATION_PROFILE.hash_included_fields),
        exclude_fields=set(OPENALEX_PUBLICATION_PROFILE.hash_excluded_fields),
        set_like_fields=set(OPENALEX_PUBLICATION_PROFILE.set_like_fields),
    ) == generate_content_hash(
        record_b,
        "openalex",
        include_fields=set(OPENALEX_PUBLICATION_PROFILE.hash_included_fields),
        exclude_fields=set(OPENALEX_PUBLICATION_PROFILE.hash_excluded_fields),
        set_like_fields=set(OPENALEX_PUBLICATION_PROFILE.set_like_fields),
    )


def test_unordered_publication_raw_json_sidecars_are_excluded_from_semantic_hash() -> (
    None
):
    assert (
        "affiliation_structured_raw_json"
        in PUBMED_PUBLICATION_PROFILE.hash_excluded_fields
    )
    assert "publication_types_raw_json" in (
        SEMANTICSCHOLAR_PUBLICATION_PROFILE.hash_excluded_fields
    )
    assert "subject_fields_raw_json" in (
        SEMANTICSCHOLAR_PUBLICATION_PROFILE.hash_excluded_fields
    )


def test_uniprot_raw_json_sidecars_are_excluded_from_semantic_hash() -> None:
    expected_raw_sidecars = {
        "alternative_products_raw_json",
        "biophysicochemical_properties_raw_json",
        "cofactors_raw_json",
        "features_raw_json",
        "reactions_raw_json",
    }

    assert expected_raw_sidecars <= UNIPROT_PROTEIN_PROFILE.hash_excluded_fields

    record_a = {
        "accession": "P12345",
        "alternative_products": '[{"id":"P12345-2","name":"Isoform 2"}]',
        "alternative_products_canonical_json": '[{"id":"P12345-2","name":"Isoform 2"}]',
        "alternative_products_raw_json": (
            '[{"commentType":"ALTERNATIVE PRODUCTS",'
            '"isoforms":[{"isoformIds":[{"value":"P12345-2"}]}]}]'
        ),
    }
    record_b = {
        **record_a,
        "alternative_products_raw_json": (
            '[{"commentType":"ALTERNATIVE PRODUCTS",'
            '"note":"provider-order-changed",'
            '"isoforms":[{"isoformIds":[{"value":"P12345-2"}]}]}]'
        ),
    }

    assert generate_content_hash(
        record_a,
        "uniprot",
        include_fields=set(UNIPROT_PROTEIN_PROFILE.hash_included_fields),
        exclude_fields=set(UNIPROT_PROTEIN_PROFILE.hash_excluded_fields),
        set_like_fields=set(UNIPROT_PROTEIN_PROFILE.set_like_fields),
    ) == generate_content_hash(
        record_b,
        "uniprot",
        include_fields=set(UNIPROT_PROTEIN_PROFILE.hash_included_fields),
        exclude_fields=set(UNIPROT_PROTEIN_PROFILE.hash_excluded_fields),
        set_like_fields=set(UNIPROT_PROTEIN_PROFILE.set_like_fields),
    )
