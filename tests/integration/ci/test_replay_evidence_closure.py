"""Replay evidence closure across the published supported pipeline families."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from bioetl.application.services.checkpoint.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.application.services.control_plane.manifest.diagnostics import (
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import (
    RunManifest,
    RunInputSnapshotRef,
    RunSourceRef,
    RunLedgerEntry,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite
from tests.integration.ci.test_reproducibility_contract_suite import (
    _PUBLISHED_SUPPORTED_BOUNDARY_FAMILIES,
    _family_context,
    _make_manifest,
    _ManifestIdentity,
)

pytestmark = pytest.mark.integration


def _checkpoint_metadata_from_summary(
    manifest: RunManifest,
    summary: dict[str, object],
) -> CheckpointMetadata:
    return CheckpointMetadata(
        records_processed=1,
        dq_contract_compatibility_hash=manifest.code_provenance.dq_contract_compatibility_hash,
        pipeline_name=manifest.pipeline_name,
        run_type=manifest.run_type.value,
        pipeline_version=manifest.code_provenance.pipeline_version,
        git_commit=manifest.code_provenance.git_commit,
        dependency_lock_hash=manifest.code_provenance.dependency_lock_hash,
        effective_config_hash=manifest.code_provenance.effective_config_hash,
        effective_config_artifact_id=manifest.code_provenance.effective_config_artifact_id,
        execution_fingerprint=manifest.execution_fingerprint,
        manifest_id=manifest.manifest_id,
        contract_ref=manifest.code_provenance.contract_ref,
        contract_version=manifest.code_provenance.contract_version,
        normalization_profile_ref="test-normalization-profile",
        normalization_profile_version="1.0.0",
        normalization_profile_hash="sha256:test-normalization-profile",
        exact_replay=True,
        input_snapshot_ids=tuple(
            str(item) for item in summary.get("input_snapshot_ids", [])
        ),
        input_snapshot_fingerprint=str(summary["input_snapshot_identity_fingerprint"]),
        silver_filter_compatibility_mode="structural_only_compat",
    )


@pytest.mark.parametrize("family", _PUBLISHED_SUPPORTED_BOUNDARY_FAMILIES)
def test_reproducibility_contract_family_exact_replay_evidence_closure(
    family: str,
) -> None:
    """Every published supported family must expose replay evidence anchors."""
    provider, entity, pipeline_name = _family_context(family)
    run_id = deterministic_run_uuid_from_callsite("test_reproducibility_contract_suite")
    input_snapshot = RunInputSnapshotRef(
        snapshot_id=f"{family}:snapshot-1",
        content_hash="content-hash-1",
        immutable_uri=f"bronze://{provider}/{entity}/snapshot-1.jsonl.zst",
        query_fingerprint="query-hash-1",
        captured_at=datetime(2025, 1, 1, 0, 0, tzinfo=UTC),
    )
    manifest = _make_manifest(
        manifest_id=f"manifest-family-{family.replace('.', '-')}",
        run_id=run_id,
        execution_fingerprint=f"fp-family-{family}",
        required_persistence_profile="forensic_grade",
        input_snapshots=(input_snapshot,),
        identity=_ManifestIdentity(
            pipeline_name=pipeline_name,
            provider=provider,
            entity=entity,
            contract_ref=family,
        ),
        execution_context="composite" if provider == "composite" else "ordinary",
    )
    if provider == "composite":
        child_pipeline = f"chembl_{entity}"
        manifest = replace(
            manifest,
            launch_context={
                **manifest.launch_context,
                "child_replay_manifests": {child_pipeline: f"child-{family}"},
            },
            resolved_config={
                **manifest.resolved_config,
                "seed": {"pipeline": child_pipeline},
            },
            source_refs=(
                RunSourceRef(
                    provider="chembl",
                    entity=entity,
                    pipeline_name=child_pipeline,
                    input_snapshots=(input_snapshot,),
                ),
            ),
        )
    ledger_entry = RunLedgerEntry(
        entry_id=f"entry-family-{family}",
        manifest_id=manifest.manifest_id,
        run_id=run_id,
        event_type="artifact_published",
        occurred_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
        event_family="artifact",
        status="success",
        stage="silver",
        dataset_ref=f"silver:{family}@1",
        lineage_fragment_id=f"silver:{family}@1#lineage",
        details={
            "artifact_path": f"silver/{provider}/{entity}",
            "metadata_path": f"silver/{provider}/{entity}/_metadata.yaml",
            "artifact_kind": "layer_output",
            "artifact_semantics": "semantic_table",
            "execution_fingerprint": manifest.execution_fingerprint,
            "manifest_id": manifest.manifest_id,
            "run_id": str(run_id),
        },
    )

    summary = build_diagnostics_summary(manifest, (ledger_entry,))
    compatibility = CheckpointCompatibilityService(
        NoOpLogger()
    ).validate_checkpoint_compatibility(
        _checkpoint_metadata_from_summary(manifest, summary),
        _checkpoint_metadata_from_summary(manifest, summary),
    )

    assert summary["replay_capability"] == "exact_replay_supported"
    assert summary["input_snapshot_identity_fingerprint"]
    assert summary["produced_artifact_trace"]["complete"] is True
    assert summary["artifact_publication_closure"] == "closed"
    assert summary["resume_contract"]["continuation_mode"] == "exact_replay"
    assert compatibility.compatible is True
