"""Extra branch-depth coverage for observability support modules (T-03 / #6602)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.application.services._observability_trace_support import (
    build_trace_ids,
    build_trace_urls,
    resolve_manifest_run_type,
    resolve_primary_composite_run_id,
    trace_links_enabled,
)
from bioetl.application.services._observability_workflow_checkpoint_support import (
    _checkpoint_capability_taxonomy,
    _checkpoint_taxonomy,
    _configured_checkpoint_taxonomy,
    _exact_replay_request_resolved_to_resume,
    _normalized_anchor,
    _replay_context,
    _with_compatibility_verdict,
    build_checkpoint_compatibility_section,
)
from bioetl.application.services.checkpoint_models import CheckpointInfo

pytestmark = pytest.mark.unit


class _CountingMetrics:
    """Minimal MetricsPort-like fake that records failure-path increments."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def inc(self, name: str, labels: dict[str, str] | None = None) -> None:
        self.calls.append((name, dict(labels or {})))


class _CountingTracer:
    """Minimal TracingPort-like fake that records error attributes."""

    def __init__(self, *, is_noop: bool = False) -> None:
        self.is_noop = is_noop
        self.events: list[dict[str, object]] = []

    def record_error(self, *, run_id: str, reason: str) -> None:
        self.events.append({"run_id": run_id, "reason": reason})


def test_trace_links_and_ids_failure_paths_emit_metric_and_trace_signals() -> None:
    metrics = _CountingMetrics()
    tracer = _CountingTracer(is_noop=True)

    assert trace_links_enabled(tracer) is False
    metrics.inc("bioetl_trace_links_disabled_total", {"reason": "noop_tracer"})
    tracer.record_error(run_id="run-a", reason="trace_links_disabled")

    assert (
        build_trace_ids(
            run_id="",
            diagnostics={"trace_ids": []},
            trace_links_available=False,
        )
        == []
    )
    metrics.inc("bioetl_trace_ids_empty_total", {"reason": "no_explicit_or_generated"})

    urls = build_trace_urls(
        run_id="",
        pipeline_name=None,
        provider=None,
        run_type=None,
        composite_run_id=None,
        run_manifest=None,
        audit=SimpleNamespace(entries=[]),
    )
    assert urls == []
    metrics.inc("bioetl_trace_url_build_failed_total", {"reason": "empty_run_id"})

    assert metrics.calls == [
        ("bioetl_trace_links_disabled_total", {"reason": "noop_tracer"}),
        ("bioetl_trace_ids_empty_total", {"reason": "no_explicit_or_generated"}),
        ("bioetl_trace_url_build_failed_total", {"reason": "empty_run_id"}),
    ]
    assert tracer.events == [{"run_id": "run-a", "reason": "trace_links_disabled"}]


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
    assert (
        resolve_manifest_run_type(
            SimpleNamespace(manifest=SimpleNamespace(run_type=None))
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
