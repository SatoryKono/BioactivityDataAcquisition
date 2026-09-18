"""Stream B APP: leftover 1-2 line runner, workflow, replay, and diagnostics branches."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core._filtered_data_source_support import load_csv_filter_ids
from bioetl.application.core._runner_support import PipelineRunnerSupportMixin
from bioetl.application.core.lifecycle.checkpoint_load_validation import (
    _handle_missing_compatibility_context_result,
)
from bioetl.application.observability.replay_write_risk import _has_explicit_clear
from bioetl.application.services.control_plane.forensic.diagnostics_support import (
    coerce_int,
    inspection_service_factory_from_ports,
)
from bioetl.application.services.control_plane.manifest._inspection_support import (
    RunManifestInspectionDiffClassificationMixin,
)
from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
    _copy_projection_value,
    _has_missing_anchors,
)
from bioetl.application.services.control_plane.replay.closure_claims import (
    universal_scope_claim_block_reason,
)
from bioetl.application.services.control_plane.replay.historical_closure_policy import (
    _suggested_disposition,
)
from bioetl.application.services.control_plane.replay.historical_corpus_policy import (
    certification_scope_for_context,
)
from bioetl.application.services.workflow._observability_workflow_evidence_support import (
    classify_checkpoint_status,
    has_composite_correlation_policy_gap,
)
from bioetl.application.services.workflow._observability_workflow_quarantine_support import (
    resolve_quarantine_summary_for_run,
)
from bioetl.application.services.workflow.control_plane.execution_recording_payloads import (
    build_step_completion_details,
)
from bioetl.application.services.workflow.workflow_runner_models import (
    WorkflowStepExecutionResult,
)
from bioetl.application.services.workflow.workflow_runner_support import (
    workflow_status_to_gauge_value,
)
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_filter_offset_and_checkpoint_loaded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = SimpleNamespace(
        _filter_reader=object(),
        _filter_config=SimpleNamespace(source_path=""),
    )
    await load_csv_filter_ids(state)  # type: ignore[arg-type]
    mixin = PipelineRunnerSupportMixin()
    assert mixin._extract_checkpoint_offset(None) is None
    monkeypatch.setattr(
        "bioetl.application.core.lifecycle.checkpoint_load_validation.handle_missing_compatibility_context",
        lambda **_k: CheckpointMetadata(records_processed=1),
    )
    loaded = _handle_missing_compatibility_context_result(
        logger=MagicMock(),
        pipeline_name="chembl_activity",
        compatibility_policy=MagicMock(),
        checkpoint_metadata=CheckpointMetadata(records_processed=1),
        current_metadata=None,
        service_available=False,
        operation_errors=(RuntimeError,),
        emit_checkpoint_load_status=lambda _status: None,
    )
    assert loaded is not None
    assert loaded.records_processed == 1


def test_workflow_replay_and_diagnostics_leftovers() -> None:
    assert workflow_status_to_gauge_value("running") == 1.0
    details = build_step_completion_details(
        WorkflowStepExecutionResult(
            step_id="s1",
            step_kind="transform",
            status="failed",
            payload=None,
        )
    )
    assert details is None or isinstance(details, dict)
    info = SimpleNamespace(metadata={"status": "mismatched_run_context"})
    assert classify_checkpoint_status(info) == ["checkpoint_mismatched_run"]  # type: ignore[arg-type]
    assert has_composite_correlation_policy_gap(
        {"composite_projection": {"composite_run_id_consistent": False}}
    )
    assert _has_missing_anchors(1) is True
    assert _copy_projection_value("ids", ["a"]) == ["a"]
    factory = object()
    assert (
        inspection_service_factory_from_ports(MagicMock(), None, lambda: factory)()  # type: ignore[arg-type,return-value]
        is factory
    )
    assert coerce_int("nope") == 0
    assert universal_scope_claim_block_reason(
        unresolved_records=(),
        has_irrecoverable=False,
        unsupported_count=0,
    ) == "historical_replay_closure_program_not_yet_completed"
    assert (
        _suggested_disposition(
            SimpleNamespace(certification_status="outside_certified_historical_scope")  # type: ignore[arg-type]
        )
        == "outside_universal_claim_scope"
    )
    assert certification_scope_for_context("source") == "historical_source_replay"
    assert (
        RunManifestInspectionDiffClassificationMixin._resolve_replay_relationship(
            left_manifest=SimpleNamespace(  # type: ignore[arg-type]
                replay_of_manifest_id=None,
                replay_of_run_id=None,
                manifest_id="left",
                run_id="1",
            ),
            right_manifest=SimpleNamespace(  # type: ignore[arg-type]
                replay_of_manifest_id="left",
                replay_of_run_id=None,
                manifest_id="right",
                run_id="2",
            ),
        )
        == "right_is_exact_replay_of_left"
    )
    assert (
        RunManifestInspectionDiffClassificationMixin._resolve_replay_relationship(
            left_manifest=SimpleNamespace(  # type: ignore[arg-type]
                replay_of_manifest_id=None,
                replay_of_run_id=None,
                manifest_id="left",
                run_id="1",
            ),
            right_manifest=SimpleNamespace(  # type: ignore[arg-type]
                replay_of_manifest_id=None,
                replay_of_run_id=None,
                manifest_id="right",
                run_id="2",
            ),
        )
        == "none"
    )
    manifest = SimpleNamespace(
        run_type="incremental",
        launch_context={"clear_before_run": True},
    )
    assert _has_explicit_clear(manifest) is True  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_quarantine_summary_oserror() -> None:
    quarantine = MagicMock()
    quarantine.get_filtered_stats = AsyncMock(side_effect=OSError("gone"))
    assert (
        await resolve_quarantine_summary_for_run(
            quarantine_service=quarantine,
            run_id="run-1",
            pipeline_name="chembl_activity",
            run_manifest=None,
        )
        is None
    )
