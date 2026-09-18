"""Stream B APP: leftover checkpoint, GO, lineage, and preflight branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite._preflight_orchestration import (
    PreflightSchemaOrchestrationMixin,
)
from bioetl.application.pipelines.uniprot.extractors._crossref_go import (
    extract_go_by_aspect,
    extract_go_terms,
)
from bioetl.application.services.checkpoint._checkpoint_compatibility_execution_validation import (
    _validate_exact_replay_and_snapshots,
    _validate_mismatch_reasons,
)
from bioetl.application.services.checkpoint._checkpoint_compatibility_runtime_identity_details import (
    _checkpoint_execution_identity_fallback_detail,
    generate_details,
)
from bioetl.application.services.checkpoint.checkpoint_service import CheckpointService
from bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support import (
    _build_refresh_summary_update,
)
from bioetl.application.services.lineage.lineage_inspection_service import (
    LineageInspectionService,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

pytestmark = pytest.mark.unit


def test_go_terms_skip_missing_ids() -> None:
    xrefs = [{"database": "GO"}]
    assert extract_go_terms(xrefs) is None
    assert extract_go_by_aspect(xrefs, "F") is None


def test_checkpoint_identity_details_and_snapshot_mismatch() -> None:
    assert _checkpoint_execution_identity_fallback_detail({"k": "v"})
    payload = generate_details(
        phase_result={"ok": True},
        config_result={"ok": True},
        execution_identity_result={"ok": True},
        schema_result={"ok": True},
        current_identity_details={"id": "a"},
        checkpoint_identity_details={"id": "b"},
        mode="strict",
        allow_policy_override=False,
        max_schema_version_delta=0,
    )
    assert payload["compatibility_mode"] == "strict"
    messages: list[str] = []
    current = CheckpointMetadata(
        records_processed=1,
        execution_fingerprint="cur",
        exact_replay=True,
        input_snapshot_fingerprint="fp",
        input_snapshot_ids=("s1",),
    )
    checkpoint = CheckpointMetadata(
        records_processed=1,
        execution_fingerprint="chk",
        exact_replay=True,
        input_snapshot_fingerprint="fp",
        input_snapshot_ids=("s2",),
    )
    _validate_mismatch_reasons(
        current,
        checkpoint,
        {"reason": "checkpoint_execution_identity_fallback_mismatch"},
        messages,
    )
    assert messages
    snapshot_messages: list[str] = []
    compatible = _validate_exact_replay_and_snapshots(
        current, checkpoint, snapshot_messages, True
    )
    assert compatible is False


@pytest.mark.asyncio
async def test_checkpoint_admin_without_tracer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "bioetl.application.services.checkpoint.checkpoint_service.get_checkpoint_impl",
        AsyncMock(return_value="cp"),
    )
    monkeypatch.setattr(
        "bioetl.application.services.checkpoint.checkpoint_service.get_checkpoint_for_manifest_id_impl",
        AsyncMock(return_value="m"),
    )
    monkeypatch.setattr(
        "bioetl.application.services.checkpoint.checkpoint_service.delete_checkpoint_impl",
        AsyncMock(return_value=True),
    )
    service = CheckpointService(
        checkpoint_port=MagicMock(),
        logger=MagicMock(),
        tracer=None,
    )
    assert await service.get_checkpoint("chembl_activity") == "cp"
    assert await service.get_checkpoint_for_manifest_id("chembl_activity", "m1") == "m"
    assert await service.delete_checkpoint("chembl_activity") is True


def test_lineage_preflight_and_replay_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MagicMock()
    port = MagicMock()
    service = LineageInspectionService(lineage_store=store, manifest_port=port)
    monkeypatch.setattr(LineageInspectionService, "_parse_run_id", lambda self, ident: "run-1")
    port.get.return_value = None
    port.get_by_run_id.return_value = None
    assert service._resolve_via_manifest("missing") is None

    class _Host(PreflightSchemaOrchestrationMixin):
        def _load_pipeline_profile(self, pipeline_name: str) -> object:
            return {"ok": True} if pipeline_name == "chembl_document" else None

        def _register_source_aliases(self, result: dict[str, object], **kwargs: object) -> None:
            result[str(kwargs.get("pipeline_name"))] = kwargs.get("fields")

    host = _Host()
    config = SimpleNamespace(
        seed=SimpleNamespace(pipeline="chembl_activity"),
        dependencies=(SimpleNamespace(pipeline="chembl_document"),),
        enrichers=(),
    )
    loaded = host._load_source_profiles(config)  # type: ignore[arg-type]
    assert "chembl_document" in loaded

    refresh_context = SimpleNamespace()
    monkeypatch.setattr(
        "bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support._build_refresh_replay_projection",
        lambda _ctx: SimpleNamespace(
            replay_payload={
                "replay_readiness_verdict": "lifecycle_projection_only",
                "operator_replay_mode": "Lifecycle Projection",
            },
            snapshot_status="ok",
            resume_contract={"ok": True},
        ),
    )
    monkeypatch.setattr(
        "bioetl.application.services.control_plane.manifest.diagnostics.replay_refresh_support._refresh_replay_summary_update_snapshot_fields",
        lambda updated, refresh_context, snapshot_status: updated,
    )
    updated = _build_refresh_summary_update(
        summary={"composite_resume_rich_replay_supported": True},
        refresh_context=refresh_context,  # type: ignore[arg-type]
    )
    assert updated.payload["operator_replay_mode"] == "Resume"
