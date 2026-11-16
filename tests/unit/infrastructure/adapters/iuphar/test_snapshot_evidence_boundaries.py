"""Reject self-consistently hashed but invalid offline acquisition declarations."""

from __future__ import annotations

import json

import pytest

from bioetl.infrastructure.adapters.iuphar._manifest import sha256
from bioetl.infrastructure.adapters.iuphar.snapshot_builder import build_snapshot_bundle
from iuphar_target_class.stage0.io import canonical_json_bytes
from tests.helpers.iuphar_snapshot import (
    synthetic_snapshot_sources,
    write_fixture_json,
)

pytestmark = pytest.mark.unit


def _documents(tmp_path):
    acquisition, _, coverage, _ = synthetic_snapshot_sources(tmp_path / "source")
    acquired = json.loads(acquisition.read_bytes())
    covered = json.loads(coverage.read_bytes())
    review_path = coverage.parent / covered["review"]["path"]
    review = json.loads(review_path.read_bytes())
    return acquisition, acquired, coverage, covered, review_path, review


def _publish(documents, output):
    acquisition, acquired, coverage, covered, review_path, review = documents
    acquisition_hash = write_fixture_json(acquisition, acquired)
    covered["acquisition_sha256"] = acquisition_hash
    review["acquisition_sha256"] = acquisition_hash
    review["scope_sha256"] = sha256(canonical_json_bytes(covered["scope"]))
    covered["review"]["sha256"] = write_fixture_json(review_path, review)
    coverage_hash = write_fixture_json(coverage, covered)
    return build_snapshot_bundle(
        acquisition=acquisition,
        acquisition_sha256=acquisition_hash,
        coverage=coverage,
        coverage_sha256=coverage_hash,
        output_dir=output,
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("unexpected", True, "unsupported snapshot coverage scope"),
        ("species_taxon_ids", "9606", "nonempty string list"),
        ("species_taxon_ids", [], "nonempty string list"),
        ("species_taxon_ids", [""], "invalid string"),
        ("species_taxon_ids", ["9606", "9606"], "duplicate snapshot scope"),
        ("required_family_types", ["GPCR"], "canonical provider tokens"),
        ("expected_raw_row_count", 0, "positive count"),
        ("expected_variant_count", True, "positive count"),
        ("selection_basis", "inferred_by_classifier", "independently reviewed"),
        ("excluded_targets", {}, "explicit list"),
        (
            "excluded_targets",
            [{"target_id": "2", "rationale": "synthetic exclusion"}],
            "every source record",
        ),
        (
            "excluded_targets",
            [
                {
                    "target_id": "2",
                    "rationale": "synthetic exclusion",
                    "source_records": [2, 2],
                }
            ],
            "duplicate snapshot exclusion identity",
        ),
    ],
)
def test_builder_refuses_invalid_scope_even_with_matching_review_hash(
    tmp_path, field, value, message
):
    documents = _documents(tmp_path)
    documents[3]["scope"][field] = value
    output = tmp_path / "must-not-publish"
    with pytest.raises(ValueError, match=message):
        _publish(documents, output)
    assert not output.exists()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("byte_count", 1, "raw byte count differs"),
        ("source_url", "http://example.test/provider.csv", "HTTPS source URL"),
        (
            "source_url",
            "https://synthetic-user:synthetic-password@example.test/provider.csv",
            "credential-free HTTPS",
        ),
    ],
)
def test_builder_refuses_invalid_acquisition_metadata_before_publication(
    tmp_path, field, value, message
):
    documents = _documents(tmp_path)
    documents[1]["raw_artifacts"]["targets_csv"][field] = value
    output = tmp_path / "must-not-publish"
    with pytest.raises(ValueError, match=message):
        _publish(documents, output)
    assert not output.exists()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("raw_artifacts", {}, "no raw provider artifacts"),
        ("raw_artifacts", [], "evidence object required"),
        ("retrieved_at", "not-a-time", "invalid acquisition retrieval timestamp"),
        ("retrieved_at", "2026-11-16T00:00:00", "needs a timezone"),
    ],
)
def test_builder_refuses_missing_source_or_unqualified_retrieval_time(
    tmp_path, field, value, message
):
    documents = _documents(tmp_path)
    documents[1][field] = value
    output = tmp_path / "must-not-publish"
    with pytest.raises(ValueError, match=message):
        _publish(documents, output)
    assert not output.exists()


@pytest.mark.parametrize("wrong_binding", ["coverage", "review", "review_references"])
def test_builder_refuses_review_bound_to_another_acquisition(tmp_path, wrong_binding):
    documents = _documents(tmp_path)
    acquisition, acquired, coverage, covered, review_path, review = documents
    acquisition_hash = write_fixture_json(acquisition, acquired)
    if wrong_binding == "coverage":
        covered["acquisition_sha256"] = "0" * 64
        message = "coverage belongs to another acquisition"
    elif wrong_binding == "review":
        review["acquisition_sha256"] = "0" * 64
        message = "review belongs to another acquisition"
    else:
        review["evidence_references"] = {}
        message = "typed artifact references"
    covered["review"]["sha256"] = write_fixture_json(review_path, review)
    coverage_hash = write_fixture_json(coverage, covered)
    output = tmp_path / "must-not-publish"
    with pytest.raises(ValueError, match=message):
        build_snapshot_bundle(
            acquisition=acquisition,
            acquisition_sha256=acquisition_hash,
            coverage=coverage,
            coverage_sha256=coverage_hash,
            output_dir=output,
        )
    assert not output.exists()
