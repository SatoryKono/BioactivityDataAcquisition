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
"""Unit tests for forensic diagnostics helper payloads."""

from __future__ import annotations

import pytest

from bioetl.application.services.control_plane.forensic.diagnostics_support import (
    _artifact_completeness,
    _checkpoint_compatibility_payload,
    _forensic_diff_payload,
    _lineage_closure_payload,
    _missing_evidence,
    _replay_capability_payload,
)
from bioetl.application.services.control_plane.manifest.inspection_models import (
    RunManifestDiffResult,
)
from bioetl.application.services.control_plane.manifest.inspection_result_model import (
    RunManifestInspectionResult,
)
from tests.unit.application.services.run_manifest_test_support import make_run_manifest


pytestmark = pytest.mark.unit


def _inspection_result(
    *,
    manifest_id: str = "manifest-forensic-1",
    diagnostics: dict[str, object] | None = None,
    ledger_entries: tuple[object, ...] = (),
) -> RunManifestInspectionResult:
    return RunManifestInspectionResult(
        manifest=make_run_manifest(manifest_id=manifest_id),
        ledger_entries=ledger_entries,
        diagnostics=diagnostics or {},
        identity_graph={},
    )


def test_artifact_completeness_marks_complete_when_artifacts_are_fully_linked() -> None:
    result = _inspection_result(
        diagnostics={
            "artifact_refs": [
                {"artifact_id": "silver:1", "metadata_path": "meta/1.json"},
                {"artifact_id": "silver:2", "metadata_path": "meta/2.json"},
            ],
            "published_artifact_count": "2",
            "missing_artifact_links": 0,
            "produced_artifact_trace": {
                "complete": True,
                "missing_requirements": [],
            },
        }
    )

    payload = _artifact_completeness(result)

    assert payload["manifest_id"] == "manifest-forensic-1"
    assert payload["published_artifact_count"] == 2
    assert payload["metadata_sidecar_count"] == 2
    assert payload["metadata_sidecar_missing_count"] == 0
    assert payload["produced_artifact_trace_complete"] is True
    assert payload["produced_artifact_trace_missing_requirements"] == []
    assert payload["complete"] is True


@pytest.mark.parametrize(
    ("supported", "expected_status"),
    [
        (None, "missing"),
        (True, "supported"),
        (False, "unsupported"),
    ],
)
def test_lineage_closure_payload_classifies_boundary_support(
    supported: bool | None,
    expected_status: str,
) -> None:
    diagnostics = (
        {}
        if supported is None
        else {"lineage_closure_boundary": {"supported": supported, "mode": "strict"}}
    )

    payload = _lineage_closure_payload(_inspection_result(diagnostics=diagnostics))

    assert payload["manifest_id"] == "manifest-forensic-1"
    assert payload["status"] == expected_status
    assert payload["supported"] is supported


def test_replay_capability_payload_compares_left_and_right_snapshots() -> None:
    left = _inspection_result(
        manifest_id="manifest-left",
        diagnostics={
            "replay_capability": "exact_replay_ready",
            "exact_replay_eligible": True,
            "exact_replay_blockers": [],
            "persistence_profile": {"attained_profile": "forensic_grade"},
        },
    )
    right = _inspection_result(
        manifest_id="manifest-right",
        diagnostics={
            "replay_capability": "rebuild_only",
            "exact_replay_eligible": False,
            "exact_replay_blockers": ["artifact_links_incomplete"],
            "persistence_profile": {"attained_profile": "replay_ready"},
        },
    )

    payload = _replay_capability_payload(left=left, right=right)

    assert payload["left"]["manifest_id"] == "manifest-left"
    assert payload["left"]["replay_capability"] == "exact_replay_ready"
    assert payload["right"]["manifest_id"] == "manifest-right"
    assert payload["right"]["exact_replay_blockers"] == ["artifact_links_incomplete"]
    assert payload["capability_match"] is False


def test_checkpoint_compatibility_payload_and_forensic_verdict_use_checkpoint_anchors() -> (
    None
):
    diff = RunManifestDiffResult(
        left_manifest_id="left",
        right_manifest_id="right",
        differences=(),
        classification="identical",
        semantic_equivalent=True,
        occurrence_only=False,
        cross_surface_replay_diff={
            "checkpoint_anchors": {
                "compatible": False,
                "matching_fields": ["pipeline_name"],
                "mismatched_fields": ["resolved_config_hash"],
            }
        },
    )

    compatibility = _checkpoint_compatibility_payload(diff.cross_surface_replay_diff)
    forensic = _forensic_diff_payload(diff)

    assert compatibility == {
        "available": True,
        "compatible": False,
        "matching_fields": ["pipeline_name"],
        "mismatched_fields": ["resolved_config_hash"],
    }
    assert forensic["verdict"] == "checkpoint_incompatible"


def test_missing_evidence_reports_expected_forensic_gaps() -> None:
    result = _inspection_result(
        diagnostics={
            "published_artifact_count": 0,
            "missing_artifact_links": 2,
            "artifact_refs": [{"artifact_id": "silver:1", "metadata_path": ""}],
            "produced_artifact_trace": {"complete": False},
            "lineage_closure_boundary": {"supported": False},
        },
    )

    assert _missing_evidence(result) == (
        "run_ledger_entries_missing",
        "published_artifacts_missing",
        "artifact_links_incomplete",
        "metadata_sidecars_missing",
        "produced_artifact_trace_incomplete",
        "lineage_closure_boundary_unsupported",
    )
