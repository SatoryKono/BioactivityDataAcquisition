"""Unit tests for the ChEMBL Activity normalization profile."""

from __future__ import annotations

from bioetl.domain.normalization.profiles import (
    CHEMBL_ACTIVITY_PROFILE,
    CHEMBL_ACTIVITY_SCHEMA_FIELDS,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_passthrough,
    normalize_profile_text,
)


def test_chembl_activity_profile_covers_schema_exactly() -> None:
    missing, extra = CHEMBL_ACTIVITY_PROFILE.coverage_gaps(
        CHEMBL_ACTIVITY_SCHEMA_FIELDS
    )

    assert missing == frozenset()
    assert extra == frozenset()


def test_chembl_activity_profile_marks_meta_fields_outside_hash() -> None:
    assert CHEMBL_ACTIVITY_PROFILE.rule_for("entity_id") is not None
    assert CHEMBL_ACTIVITY_PROFILE.rule_for("entity_id").include_in_hash is False
    assert CHEMBL_ACTIVITY_PROFILE.rule_for("_run_id") is not None
    assert CHEMBL_ACTIVITY_PROFILE.rule_for("_run_id").include_in_hash is False
    assert CHEMBL_ACTIVITY_PROFILE.rule_for("activity_id") is not None
    assert CHEMBL_ACTIVITY_PROFILE.rule_for("activity_id").include_in_hash is True


def test_chembl_activity_profile_snapshot_contains_expected_fields_and_semantics() -> (
    None
):
    assert CHEMBL_ACTIVITY_SCHEMA_FIELDS[:10] == (
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "_index",
        "_dq_warn",
        "_dq_error",
        "_state",
    )
    assert CHEMBL_ACTIVITY_SCHEMA_FIELDS[-5:] == (
        "journal",
        "publication_doi",
        "publication_pmid",
        "publication_pmc_id",
        "publication_year",
    )
    assert CHEMBL_ACTIVITY_PROFILE.rule_for("activity_properties") is not None
    assert CHEMBL_ACTIVITY_PROFILE.rule_for("activity_properties").set_like is True


def test_chembl_activity_meta_fields_use_passthrough_normalizer() -> None:
    assert (
        CHEMBL_ACTIVITY_PROFILE.rule_for("entity_id").normalizer
        is normalize_profile_passthrough
    )
    assert (
        CHEMBL_ACTIVITY_PROFILE.rule_for("_run_id").normalizer
        is normalize_profile_passthrough
    )
    assert (
        CHEMBL_ACTIVITY_PROFILE.rule_for("_index").normalizer
        is normalize_profile_passthrough
    )
    assert (
        CHEMBL_ACTIVITY_PROFILE.rule_for("activity_id").normalizer
        is normalize_profile_text
    )
