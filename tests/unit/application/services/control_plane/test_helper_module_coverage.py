# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Coverage anchors for split control-plane and batch helper modules."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest

from bioetl.application.core.batch_operation_errors import OPERATION_ERRORS
from bioetl.application.services.control_plane.manifest.diagnostics.diagnostic_context import (
    extract_diagnostic_context,
    update_correlation_anchor_gaps,
)
from bioetl.application.services.control_plane.manifest.diagnostics.replay_invariants.nested_mapping import (
    lookup_mapping_path,
)
from bioetl.application.services.control_plane.manifest.inspection_result_model import (
    RunManifestInspectionResult,
)
from bioetl.application.services.control_plane.replay._historical_snapshot_certification_modes import (
    HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED,
    HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED,
)
from bioetl.application.services.control_plane.replay._historical_snapshot_materialization_modes import (
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
    MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION,
    POST_MANIFEST_SNAPSHOT_MATERIALIZATION_MODES,
)
from bioetl.application.services.control_plane.workflow.execution_incremental_metadata import (
    extract_incremental_metadata,
)
from bioetl.application.services.control_plane.workflow.execution_recording import (
    WorkflowExecutionRecorder,
)
from bioetl.domain.control_plane import RunLedgerEntry, WorkflowExecutionState
from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import RunID
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from tests.unit.application.services.run_manifest_test_support import make_run_manifest

pytestmark = pytest.mark.unit


def _run_id() -> RunID:
    return RunID(UUID("00000000-0000-0000-0000-000000000601"))


def _ledger_entry(
    *,
    event_type: str = "checkpoint_saved",
    event_family: str | None = "checkpoint",
    details: dict[str, object] | None = None,
) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id="entry-1",
        manifest_id="manifest-1",
        run_id=_run_id(),
        event_type=event_type,
        event_family=event_family,
        occurred_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        details=details,
    )


def test_split_batch_operation_errors_exports_expected_exception_tuple() -> None:
    assert BioETLError in OPERATION_ERRORS
    assert RuntimeError in OPERATION_ERRORS
    assert TypeError in OPERATION_ERRORS


def test_diagnostic_context_extracts_anchors_and_counts_missing_gaps() -> None:
    entry = _ledger_entry(
        details={
            "_diagnostic": {
                "resolved_config_hash": "r" * 64,
                "effective_config_hash": None,
                "contract_ref": "chembl.activity",
                "data_contract_version": "1.0.0",
            }
        }
    )
    gaps: defaultdict[str, int] = defaultdict(int)

    assert extract_diagnostic_context(entry)["contract_ref"] == "chembl.activity"

    update_correlation_anchor_gaps(gaps, entry)

    assert dict(gaps) == {
        "effective_config_hash": 1,
        "composite_run_id": 1,
    }


def test_diagnostic_context_ignores_manifest_created_diagnostic_event() -> None:
    gaps: defaultdict[str, int] = defaultdict(int)

    update_correlation_anchor_gaps(
        gaps,
        _ledger_entry(event_type="manifest_created", event_family="diagnostic"),
    )

    assert dict(gaps) == {}


def test_replay_invariant_nested_mapping_facade_delegates_lookup() -> None:
    assert lookup_mapping_path({"a": {"b": 42}}, "a", "b") == 42
    assert lookup_mapping_path({"a": object()}, "a", "b") is None
    assert lookup_mapping_path({"a": {"b": 1}}, "a", "b") == 1


def test_corpus_service_shares_export_tuple_without_importing_models() -> None:
    import ast
    from pathlib import Path

    from bioetl.application.services.control_plane.replay import (
        _historical_record_payload as payload,
    )
    from bioetl.application.services.control_plane.replay import (
        historical_corpus_models as models,
    )
    from bioetl.application.services.control_plane.replay import (
        historical_corpus_service as service,
    )

    assert models.CORPUS_MODEL_PUBLIC_NAMES is payload.CORPUS_MODEL_PUBLIC_NAMES
    assert service.CORPUS_MODEL_PUBLIC_NAMES is payload.CORPUS_MODEL_PUBLIC_NAMES
    tree = ast.parse(Path(service.__file__).read_text(encoding="utf-8"))
    imported_modules = [
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    ] + [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    assert not any(
        module.endswith("historical_corpus_models") for module in imported_modules
    )


def test_manifest_inspection_result_model_serializes_payload() -> None:
    manifest = make_run_manifest(manifest_id="manifest-helper-coverage")
    entry = _ledger_entry(details={"_diagnostic": {"contract_ref": "chembl.activity"}})
    result = RunManifestInspectionResult(
        manifest=manifest,
        ledger_entries=(entry,),
        diagnostics={"replay_readiness_verdict": "exact_replay_ready"},
        identity_graph={"manifest_id": manifest.manifest_id},
    )

    payload = result.to_dict()

    assert payload["manifest"]["manifest_id"] == "manifest-helper-coverage"
    assert payload["ledger_entries"][0]["entry_id"] == "entry-1"
    assert payload["diagnostics"] == {"replay_readiness_verdict": "exact_replay_ready"}
    assert payload["identity_graph"] == {"manifest_id": manifest.manifest_id}


def test_historical_replay_mode_constant_helpers_are_canonical() -> None:
    assert HISTORICAL_SOURCE_SNAPSHOT_CERTIFIED in (
        POST_MANIFEST_SNAPSHOT_MATERIALIZATION_MODES
    )
    assert HISTORICAL_COMPOSITE_REPLAY_ENVELOPE_CERTIFIED in (
        POST_MANIFEST_SNAPSHOT_MATERIALIZATION_MODES
    )
    assert LIVE_CAPTURE_SNAPSHOT_MATERIALIZED in (
        POST_MANIFEST_SNAPSHOT_MATERIALIZATION_MODES
    )
    assert MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION == (
        "mixed_post_manifest_snapshot_materialization"
    )


def test_extract_incremental_metadata_reads_first_pipeline_step() -> None:
    config = WorkflowConfig(
        name="workflow",
        steps=(
            TransformStepConfig(
                step_id="prepare",
                transform_name="prepare_manifest",
            ),
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
                run_options=WorkflowRunOptionsConfig(start_offset=5, limit=10),
            ),
        ),
    )

    assert extract_incremental_metadata(config) == (5, 10)
    assert extract_incremental_metadata(
        WorkflowConfig(
            name="transform-only",
            steps=(
                TransformStepConfig(
                    step_id="prepare",
                    transform_name="prepare_manifest",
                ),
            ),
        )
    ) == (None, None)


def test_workflow_execution_recorder_context_holds_mutable_state_owner() -> None:
    state = WorkflowExecutionState(
        workflow_run_id=_run_id(),
        manifest_id="manifest-1",
        workflow_name="chembl_baseline",
        execution_fingerprint="fp-1",
        status="pending",
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        completed_at=None,
        selected_step_ids=("extract",),
        steps=(),
        completed_transform_fingerprints={},
    )
    recorder = WorkflowExecutionRecorder(
        ledger=SimpleNamespace(),
        state_port=SimpleNamespace(save=lambda saved_state: saved_state),
        state=state,
    )

    assert recorder.state is state
    assert recorder.ledger is not None
    assert recorder.state_port is not None
