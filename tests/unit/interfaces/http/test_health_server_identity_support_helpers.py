# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Focused branch coverage for identity-table display helper functions."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.control_plane import RunCodeProvenance, RunManifest
from bioetl.domain.types import RunType
from bioetl.interfaces.http import _health_server_identity_support as support
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite


pytestmark = pytest.mark.unit


def _manifest(
    *,
    pipeline_name: str = "chembl_activity",
    provider: str = "chembl",
    runtime_config: dict[str, object] | None = None,
    launch_context: dict[str, object] | None = None,
    resolved_config: dict[str, object] | None = None,
) -> RunManifest:
    return RunManifest(
        manifest_id="manifest-identity-support",
        execution_fingerprint="fingerprint-identity-support",
        schema_version="1.0",
        created_at=datetime(2026, 7, 6, 12, 0, tzinfo=UTC),
        run_id=deterministic_run_uuid_from_callsite("identity-support-helpers"),
        run_type=RunType.INCREMENTAL,
        pipeline_name=pipeline_name,
        provider=provider,
        entity="activity",
        runtime_config=runtime_config or {},
        launch_context=launch_context or {},
        resolved_config=resolved_config or {},
        code_provenance=RunCodeProvenance(git_commit="abc123"),
    )


def test_identity_support_rows_cover_empty_and_composite_manifest_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    composite_manifest = _manifest(
        pipeline_name="composite_activity",
        provider="composite",
        runtime_config={"execution_context": "", "resume": True},
        launch_context={"dry_run": "yes"},
        resolved_config={"use_cached_bronze": False},
    )

    assert support._anchor_values(None) == {}

    monkeypatch.setattr(
        support,
        "_anchor_values",
        lambda _manifest, checkpoint_metadata=None: {
            "run_id": "run-1",
            "manifest_id": "manifest-1",
            "provider_entity": "composite.activity",
            "pipeline_version": "1.0.0",
            "contract_version": "2026.07",
            "git_commit": "abc123",
            "exact_replay_eligible": None,
            "replay_capability": "custom-capability",
            "replay_mode": "custom-mode",
            "checkpoint_anchor_status": "",
            "identity_graph_complete": "complete",
            "composite_run_identity": "composite-1",
        },
    )
    rows = support._build_identity_rows(
        requested_pipeline="composite_activity",
        resolved_manifest=composite_manifest,
        selected_pipelines=("composite_activity",),
        selected_run_id=None,
        checkpoint_metadata=None,
        identity_evidence_summary=None,
    )
    row_values = {row["parameter"]: row["value"] for row in rows}
    assert row_values["Composite Run"] == "composite-1"
    assert row_values["Contract [Schema]"] == "version=2026.07"
    assert row_values["Execution [Type|Context|Git]"] == (
        "incremental | composite | git=abc123"
    )
    assert row_values["Resume|Dry run|Cached Bronze"] == "Yes | Yes | No"
    assert row_values["Identity Health [Gaps]"] == "Complete [0 gaps]"

    monkeypatch.setattr(support, "_anchor_values", lambda *_args, **_kwargs: {})
    unavailable_rows = support._build_identity_rows(
        requested_pipeline="$__all",
        resolved_manifest=None,
        selected_pipelines=(),
        selected_run_id="run-1",
        checkpoint_metadata=None,
        identity_evidence_summary=None,
    )
    assert unavailable_rows[0]["value"] == "run-1"
    assert (
        unavailable_rows[1]["value"] == "select one concrete pipeline or exact run_id"
    )


def test_identity_support_display_helpers_cover_numeric_gap_and_fallback_edges() -> (
    None
):
    manifest = _manifest(
        runtime_config={"execution_context": "manual", "resume": "false"},
        launch_context={"dry_run": False},
        resolved_config={"use_cached_bronze": "true"},
    )

    assert support._execution_summary(None, {}) is None
    assert support._execution_summary(manifest, {}) == "incremental | manual"
    assert support._execution_flags(None) is None
    assert support._replay_summary({}) is None
    assert (
        support._checkpoint_anchor_status(
            {"checkpoint_anchor_status": "FALLBACK"},
            {"checkpoint_anchor_status": ""},
        )
        == "FALLBACK"
    )
    assert (
        support._identity_health(
            {},
            {"identity_gap_count": "bad", "identity_graph_complete": None},
        )
        == "Unknown [0 gaps]"
    )
    assert (
        support._identity_health(
            {},
            {"identity_gap_count": 2.8, "identity_graph_complete": False},
        )
        == "Incomplete [2 gaps]"
    )
    assert (
        support._identity_health(
            {"identity_graph_complete": False, "correlation_anchor_gaps": [1, 2]},
            None,
        )
        == "Incomplete [2 gaps]"
    )
    assert (
        support._identity_health(
            {"identity_graph_complete": None, "correlation_anchor_gaps": "gap"},
            None,
        )
        == "Unknown [0 gaps]"
    )

    assert support._int_or_zero(True) == 0
    assert support._int_or_zero(-1) == 0
    assert support._int_or_zero("bad") == 0
    assert support._payload_value(manifest, "missing") is None
    assert support._yes_no("1") == "Yes"
    assert support._display_eligible("yes") == "Yes"
    assert support._display_eligible("no") == "No"
    assert support._display_capability(None) == "Unknown"
    assert support._display_replay_mode(None) == "Unknown"
    assert support._gap_count({"a": True, "b": [1, 2], "c": {"x": 1}, "d": "yes"}) == 5
    assert support._gap_count({"a": False, "b": ""}) == 0
    assert support._gap_count(("a", "b")) == 2
    assert support._display(" ", unavailable="missing") == "missing"
    assert support._text(" ") is None
