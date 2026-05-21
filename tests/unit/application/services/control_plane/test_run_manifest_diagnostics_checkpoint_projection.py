"""Tests for shared run-manifest checkpoint diagnostic projections."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane._run_manifest_diagnostics_checkpoint_projection import (
    build_checkpoint_anchor_projection,
    build_current_checkpoint_anchor_payload,
    build_resume_anchor_comparison,
    resolve_resume_identity_maps,
)


@pytest.mark.unit
def test_build_current_checkpoint_anchor_payload_uses_bounded_anchor_fields() -> None:
    payload = build_current_checkpoint_anchor_payload(
        {
            "execution_fingerprint": "fingerprint-1",
            "manifest_id": "manifest-1",
            "effective_config_hash": "hash-1",
            "contract_ref": "chembl.activity",
            "contract_version": "1.0.0",
            "effective_config_artifact_id": "artifact-1",
            "input_snapshot_ids": ["snapshot-1"],
            "ignored": "not-projected",
        }
    )

    assert payload == {
        "execution_fingerprint": "fingerprint-1",
        "manifest_id": "manifest-1",
        "effective_config_hash": "hash-1",
        "contract_ref": "chembl.activity",
        "contract_version": "1.0.0",
        "effective_config_artifact_id": "artifact-1",
        "input_snapshot_ids": ["snapshot-1"],
    }


@pytest.mark.unit
def test_resume_anchor_comparison_reports_missing_and_mismatched_fields() -> None:
    summary = {
        "resume_diagnostics": {
            "current_identity": {
                "execution_fingerprint": "current",
                "manifest_id": "manifest-1",
            },
            "checkpoint_identity": {
                "execution_fingerprint": "checkpoint",
                "checkpoint_only": "anchor",
            },
        }
    }

    comparison = build_resume_anchor_comparison(summary)

    assert comparison["checkpoint_identity_present"] is True
    assert comparison["mismatched_fields"] == ["execution_fingerprint"]
    assert comparison["missing_current_fields"] == ["checkpoint_only"]
    assert comparison["missing_checkpoint_fields"] == ["manifest_id"]


@pytest.mark.unit
def test_resume_identity_maps_return_none_without_complete_resume_payload() -> None:
    assert resolve_resume_identity_maps({"resume_diagnostics": {}}) is None
    assert build_resume_anchor_comparison({}) == {
        "checkpoint_identity_present": False,
        "matching_fields": [],
        "mismatched_fields": [],
        "missing_current_fields": [],
        "missing_checkpoint_fields": [],
    }


@pytest.mark.unit
def test_build_checkpoint_anchor_projection_combines_anchor_views() -> None:
    summary = {
        "execution_fingerprint": "fingerprint-1",
        "manifest_id": "manifest-1",
        "effective_config_hash": "hash-1",
        "contract_ref": "chembl.activity",
        "contract_version": "1.0.0",
        "effective_config_artifact_id": "artifact-1",
        "input_snapshot_ids": ["snapshot-1"],
    }

    projection = build_checkpoint_anchor_projection(summary)

    assert projection == {
        "current_manifest_anchors": {
            "execution_fingerprint": "fingerprint-1",
            "manifest_id": "manifest-1",
            "effective_config_hash": "hash-1",
            "contract_ref": "chembl.activity",
            "contract_version": "1.0.0",
            "effective_config_artifact_id": "artifact-1",
            "input_snapshot_ids": ["snapshot-1"],
        },
        "resume_anchor_comparison": {
            "checkpoint_identity_present": False,
            "matching_fields": [],
            "mismatched_fields": [],
            "missing_current_fields": [],
            "missing_checkpoint_fields": [],
        },
    }
