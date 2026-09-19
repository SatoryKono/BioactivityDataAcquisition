"""Behavioral coverage for composite and service guard tails in #10469."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from bioetl.application.composite._preflight_reporting import (
    PreflightValidationReportingMixin,
)
from bioetl.application.composite.merger_input_mixin import _MergeInputLoaderMixin
from bioetl.application.composite.runner_pkg.runner_control_plane_phase_followup import (
    _record_enricher_completion,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_runtime import (
    handle_dry_run_merge_skip,
)
from bioetl.application.services.control_plane.manifest.inspection_verification import (
    RunManifestInspectionCompareMixin,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.replay_parentage import (
    _is_full_scan_idempotent_rebuild,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_summary import (
    _merge_ledger_snapshots_by_id,
)
from bioetl.application.services.control_plane.workflow.inspection_service import (
    WorkflowInspectionService,
)
from bioetl.application.services.execution.pipeline_run_lifecycle_service import (
    PipelineRunLifecycleService,
)
from bioetl.application.services.export_lineage.export_manifest_attribution import (
    provider_attribution_payload,
)
from bioetl.application.services.quality.data_quality_thresholds import (
    DataQualityThresholdMixin,
)


pytestmark = pytest.mark.unit


def test_preflight_profile_summary_is_quiet_without_profiles() -> None:
    host = object.__new__(PreflightValidationReportingMixin)
    host._logger = Mock()

    host._log_profile_loading_summary({})

    host._logger.debug.assert_not_called()


@pytest.mark.asyncio
async def test_merge_input_requires_an_explicit_silver_reader() -> None:
    host = object.__new__(_MergeInputLoaderMixin)
    host._delta_reader = None
    host._storage = None

    with pytest.raises(RuntimeError, match="requires delta_reader or silver_reader"):
        await host._read_silver_table("silver/chembl_assay")


def test_enricher_completion_delegates_structured_payload() -> None:
    ledger = Mock()
    ledger.record_composite_enricher_completed.return_value = "entry"

    assert (
        _record_enricher_completion(ledger, name="crossref", data={"records": 3})
        == "entry"
    )
    ledger.record_composite_enricher_completed.assert_called_once_with(
        enricher_name="crossref", result={"records": 3}
    )


def test_dry_run_merge_shortcut_rejects_live_runtime() -> None:
    host = SimpleNamespace(_runtime=SimpleNamespace(dry_run=False))

    with pytest.raises(RuntimeError, match="requires runtime.dry_run=True"):
        handle_dry_run_merge_skip(host, SimpleNamespace())


def test_manifest_compare_ignores_untyped_artifact_refs() -> None:
    assert (
        RunManifestInspectionCompareMixin._artifact_refs_from_diagnostics(
            {"artifact_refs": "invalid"}
        )
        == ()
    )


def test_manifest_launch_context_marks_full_scan_rebuild() -> None:
    manifest = SimpleNamespace(
        launch_context={"full_scan_idempotent_rebuild": True},
        runtime_config={},
        resolved_config={},
    )

    assert _is_full_scan_idempotent_rebuild(manifest)


def test_snapshot_summary_ignores_duplicate_with_same_content_hash() -> None:
    existing = {"snapshot-1": {"snapshot_id": "snapshot-1", "content_hash": "sha256:a"}}

    conflicts = _merge_ledger_snapshots_by_id(
        existing,
        [{"snapshot_id": "snapshot-1", "content_hash": "sha256:a"}],
    )

    assert conflicts == []
    assert len(existing) == 1


def test_workflow_inspection_returns_none_for_unknown_run_id() -> None:
    state_port = Mock()
    state_port.get_by_run_id.return_value = None
    service = WorkflowInspectionService(
        manifest_port=Mock(), ledger_port=Mock(), state_port=state_port
    )
    run_id = str(uuid4())

    assert service.inspect_run_id(run_id) is None
    state_port.get_by_run_id.assert_called_once()


def test_lifecycle_stage_start_preserves_explicit_timestamp() -> None:
    clock = Mock()
    run = Mock()
    service = PipelineRunLifecycleService(clock=clock)
    started_at = datetime(2026, 9, 16, tzinfo=UTC)

    service.stage_started(run, "extract", started_at=started_at)

    run.record_stage_start.assert_called_once_with(
        stage="extract", started_at=started_at
    )
    clock.now.assert_not_called()


def test_unknown_provider_has_explicit_nonstrict_attribution() -> None:
    result = provider_attribution_payload("private-provider", strict=False)

    assert result["provider"] == "private-provider"
    assert result["license_name"] == "unknown"
    assert result["source_url"] is None


def test_disabled_hard_threshold_does_not_emit_failure() -> None:
    host = object.__new__(DataQualityThresholdMixin)
    host._config = SimpleNamespace(hard_fail_threshold=1.1)
    host._logger = Mock()
    host._pipeline_metrics = Mock()
    host._pipeline_name = "chembl_assay"

    host._check_hard_threshold(error_rate=1.0, quarantined_count=2)

    host._logger.error.assert_not_called()
    host._pipeline_metrics.record_dq_validation_failures.assert_not_called()
