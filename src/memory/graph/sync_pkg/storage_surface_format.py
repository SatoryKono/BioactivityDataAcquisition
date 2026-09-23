"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Mapping

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.default_batch_size import (
    CHEMBL_ACTIVITY_CONTRACT_REF,
    EFFECTIVE_CONFIG_ARTIFACT_REF,
    RUN_LEDGER_ARTIFACT_REF,
    RUN_MANIFEST_ARTIFACT_REF,
    RUN_MANIFEST_INSPECTION_DOC_PATH,
    RUN_MANIFEST_LEDGER_DOC_PATH,
    TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "RUN_INSTANCE_CHAIN_ARTIFACT_REFS",
    "RUN_INSTANCE_CHAIN_DOCS",
    "RUN_INSTANCE_PRIMARY_ARTIFACT_REFS",
    "RUN_INSTANCE_PRIMARY_DOCS",
    "RUN_INSTANCE_SPECS",
    "RUN_INSTANCE_TRACEABILITY_DOCS",
    "_chembl_activity_run_instance_fixture",
    "_run_instance_definition_spec",
    "_run_instance_fixture_spec",
    "_storage_surface_format",
]


def _storage_surface_format(snapshot: GraphSnapshot, storage: NodeKey) -> str | None:
    storage_node = snapshot.nodes.get(storage)
    if storage_node is None:
        return None
    format_value = storage_node.properties.get("format")
    return str(format_value) if format_value is not None else None


def _run_instance_fixture_spec(
    *,
    manifest_id: str,
    run_id: str,
    source_path: str,
    doc_paths: tuple[str, ...],
    artifact_refs: tuple[str, ...],
    **extra: object,
) -> dict[str, object]:
    spec: dict[str, object] = {
        "manifest_id": manifest_id,
        "run_id": run_id,
        "source_path": source_path,
        "doc_paths": doc_paths,
        "artifact_refs": artifact_refs,
    }
    spec.update(extra)
    return spec


RUN_INSTANCE_PRIMARY_DOCS = (RUN_MANIFEST_LEDGER_DOC_PATH,)
RUN_INSTANCE_CHAIN_DOCS = (
    RUN_MANIFEST_LEDGER_DOC_PATH,
    RUN_MANIFEST_INSPECTION_DOC_PATH,
)
RUN_INSTANCE_TRACEABILITY_DOCS = (
    RUN_MANIFEST_LEDGER_DOC_PATH,
    TRACEABILITY_SIGNAL_OWNERSHIP_DOC_PATH,
)
RUN_INSTANCE_PRIMARY_ARTIFACT_REFS = (
    RUN_MANIFEST_ARTIFACT_REF,
    EFFECTIVE_CONFIG_ARTIFACT_REF,
)
RUN_INSTANCE_CHAIN_ARTIFACT_REFS = (
    RUN_MANIFEST_ARTIFACT_REF,
    RUN_LEDGER_ARTIFACT_REF,
    EFFECTIVE_CONFIG_ARTIFACT_REF,
)
RUN_INSTANCE_SPECS = (
    (
        "manifest-left",
        "00000000-0000-0000-0000-000000000301",
        "tests/integration/ci/test_reproducibility_contract_suite.py",
        RUN_INSTANCE_PRIMARY_DOCS,
        RUN_INSTANCE_PRIMARY_ARTIFACT_REFS,
        {
            "execution_fingerprint": "fp-stable",
            "created_at": "2025-01-01T00:00:00+00:00",
            "effective_config_artifact_id": "eca-123",
            "config_hash": "deadbeef",
            "replay_capability": "rebuild_only",
            "surface_kind": "reproducibility_fixture",
            "lifecycle_status": "fixture_manifest_only",
        },
    ),
    (
        "manifest-chain-smoke",
        "00000000-0000-0000-0000-000000000103",
        "tests/unit/application/services/test_run_manifest_inspection_service.py",
        RUN_INSTANCE_CHAIN_DOCS,
        (
            *RUN_INSTANCE_CHAIN_ARTIFACT_REFS,
            "lineage::run_index",
        ),
        {
            "effective_config_artifact_id": "eca-smoke-1",
            "config_hash": "hash-smoke",
            "surface_kind": "lifecycle_smoke_fixture",
            "lifecycle_status": "success",
            "published_dataset_ref": "silver:chembl.activity@1",
            "lineage_fragment_id": "silver:fragment-smoke-1",
        },
    ),
    (
        "manifest-chain-2",
        "00000000-0000-0000-0000-000000000102",
        "tests/unit/application/services/test_run_manifest_inspection_service.py",
        RUN_INSTANCE_TRACEABILITY_DOCS,
        RUN_INSTANCE_CHAIN_ARTIFACT_REFS,
        {
            "effective_config_artifact_id": "eca-chain-2",
            "surface_kind": "dq_failure_fixture",
            "lifecycle_status": "failed",
            "dq_disposition": "fail",
            "dq_rule_id": "gold.not_null.id",
            "dq_report_path": "data/output/gold/chembl/activity/_dq.json",
        },
    ),
    (
        "manifest-composite-quarantine",
        "00000000-0000-0000-0000-000000000402",
        "tests/integration/ci/test_reproducibility_contract_suite.py",
        RUN_INSTANCE_TRACEABILITY_DOCS,
        RUN_INSTANCE_CHAIN_ARTIFACT_REFS,
        {
            "execution_fingerprint": "fp-stable",
            "created_at": "2025-01-01T00:00:00+00:00",
            "effective_config_artifact_id": "eca-123",
            "config_hash": "deadbeef",
            "surface_kind": "cross_validation_quarantine_fixture",
            "lifecycle_status": "quarantined",
            "last_event_at": "2025-02-03T00:00:00+00:00",
            "replay_contract": "excluded_from_exact_replay",
            "diagnostic_scope": "composite_cross_validation_quarantine",
        },
    ),
)


def _chembl_activity_run_instance_fixture(
    *,
    manifest_id: str,
    run_id: str,
    source_path: str,
    doc_paths: tuple[str, ...],
    artifact_refs: tuple[str, ...],
    **extra: object,
) -> dict[str, object]:
    return _run_instance_fixture_spec(
        manifest_id=manifest_id,
        run_id=run_id,
        source_path=source_path,
        doc_paths=doc_paths,
        artifact_refs=artifact_refs,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        run_type="incremental",
        contract_ref=CHEMBL_ACTIVITY_CONTRACT_REF,
        contract_version="1.0.0",
        **extra,
    )


def _run_instance_definition_spec(
    definition: tuple[
        str, str, str, tuple[str, ...], tuple[str, ...], Mapping[str, object]
    ],
) -> dict[str, object]:
    manifest_id, run_id, source_path, doc_paths, artifact_refs, extra = definition
    return _chembl_activity_run_instance_fixture(
        manifest_id=manifest_id,
        run_id=run_id,
        source_path=source_path,
        doc_paths=doc_paths,
        artifact_refs=artifact_refs,
        **dict(extra),
    )
