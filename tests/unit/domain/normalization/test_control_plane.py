"""Tests for control-plane normalization helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.domain.normalization.control_plane import (
    normalize_execution_identity_payload,
    normalize_control_plane_opaque_hash_ref,
    normalize_control_plane_strict_sha256,
    normalize_runtime_anchor_payload,
    normalize_run_ledger_payload,
    normalize_run_manifest_spec,
)


def test_normalize_run_manifest_spec_is_deterministic_for_set_like_refs() -> None:
    payload = {
        "schema_version": "1.0",
        "run_type": "incremental",
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity": "activity",
        "launch_context": {"resume": False, "limit": 100},
        "runtime_config": {"limit": 100, "run_type": "incremental"},
        "resolved_config": {"entity_type": "activity", "provider": "chembl"},
        "code_provenance": {
            "git_commit": "abc1234",
            "config_hash": "DEADBEEF",
        },
        "source_refs": [
            {
                "query": "assay_type=B",
                "pipeline_name": "chembl_activity",
                "entity": "activity",
                "provider": "chembl",
                "input_snapshots": [
                    {
                        "snapshot_id": "snapshot-b-2",
                        "content_hash": "hash-b-2",
                        "immutable_uri": "file:///snapshots/b-2.jsonl",
                    },
                    {
                        "snapshot_id": "snapshot-b-1",
                        "content_hash": "hash-b-1",
                        "immutable_uri": "file:///snapshots/b-1.jsonl",
                    },
                ],
            },
            {
                "pipeline_name": "chembl_activity",
                "provider": "chembl",
                "entity": "activity",
                "query": "assay_type=F",
                "input_snapshots": [
                    {
                        "snapshot_id": "snapshot-f-1",
                        "content_hash": "hash-f-1",
                        "immutable_uri": "file:///snapshots/f-1.jsonl",
                    }
                ],
            },
        ],
        "planned_artifacts": [
            {"path": "data/output/gold/chembl/activity", "layer": "gold"},
            {"layer": "bronze", "path": "data/output/bronze/chembl/activity"},
        ],
    }

    reordered_payload = {
        **payload,
        "launch_context": {"limit": 100, "resume": False},
        "runtime_config": {"run_type": "incremental", "limit": 100},
        "resolved_config": {"provider": "chembl", "entity_type": "activity"},
        "source_refs": list(reversed(payload["source_refs"])),
        "planned_artifacts": list(reversed(payload["planned_artifacts"])),
    }

    normalized = normalize_run_manifest_spec(payload)
    reordered = normalize_run_manifest_spec(reordered_payload)

    assert normalized == reordered
    assert normalized["code_provenance"] == {
        "config_hash": "deadbeef",
        "git_commit": "abc1234",
    }
    assert normalized["planned_artifacts"] == [
        {"layer": "bronze", "path": "data/output/bronze/chembl/activity"},
        {"layer": "gold", "path": "data/output/gold/chembl/activity"},
    ]
    assert normalized["source_refs"][0]["input_snapshots"] == [
        {
            "content_hash": "hash-b-1",
            "immutable_uri": "file:///snapshots/b-1.jsonl",
            "snapshot_id": "snapshot-b-1",
        },
        {
            "content_hash": "hash-b-2",
            "immutable_uri": "file:///snapshots/b-2.jsonl",
            "snapshot_id": "snapshot-b-2",
        },
    ]


def test_normalize_run_manifest_spec_orders_input_snapshots_by_snapshot_id() -> None:
    payload = {
        "schema_version": "1.0",
        "run_type": "incremental",
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity": "activity",
        "launch_context": {"resume": False},
        "runtime_config": {"run_type": "incremental"},
        "resolved_config": {"provider": "chembl", "entity_type": "activity"},
        "source_refs": [
            {
                "provider": "chembl",
                "entity": "activity",
                "pipeline_name": "chembl_activity",
                "input_snapshots": [
                    {
                        "snapshot_id": "z-snapshot",
                        "content_hash": "aaa",
                        "immutable_uri": "file:///snapshots/a.jsonl",
                    },
                    {
                        "snapshot_id": "a-snapshot",
                        "content_hash": "zzz",
                        "immutable_uri": "file:///snapshots/z.jsonl",
                    },
                ],
            }
        ],
    }

    normalized = normalize_run_manifest_spec(payload)

    assert [
        item["snapshot_id"]
        for item in normalized["source_refs"][0]["input_snapshots"]
    ] == ["a-snapshot", "z-snapshot"]


def test_normalize_run_ledger_payload_is_idempotent() -> None:
    occurred_at = datetime(2026, 4, 8, 12, 53, 47, tzinfo=UTC)
    payload = {
        "entry_id": "entry-1",
        "manifest_id": "manifest-1",
        "run_id": UUID("11111111-1111-1111-1111-111111111111"),
        "event_type": "stage_started",
        "event_family": "pipeline.phase",
        "occurred_at": occurred_at,
        "status": "running",
        "stage": "seed",
        "metrics_snapshot": {"records_b": 2, "records_a": 1},
        "details": {
            "beta": {"z": 1, "a": 2},
            "alpha": "value",
            "_diagnostic": {"run_id": UUID("11111111-1111-1111-1111-111111111111")},
        },
    }

    normalized = normalize_run_ledger_payload(payload)
    normalized_again = normalize_run_ledger_payload(normalized)

    assert normalized == normalized_again
    assert normalized["run_id"] == "11111111-1111-1111-1111-111111111111"
    assert normalized["occurred_at"] == "2026-04-08T12:53:47Z"
    assert normalized["metrics_snapshot"] == {"records_a": 1, "records_b": 2}
    assert list(normalized["details"]) == ["_diagnostic", "alpha", "beta"]


def test_normalize_runtime_anchor_payload_coerces_canonical_contract_fields() -> None:
    normalized = normalize_runtime_anchor_payload(
        {
            "config_hash": " SHA256:FACE ",
            "dq_contract_compatibility_hash": " DEADBEEF ",
            "contract_schema_hash": " ABC123 ",
            "effective_config_hash": " SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
            "contract_ref": " ChemBL.Activity ",
            "contract_version": " v2 ",
            "manifest_id": " manifest-123 ",
            "composite_run_identity": " run-42 ",
        }
    )

    assert normalized == {
        "config_hash": "sha256:face",
        "dq_contract_compatibility_hash": "deadbeef",
        "contract_schema_hash": "abc123",
        "effective_config_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "contract_ref": "chembl.activity",
        "contract_version": "2.0.0",
        "manifest_id": "manifest-123",
        "composite_run_identity": "run-42",
    }


def test_normalize_execution_identity_payload_coerces_canonical_identity_fields() -> None:
    normalized = normalize_execution_identity_payload(
        {
            "pipeline_name": " chembl_activity ",
            "run_type": " INCREMENTAL ",
            "pipeline_version": " 1.2.3 ",
            "effective_config_hash": " SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
            "dq_contract_compatibility_hash": " DEADBEEF ",
            "contract_ref": " ChemBL.Activity ",
            "contract_version": " v2 ",
            "effective_config_artifact_id": " artifact-42 ",
            "exact_replay": True,
            "input_snapshot_fingerprint": " FACE ",
        }
    )

    assert normalized == {
        "pipeline_name": "chembl_activity",
        "run_type": "incremental",
        "pipeline_version": "1.2.3",
        "effective_config_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "dq_contract_compatibility_hash": "deadbeef",
        "contract_ref": "chembl.activity",
        "contract_version": "2.0.0",
        "effective_config_artifact_id": "artifact-42",
        "exact_replay": "true",
        "input_snapshot_fingerprint": "face",
    }


def test_normalize_control_plane_opaque_hash_ref_keeps_legacy_non_strict_values() -> None:
    assert normalize_control_plane_opaque_hash_ref(" SHA256:FACE ") == "sha256:face"
    assert normalize_control_plane_opaque_hash_ref(" compat-hash-123 ") == "compat-hash-123"


def test_normalize_control_plane_strict_sha256_requires_lowercase_hex_payload() -> None:
    assert normalize_control_plane_strict_sha256(
        " SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA "
    ) == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

    with pytest.raises(ValueError, match="Invalid SHA256 format"):
        normalize_control_plane_strict_sha256("sha256:not-hex")


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        (
            {
                "contract_ref": "ChemBL Activity/Bad",
                "contract_version": "1.0.0",
                "effective_config_hash": "a" * 64,
            },
            "Invalid contract_ref format",
        ),
        (
            {
                "contract_ref": "chembl.activity",
                "contract_version": "1.0.beta",
                "effective_config_hash": "a" * 64,
            },
            "Invalid contract_version format",
        ),
        (
            {
                "contract_ref": "chembl.activity",
                "contract_version": "1.0.0",
                "effective_config_hash": "sha256:not-hex",
            },
            "Invalid effective_config_hash format",
        ),
    ],
)
def test_normalize_runtime_anchor_payload_fails_closed_on_malformed_anchors(
    payload: dict[str, str],
    expected_message: str,
) -> None:
    with pytest.raises(ValueError, match=expected_message):
        normalize_runtime_anchor_payload(payload)
