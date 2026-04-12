"""Tests for canonical control-plane fingerprint contracts."""

from __future__ import annotations

from bioetl.domain.normalization import compute_manifest_execution_fingerprint
from bioetl.domain.normalization import compute_degraded_runtime_anchor_fingerprint
from bioetl.domain.normalization import normalize_run_manifest_spec
from bioetl.domain.normalization import normalize_runtime_anchor_payload


def test_manifest_execution_fingerprint_is_deterministic_for_equivalent_payloads() -> None:
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
            "contract_ref": " ChemBL.Activity ",
            "contract_version": " v2 ",
        },
        "source_refs": [
            {
                "query": "assay_type=B",
                "pipeline_name": "chembl_activity",
                "entity": "activity",
                "provider": "chembl",
                "input_snapshots": [
                    {"snapshot_id": "b-2", "content_hash": "hash-b-2"},
                    {"snapshot_id": "b-1", "content_hash": "hash-b-1"},
                ],
            }
        ],
        "planned_artifacts": [
            {"path": "data/output/gold/chembl/activity", "layer": "gold"},
            {"layer": "bronze", "path": "data/output/bronze/chembl/activity"},
        ],
    }
    reordered = {
        **payload,
        "launch_context": {"limit": 100, "resume": False},
        "runtime_config": {"run_type": "incremental", "limit": 100},
        "resolved_config": {"provider": "chembl", "entity_type": "activity"},
        "source_refs": list(reversed(payload["source_refs"])),
        "planned_artifacts": list(reversed(payload["planned_artifacts"])),
    }

    assert compute_manifest_execution_fingerprint(
        normalize_run_manifest_spec(payload)
    ) == compute_manifest_execution_fingerprint(normalize_run_manifest_spec(reordered))


def test_manifest_execution_fingerprint_matches_golden_value() -> None:
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
            "contract_ref": " ChemBL.Activity ",
            "contract_version": " v2 ",
        },
        "source_refs": [
            {
                "query": "assay_type=B",
                "pipeline_name": "chembl_activity",
                "entity": "activity",
                "provider": "chembl",
                "input_snapshots": [
                    {"snapshot_id": "b-2", "content_hash": "hash-b-2"},
                    {"snapshot_id": "b-1", "content_hash": "hash-b-1"},
                ],
            }
        ],
        "planned_artifacts": [
            {"path": "data/output/gold/chembl/activity", "layer": "gold"},
            {"layer": "bronze", "path": "data/output/bronze/chembl/activity"},
        ],
    }

    assert (
        compute_manifest_execution_fingerprint(normalize_run_manifest_spec(payload))
        == "608f808f7b3842c09f42505853ee92ba113ff9ef29851d2a481714247a8ca08d"
    )


def test_runtime_anchor_fingerprint_is_deterministic_for_equivalent_payloads() -> None:
    payload = {
        "effective_config_hash": " SHA256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA ",
        "contract_ref": " ChemBL.Activity ",
        "contract_version": " v2 ",
        "manifest_id": " manifest-123 ",
        "dq_contract_compatibility_hash": " DEADBEEF ",
        "effective_config_artifact_id": " artifact-42 ",
    }
    reordered = {
        "effective_config_artifact_id": "artifact-42",
        "manifest_id": "manifest-123",
        "dq_contract_compatibility_hash": "deadbeef",
        "contract_version": "2.0.0",
        "contract_ref": "chembl.activity",
        "effective_config_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }

    assert compute_degraded_runtime_anchor_fingerprint(
        normalize_runtime_anchor_payload(payload)
    ) == compute_degraded_runtime_anchor_fingerprint(
        normalize_runtime_anchor_payload(reordered)
    )
