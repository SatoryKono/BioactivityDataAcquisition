"""Stream B APP: leftover state-flow, evidence, debug-export, and runner branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.batch_executor_state_flow import process_stateful_batch
from bioetl.application.core.lifecycle.batch_fsm import BatchExecutionCommand
from bioetl.application.observability.control_plane_evidence.checkpoint_validation import (
    _checkpoint_anchor_checks,
)
from bioetl.application.observability.control_plane_evidence.lineage_identity import (
    identity_gaps,
)
from bioetl.application.observability.control_plane_evidence.retention import (
    _artifact_matches_manifest,
)
from bioetl.application.observability.control_plane_integrity_metrics import (
    ControlPlaneIntegrityMetricsService,
)
from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)
from bioetl.application.pipelines.uniprot.extractors._comment_structured_facets import (
    _extract_cofactors_raw,
)
from bioetl.application.services.checkpoint._checkpoint_compatibility_runtime_identity_details import (
    _degraded_runtime_anchor_detail,
)
from bioetl.application.services.control_plane.manifest.diagnostics import replay_state as replay
from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionService,
)
from bioetl.application.services.export_lineage.debug_export_service import (
    DebugExportConfig,
    DebugExportService,
)
from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    _upstream_completeness_evidence,
)
from bioetl.domain.lineage import LineageGraphFragment, LineageNodeRef, LineageNodeType
from bioetl.domain.types import RunID

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_stateful_batch_skips_commit_without_command() -> None:
    assembled = SimpleNamespace(
        new_state="assembled",
        commands={BatchExecutionCommand.PROCESS_BATCH},
    )
    processed = SimpleNamespace(new_state="processed", commands=set())
    host = SimpleNamespace(
        _fsm_state="start",
        _query_string=None,
        _fsm=SimpleNamespace(advance=MagicMock(side_effect=[assembled, processed])),
        _processing_port=SimpleNamespace(process_batch=AsyncMock(return_value="ok")),
        _execution_state_service=MagicMock(),
    )
    await process_stateful_batch(host, [{"id": 1}], 0)  # type: ignore[arg-type]
    host._execution_state_service.commit_successful_batch.assert_not_called()


def test_evidence_integrity_replay_and_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = SimpleNamespace(
        run_id="run-1",
        manifest_id="m1",
        pipeline_name="chembl_activity",
        run_type=SimpleNamespace(value="full"),
        execution_fingerprint="fp",
    )
    checks = _checkpoint_anchor_checks(
        manifest=manifest,  # type: ignore[arg-type]
        checkpoint_run_id="run-1",
        metadata={},
    )
    assert checks[0].reason == "checkpoint_anchor_incomplete"
    node = LineageNodeRef(
        node_type=LineageNodeType.RUN,
        node_id="run:bad",
        attributes={},
    )
    fragment = LineageGraphFragment(
        fragment_id="f1",
        nodes=(node,),
        edges=(),
        run_id="run-1",
        manifest_id="m1",
    )
    gaps = identity_gaps(manifest=manifest, fragments=(fragment,))  # type: ignore[arg-type]
    assert "run_node:run:bad" in gaps
    artifact = SimpleNamespace(artifact_id="snap-1", protected_by=())
    snap_manifest = SimpleNamespace(
        manifest_id="m1",
        run_id="run-1",
        code_provenance=SimpleNamespace(effective_config_artifact_id=None),
        source_refs=(
            SimpleNamespace(input_snapshots=(SimpleNamespace(snapshot_id="snap-1"),)),
        ),
    )
    assert _artifact_matches_manifest(artifact, snap_manifest) is True  # type: ignore[arg-type]
    assert (
        _degraded_runtime_anchor_detail(
            manifest_id=None,
            contract_ref=None,
            contract_version=None,
            effective_config_hash=None,  # type: ignore[arg-type]
            effective_config_artifact_id=None,
        )
        == ""
    )
    monkeypatch.setattr(
        "bioetl.application.observability.control_plane_integrity_metrics.manifest_expects_ledger",
        lambda _m: False,
    )
    metrics = ControlPlaneIntegrityMetricsService(
        manifest_port=SimpleNamespace(list_all=lambda: [object()]),  # type: ignore[arg-type]
        ledger_port=MagicMock(),
        metrics=MagicMock(),
    )
    assert metrics.refresh() == ()


@pytest.mark.asyncio
async def test_debug_export_protein_class_and_lineage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _written() -> str:
        return "written"

    service = DebugExportService(
        config=DebugExportConfig(enabled=True),
        run_id=RunID(uuid4()),
        pipeline_id="chembl_activity",
        provider_id="chembl",
        writer=SimpleNamespace(write_pack=lambda **_k: _written()),
    )
    monkeypatch.setattr(service, "build_pack", lambda **_k: {})
    assert await service.persist() == "written"
    service.record_transform_failure(raw_record={"id": 1}, record_index=0)
    host = ProteinClassTransformer.__new__(ProteinClassTransformer)
    monkeypatch.setattr(
        "bioetl.application.pipelines.chembl.protein_class_transformer.BaseChemblTransformer.transform_pre_silver",
        AsyncMock(return_value={"ok": True}),
    )
    assert (
        await host.transform_pre_silver(object(), {"protein_class_id": 5}, 0)  # type: ignore[arg-type]
        == {"ok": True}
    )
    assert _extract_cofactors_raw({"COFACTOR": [{"cofactors": ["x"]}]}) == []
    store = MagicMock()
    store.list_by_manifest_id.return_value = ()
    store.list_by_run_id.return_value = ()
    inspector = LineageInspectionService(lineage_store=store, manifest_port=None)
    monkeypatch.setattr(LineageInspectionService, "_parse_run_id", lambda self, ident: None)
    assert inspector._resolve_via_direct_indexes("missing") is None
    monkeypatch.setattr(LineageInspectionService, "_parse_run_id", lambda self, ident: "run-1")
    assert inspector._resolve_via_direct_indexes("run-1") is None
    loader = SimpleNamespace(load_latest_report=lambda: {"universal_claim": "nope"})
    inspection = RunManifestInspectionService.__new__(RunManifestInspectionService)
    inspection.historical_replay_universe_report_loader = loader
    diagnostics: dict[str, object] = {}
    inspection._attach_historical_replay_universe_claim(diagnostics)
    assert diagnostics == {}


def test_replay_reason_and_reconcile_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(replay, "_collect_append_mode_semantic_sinks", lambda _m: ())
    monkeypatch.setattr(replay, "_has_partial_input_snapshot_envelope", lambda _e: False)
    monkeypatch.setattr(
        replay, "_has_historical_composite_certified_snapshots", lambda _s: False
    )
    monkeypatch.setattr(
        replay, "_has_historical_source_certified_snapshots", lambda _s: False
    )
    monkeypatch.setattr(replay, "_resolve_exact_replay_supported_reason", lambda **_k: None)
    monkeypatch.setattr(replay, "_requires_resume_without_snapshot_reason", lambda **_k: False)
    monkeypatch.setattr(replay, "_is_composite_execution_context", lambda _m: False)
    reason = replay._resolve_replay_capability_reason(
        manifest=SimpleNamespace(),  # type: ignore[arg-type]
        input_snapshots=[],
        resume_requested=False,
        policy_assessment=SimpleNamespace(snapshot_envelope={}),
        replay_family_context=SimpleNamespace(
            profile=SimpleNamespace(strict_exact_replay_supported=True)
        ),
    )
    assert reason == "immutable_input_snapshots_missing"
    evidence = _upstream_completeness_evidence(
        {"step": {"reference_completeness_evidence": {"reference_identity": ""}}},
        "silver/chembl/activity",
    )
    assert evidence == {"reference_identity": ""}
