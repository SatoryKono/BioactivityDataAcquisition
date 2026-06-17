"""Unit tests for historical replay CLI support helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bioetl.interfaces.cli.commands._run_manifest_historical_support import (
    _coerce_bulk_certification_specs,
    _load_residual_dispositions,
    _load_universe_external_records,
)


pytestmark = pytest.mark.unit


def test_coerce_bulk_certification_specs_normalizes_snapshot_entries() -> None:
    specs = _coerce_bulk_certification_specs(
        {
            "specs": [
                {
                    "manifest_id": " manifest-1 ",
                    "certifications": [
                        {
                            "provider": " chembl ",
                            "entity": " activity ",
                            "pipeline_name": " chembl_activity ",
                            "snapshot_id": " snapshot-1 ",
                            "content_hash": " sha256:abc ",
                            "immutable_uri": " s3://archive/snapshot-1 ",
                            "bronze_batch_ref": " bronze-batch-1 ",
                            "query": " ",
                            "query_fingerprint": " fp-1 ",
                            "certification_basis": " ",
                        }
                    ],
                }
            ]
        }
    )

    assert len(specs) == 1
    assert specs[0].manifest_id == "manifest-1"
    certification = specs[0].certifications[0]
    assert certification.provider == "chembl"
    assert certification.entity == "activity"
    assert certification.query is None
    assert certification.query_fingerprint == "fp-1"
    assert certification.certification_basis == "retained_bronze_artifact"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "Bulk certification plan must be a JSON object"),
        ({}, "requires a non-empty specs list"),
        ({"specs": ["not-a-dict"]}, "specs must be JSON objects"),
        ({"specs": [{"certifications": [{}]}]}, "missing manifest_id"),
        (
            {"specs": [{"manifest_id": "manifest-1", "certifications": []}]},
            "requires certifications",
        ),
        (
            {
                "specs": [
                    {
                        "manifest_id": "manifest-1",
                        "certifications": ["not-a-dict"],
                    }
                ]
            },
            "entries for 'manifest-1' must be JSON objects",
        ),
        (
            {
                "specs": [
                    {
                        "manifest_id": "manifest-1",
                        "certifications": [
                            {
                                "provider": "chembl",
                                "entity": "activity",
                            }
                        ],
                    }
                ]
            },
            "missing fields:",
        ),
    ],
)
def test_coerce_bulk_certification_specs_rejects_malformed_payloads(
    payload: object,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _coerce_bulk_certification_specs(payload)


def test_load_residual_dispositions_reads_optional_evidence_refs(
    tmp_path: Path,
) -> None:
    dispositions_path = tmp_path / "residual-dispositions.json"
    dispositions_path.write_text(
        json.dumps(
            {
                "dispositions": [
                    {
                        "manifest_id": "manifest-1",
                        "disposition": "irrecoverable_missing_immutable_evidence",
                        "rationale": "archive is no longer available",
                        "evidence_refs": [" evidence-1 ", "", "evidence-2"],
                    },
                    {
                        "manifest_id": "manifest-2",
                        "disposition": "outside_universal_claim_scope",
                        "rationale": "not part of this corpus",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    dispositions = _load_residual_dispositions(dispositions_path)

    assert [item.manifest_id for item in dispositions] == ["manifest-1", "manifest-2"]
    assert dispositions[0].evidence_refs == ("evidence-1", "evidence-2")
    assert dispositions[1].evidence_refs == ()


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "Residual disposition file must be a JSON object"),
        ({}, "requires a dispositions list"),
        ({"dispositions": ["bad"]}, "entries must be JSON objects"),
        (
            {"dispositions": [{"manifest_id": "manifest-1"}]},
            "require manifest_id, disposition, and rationale",
        ),
        (
            {
                "dispositions": [
                    {
                        "manifest_id": "manifest-1",
                        "disposition": "irrecoverable_missing_immutable_evidence",
                        "rationale": "known gap",
                        "evidence_refs": "not-a-list",
                    }
                ]
            },
            "evidence_refs must be a list",
        ),
    ],
)
def test_load_residual_dispositions_rejects_malformed_files(
    tmp_path: Path,
    payload: object,
    message: str,
) -> None:
    dispositions_path = tmp_path / "invalid-dispositions.json"
    dispositions_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        _load_residual_dispositions(dispositions_path)


def test_load_residual_dispositions_returns_empty_tuple_without_file() -> None:
    assert _load_residual_dispositions(None) == ()


def test_load_universe_external_records_reads_archived_pack_fixture() -> None:
    pack_path = Path(
        "tests/fixtures/control_plane/historical_replay_universe/minimal_archive_pack.json"
    )

    records = _load_universe_external_records((pack_path,))

    assert len(records) == 1
    record = records[0]
    assert record.manifest_id == "archived-manifest-minimal"
    assert record.source_pack_ref == "archive-pack-minimal"
    assert record.durable_evidence_coverage is True


def test_load_universe_external_records_rejects_missing_required_fields(
    tmp_path: Path,
) -> None:
    pack_path = tmp_path / "invalid-pack.json"
    pack_path.write_text(
        json.dumps(
            {
                "pack_id": "invalid-pack",
                "records": [
                    {
                        "manifest_id": "missing-run-id",
                        "pipeline_name": "chembl_activity",
                        "provider": "chembl",
                        "entity": "activity",
                        "execution_context": "isolated",
                        "certification_status": "already_certified",
                        "replay_occurrence_kind": "historical_source_replay_certified_parent",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing fields: run_id"):
        _load_universe_external_records((pack_path,))


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ([], "Universe pack must be a JSON object"),
        ({"records": []}, "requires a non-empty records list"),
        (
            {
                "records": [
                    {
                        "manifest_id": "manifest-1",
                        "run_id": "run-1",
                        "pipeline_name": "chembl_activity",
                        "provider": "chembl",
                        "entity": "activity",
                        "execution_context": "historical",
                        "certification_status": "already_certified",
                        "replay_occurrence_kind": "historical_source_replay",
                        "blocking_reasons": "not-a-list",
                    }
                ]
            },
            "blocking_reasons must be a list",
        ),
    ],
)
def test_load_universe_external_records_rejects_malformed_packs(
    tmp_path: Path,
    payload: object,
    message: str,
) -> None:
    pack_path = tmp_path / "invalid-universe-pack.json"
    pack_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        _load_universe_external_records((pack_path,))
