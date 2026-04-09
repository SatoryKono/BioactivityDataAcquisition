"""Unit tests for checkpoint metadata hashing helpers."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from bioetl.composition.factories.pipeline.checkpoint_metadata_helpers import (
    _compute_execution_identity_fingerprint,
    _normalize_execution_identity_payload,
    build_current_checkpoint_metadata,
)
from bioetl.domain.normalization import serialize_json_canonical
from bioetl.domain.types import RunType


def _make_pipeline(
    *,
    pipeline_name: str = "chembl_activity",
    run_type: RunType = RunType.INCREMENTAL,
    pipeline_version: str | None = "1.2.3",
    config_hash: str | None = "sha256:abc",
    dq_contract_compatibility_hash: str | None = "deadbeef",
    effective_config_artifact_id: str | None = "artifact-1",
    manifest_id: str | None = "manifest-1",
) -> SimpleNamespace:
    run_context = SimpleNamespace(
        pipeline_version=pipeline_version,
        config_hash=config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        manifest_id=manifest_id,
    )
    services = SimpleNamespace(metadata_coordinator=SimpleNamespace(run_context=run_context))
    config = SimpleNamespace(pipeline_name=pipeline_name)
    runtime = SimpleNamespace(run_type=run_type)
    return SimpleNamespace(services=services, config=config, runtime=runtime)


@pytest.mark.unit
def test_normalize_execution_identity_payload_canonicalizes_hash_like_anchors() -> None:
    payload = _normalize_execution_identity_payload(
        pipeline_name=" chembl_activity ",
        run_type=" incremental ",
        pipeline_version=" 1.2.3 ",
        effective_config_hash=" SHA256:ABC ",
        dq_contract_compatibility_hash=" DEADBEEF ",
    )

    assert payload == {
        "pipeline_name": "chembl_activity",
        "run_type": "incremental",
        "pipeline_version": "1.2.3",
        "effective_config_hash": "sha256:abc",
        "dq_contract_compatibility_hash": "deadbeef",
    }


@pytest.mark.unit
def test_compute_execution_identity_fingerprint_is_order_invariant() -> None:
    payload_a = {
        "pipeline_name": "chembl_activity",
        "run_type": "incremental",
        "pipeline_version": "1.2.3",
        "effective_config_hash": "sha256:abc",
        "dq_contract_compatibility_hash": "deadbeef",
    }
    payload_b = {
        "dq_contract_compatibility_hash": "deadbeef",
        "effective_config_hash": "sha256:abc",
        "pipeline_version": "1.2.3",
        "run_type": "incremental",
        "pipeline_name": "chembl_activity",
    }

    assert _compute_execution_identity_fingerprint(payload_a) == (
        _compute_execution_identity_fingerprint(payload_b)
    )


@pytest.mark.unit
def test_compute_execution_identity_fingerprint_matches_canonical_serializer() -> None:
    payload = {
        "pipeline_name": "chembl_activity",
        "run_type": "incremental",
        "pipeline_version": "1.2.3",
        "effective_config_hash": "sha256:abc",
        "dq_contract_compatibility_hash": "deadbeef",
    }

    expected = hashlib.sha256(
        serialize_json_canonical(payload).encode("utf-8")
    ).hexdigest()

    assert _compute_execution_identity_fingerprint(payload) == expected


@pytest.mark.unit
def test_build_current_checkpoint_metadata_uses_canonical_identity_pipeline() -> None:
    pipeline_a = _make_pipeline(
        config_hash=" SHA256:ABC ",
        dq_contract_compatibility_hash=" DEADBEEF ",
        pipeline_version=" 1.2.3 ",
    )
    pipeline_b = _make_pipeline(
        config_hash="sha256:abc",
        dq_contract_compatibility_hash="deadbeef",
        pipeline_version="1.2.3",
    )

    metadata_a = build_current_checkpoint_metadata(pipeline_a)
    metadata_b = build_current_checkpoint_metadata(pipeline_b)

    assert metadata_a.effective_config_hash == "sha256:abc"
    assert metadata_a.dq_contract_compatibility_hash == "deadbeef"
    assert metadata_a.pipeline_version == "1.2.3"
    assert metadata_a.execution_fingerprint == metadata_b.execution_fingerprint
    assert metadata_a.effective_config_artifact_id == "artifact-1"
    assert metadata_a.run_context == {
        "pipeline_name": "chembl_activity",
        "manifest_id": "manifest-1",
    }
