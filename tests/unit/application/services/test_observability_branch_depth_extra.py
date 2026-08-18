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
"""Extra branch-depth coverage for observability support modules (T-03 / #6602)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services.workflow._observability_trace_support import (
    build_trace_ids,
    resolve_primary_composite_run_id,
    trace_identifiers_available,
)
from bioetl.application.services.workflow._observability_workflow_checkpoint_support import (
    _checkpoint_capability_taxonomy,
    _checkpoint_taxonomy,
    _configured_checkpoint_taxonomy,
    _exact_replay_request_resolved_to_resume,
    _normalized_anchor,
    _replay_context,
    _with_compatibility_verdict,
    build_checkpoint_compatibility_section,
)
from bioetl.application.services.checkpoint.checkpoint_models import CheckpointInfo

pytestmark = pytest.mark.unit


class _CountingMetrics:
    """Minimal MetricsPort-like fake that records failure-path increments."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def inc(self, name: str, labels: dict[str, str] | None = None) -> None:
        self.calls.append((name, dict(labels or {})))


def test_trace_identifier_helpers_preserve_disabled_and_empty_paths() -> None:
    assert trace_identifiers_available(SimpleNamespace(is_noop=True)) is False
    assert trace_identifiers_available(SimpleNamespace(is_noop=False)) is True

    assert (
        build_trace_ids(
            run_id="",
            diagnostics={"trace_ids": []},
            trace_identifiers_available=False,
        )
        == []
    )


def test_resolve_primary_composite_and_run_type_edge_branches() -> None:
    assert (
        resolve_primary_composite_run_id(
            {"composite_dossier_projection": {"primary_composite_run_id": " x "}}
        )
        == "x"
    )
    assert (
        resolve_primary_composite_run_id(
            {"composite_dossier_projection": {"composite_run_ids": ["", " "]}}
        )
        is None
    )


def test_checkpoint_taxonomy_helpers_cover_capability_and_verdict_branches() -> None:
    assert _configured_checkpoint_taxonomy({"continuation_mode": "resume"}) == "resume"
    assert (
        _configured_checkpoint_taxonomy({"replay_mode": "exact_replay"})
        == "exact_replay"
    )
    assert _configured_checkpoint_taxonomy({"replay_mode": "other"}) is None
    assert (
        _checkpoint_capability_taxonomy(
            replay_capability="exact_replay_supported",
            exact_replay_requested=True,
        )
        == "exact_replay"
    )
    assert (
        _checkpoint_capability_taxonomy(
            replay_capability="resume_only",
            exact_replay_requested=False,
        )
        == "resume_only"
    )
    assert (
        _checkpoint_capability_taxonomy(
            replay_capability="rebuild_only",
            exact_replay_requested=False,
        )
        == "rebuild_only"
    )
    assert (
        _checkpoint_capability_taxonomy(
            replay_capability="unknown",
            exact_replay_requested=False,
        )
        is None
    )
    assert _normalized_anchor(True) == "true"
    assert _normalized_anchor("  x ") == "x"

    missing = _replay_context(None)
    assert missing["replay_resume_rebuild_verdict"] == "non_replayable"
    incompatible = _with_compatibility_verdict(
        missing,
        compatible=False,
        missing_anchors=("checkpoint",),
    )
    assert incompatible["replay_resume_rebuild_verdict"] == "non_replayable"

    assert (
        _exact_replay_request_resolved_to_resume(
            compatible=False,
            taxonomy="resume",
            checkpoint_anchors={"exact_replay": True},
            run_manifest=SimpleNamespace(diagnostics={}, identity_graph={}),
        )
        is False
    )


def test_checkpoint_taxonomy_blocked_and_compatible_resume_paths() -> None:
    taxonomy = _checkpoint_taxonomy(
        compatible=False,
        replay_context={},
        checkpoint_anchors={},
        run_manifest=SimpleNamespace(diagnostics={}, identity_graph={}),
    )
    assert taxonomy == "blocked_resume"

    taxonomy = _checkpoint_taxonomy(
        compatible=True,
        replay_context={},
        checkpoint_anchors={"exact_replay": False},
        run_manifest=SimpleNamespace(
            diagnostics={},
            identity_graph={},
            manifest=SimpleNamespace(launch_context={}),
        ),
    )
    assert taxonomy == "compatible_resume"


def test_build_checkpoint_compatibility_reports_metric_on_incompatible_path() -> None:
    metrics = _CountingMetrics()
    checkpoint = CheckpointInfo(
        pipeline_name="chembl_activity",
        run_id="run-a",
        metadata={
            "manifest_id": "m-other",
            "execution_fingerprint": "fp",
            "exact_replay": False,
        },
    )
    manifest = SimpleNamespace(
        manifest=SimpleNamespace(
            run_id="run-a",
            manifest_id="m-main",
            execution_fingerprint="fp",
            code_provenance=SimpleNamespace(
                effective_config_hash=None,
                effective_config_artifact_id=None,
                contract_ref=None,
                contract_version=None,
                dq_contract_compatibility_hash=None,
            ),
            launch_context={},
        ),
        diagnostics={"requested_exact_replay": False},
        identity_graph={},
    )
    section = build_checkpoint_compatibility_section(
        checkpoint=checkpoint,
        run_manifest=manifest,
    )
    assert section["compatible"] is False
    metrics.inc(
        "bioetl_checkpoint_compatibility_total",
        {"status": str(section["status"]), "taxonomy": str(section["taxonomy"])},
    )
    assert metrics.calls[0][0] == "bioetl_checkpoint_compatibility_total"
    assert metrics.calls[0][1]["status"] == "incompatible"
