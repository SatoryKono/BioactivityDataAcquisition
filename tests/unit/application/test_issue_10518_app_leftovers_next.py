"""Stream B APP: leftover checkpoint, loop, evidence, replay, and hash-policy branches."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core._record_processor_span_support import (
    RecordProcessorSpanExecutor,
)
from bioetl.application.core.batch_executor_loop_helpers import (
    append_record_and_update_batch_size,
    create_batch_extraction_loop_state,
    reset_batch_after_flush,
    should_flush_batch,
)
from bioetl.application.core.lifecycle.checkpoint_load_validation import (
    _handle_missing_compatibility_context_result,
)
from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointRuntimeParams,
    CheckpointRuntimeService,
)
from bioetl.application.core.record_processor_config import (
    ContentHashPolicyGroup,
    ContentHashVersionPolicy,
)
from bioetl.application.observability.control_plane_evidence.lineage_identity import (
    _edge_anchor_gaps,
    _fragment_anchor_gaps,
    _special_node_gap,
)
from bioetl.application.observability.control_plane_evidence.service import (
    ControlPlaneEvidenceService,
)
from bioetl.application.observability.control_plane_evidence.service_support import (
    EvidenceScopeContext,
)
from bioetl.application.services.control_plane.manifest.replay_taxonomy import (
    _copy_projection_value,
    _has_missing_anchors,
    resolve_replay_next_action,
)
from bioetl.application.services.control_plane.replay import closure_claims as claims
from bioetl.application.services.control_plane.replay.historical_closure_models import (
    HistoricalReplayResidualDispositionRecord,
)
from bioetl.application.services.control_plane.replay.historical_closure_policy import (
    resolve_closure_verdict,
    validate_residual_dispositions,
)
from bioetl.application.services.ops.error_handler import _legacy_increment_kwargs
from bioetl.domain.lineage.refs import LineageNodeType
from bioetl.domain.medallion import LoadingStrategy

pytestmark = pytest.mark.unit


def _scope(*, manifest: object | None = None) -> EvidenceScopeContext:
    return EvidenceScopeContext(
        requested_pipeline="chembl_activity",
        selected_run_id=None,
        selected_run_types=(),
        resolved_via="pipeline_scope",
        manifest=manifest,  # type: ignore[arg-type]
    )


def test_hash_policy_group_rejects_and_active_lookup() -> None:
    policy = ContentHashVersionPolicy(version="1.0.0")
    group = ContentHashPolicyGroup(active_version="1.0.0", policies=(policy,))
    assert group.active_policy is policy
    assert group.for_version("missing") is None
    with pytest.raises(ValueError, match="cannot be empty"):
        ContentHashPolicyGroup(active_version="  ", policies=(policy,))
    with pytest.raises(ValueError, match="unique"):
        ContentHashPolicyGroup(
            active_version="1.0.0",
            policies=(policy, ContentHashVersionPolicy(version="1.0.0")),
        )
    with pytest.raises(ValueError, match="present"):
        ContentHashPolicyGroup(
            active_version="9.0.0",
            policies=(policy,),
        )


def test_batch_loop_helpers_append_flush_and_reset() -> None:
    state = create_batch_extraction_loop_state(batch_size=2, check_interval=1)
    memory = SimpleNamespace(
        check_pressure=lambda *_a, **_k: 2,
        maybe_recover=lambda size: size,
    )
    append_record_and_update_batch_size(
        loop_state=state,
        raw_record={"id": 1},  # type: ignore[arg-type]
        memory_manager=memory,  # type: ignore[arg-type]
        records_fetched=1,
    )
    assert should_flush_batch(state) is False
    append_record_and_update_batch_size(
        loop_state=state,
        raw_record={"id": 2},  # type: ignore[arg-type]
        memory_manager=memory,  # type: ignore[arg-type]
        records_fetched=2,
    )
    assert should_flush_batch(state) is True
    reset_batch_after_flush(loop_state=state, memory_manager=memory)  # type: ignore[arg-type]
    assert state.batch == []


@pytest.mark.asyncio
async def test_checkpoint_runtime_load_paths_and_strategy_block() -> None:
    blocked = CheckpointRuntimeService(
        AsyncMock(),
        MagicMock(),
        CheckpointRuntimeParams(
            pipeline_name="chembl_activity",
            run_id="r1",
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        ),
    )
    assert blocked._resume_blocked_by_loading_strategy() is True
    assert blocked.current_metadata is None

    port = AsyncMock()
    port.load_for_manifest_id = AsyncMock(return_value=("r1", {"k": 1}))
    port.load_for_run = AsyncMock(return_value=("r2", {"k": 2}))
    port.load = AsyncMock(return_value=("r3", {"k": 3}))
    metrics = MagicMock()
    by_manifest = CheckpointRuntimeService(
        port,
        MagicMock(),
        CheckpointRuntimeParams(
            pipeline_name="chembl_activity",
            run_id="r1",
            resume=True,
            resume_manifest_id="m1",
        ),
        metrics=metrics,
    )
    assert await by_manifest._load_checkpoint_data() == ("r1", {"k": 1})

    by_run = CheckpointRuntimeService(
        port,
        MagicMock(),
        CheckpointRuntimeParams(
            pipeline_name="chembl_activity",
            run_id="r1",
            resume=True,
            resume_run_id="r2",
        ),
    )
    assert await by_run._load_checkpoint_data() == ("r2", {"k": 2})

    by_name = CheckpointRuntimeService(
        port,
        MagicMock(),
        CheckpointRuntimeParams(
            pipeline_name="chembl_activity",
            run_id="r1",
            resume=True,
        ),
    )
    assert await by_name._load_checkpoint_data() == ("r3", {"k": 3})

    port.load = AsyncMock(side_effect=ValueError("missing"))
    failing = CheckpointRuntimeService(
        port,
        MagicMock(),
        CheckpointRuntimeParams(
            pipeline_name="chembl_activity",
            run_id="r1",
            resume=True,
        ),
        metrics=metrics,
    )
    with pytest.raises(ValueError, match="missing"):
        await failing._load_checkpoint_data()
    metrics.increment_counter.assert_called()


def test_checkpoint_missing_compatibility_context_none_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[str] = []
    monkeypatch.setattr(
        "bioetl.application.core.lifecycle.checkpoint_load_validation.handle_missing_compatibility_context",
        lambda **_k: None,
    )
    result = _handle_missing_compatibility_context_result(
        logger=MagicMock(),
        pipeline_name="chembl_activity",
        compatibility_policy="soft_fail",
        checkpoint_metadata=MagicMock(),
        current_metadata=None,
        service_available=False,
        operation_errors=(ValueError,),
        emit_checkpoint_load_status=emitted.append,
    )
    assert result is None
    assert emitted == ["missing_compatibility_context"]


def test_evidence_service_unresolved_and_trust_row_gaps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    svc = ControlPlaneEvidenceService()
    now = datetime(2026, 1, 1, tzinfo=UTC)
    unresolved = _scope()
    lineage = svc.lineage_validation(scope=unresolved)
    assert lineage["endpoint"] == "lineage-validation"
    retention = svc.retention_compliance(scope=unresolved, now=now)
    assert retention["endpoint"] == "retention-compliance"

    monkeypatch.setattr(
        ControlPlaneEvidenceService,
        "manifest_validation",
        lambda self, *, scope: {"endpoint": "m", "rows": []},
    )
    monkeypatch.setattr(
        ControlPlaneEvidenceService,
        "lineage_validation",
        lambda self, *, scope: {"endpoint": "l", "rows": ["skip"]},
    )
    monkeypatch.setattr(
        ControlPlaneEvidenceService,
        "retention_compliance",
        lambda self, *, scope, now: {
            "endpoint": "r",
            "rows": [{"status": "weird", "check": "c", "reason": "ok", "detail": ""}],
        },
    )
    summary = svc.trust_summary(scope=unresolved, now=now)
    assert summary["endpoint"] == "trust-summary"

    planner = SimpleNamespace(
        plan=lambda *_a, **_k: SimpleNamespace(cutoff=now, artifacts=())
    )
    hosted = ControlPlaneEvidenceService(lifecycle_planner=planner)  # type: ignore[arg-type]
    hosted._bounded_retention_plan(SimpleNamespace(), now)  # type: ignore[arg-type]


def test_replay_taxonomy_and_closure_claim_reasons() -> None:
    assert "degraded" in resolve_replay_next_action("resume_only_degraded").lower()
    assert _has_missing_anchors({"a": 1}) is True
    assert _has_missing_anchors("  ") is False
    assert _has_missing_anchors(["x"]) is True
    assert _copy_projection_value("not_a_list_field", {"k": 1}) == {"k": 1}
    assert claims._record_manifest_id("plain") is None
    blockers = claims.build_narrowed_scope_global_claim(
        unresolved_records=(),
        narrowed_scope_blockers=("m1",),
    )
    assert (
        blockers["reason"]
        == "retained_certifiable_scope_still_contains_in_scope_blockers"
    )
    reason = claims.universal_scope_claim_block_reason(
        unresolved_records=(),
        has_irrecoverable=False,
        unsupported_count=2,
    )
    assert reason == "some_retained_runs_remain_outside_supported_historical_scope"
    disposition = HistoricalReplayResidualDispositionRecord(
        manifest_id="m1",
        disposition="manual_review_required",
        rationale="review",
    )
    blocked = SimpleNamespace(manifest_id="m1")
    with pytest.raises(ValueError, match="Duplicate"):
        validate_residual_dispositions(
            blocked_records=(blocked,),  # type: ignore[arg-type]
            residual_dispositions=(disposition, disposition),
        )
    inventory = SimpleNamespace(
        manifest_count=2,
        certified_count=0,
        replayable_count=0,
        unsupported_count=2,
        remaining_uncertified_count=2,
    )
    verdict, _reason = resolve_closure_verdict(
        inventory=inventory,  # type: ignore[arg-type]
        unresolved_records=(),
        disposition_map={},
        claim_scope_mode="all_retained_historical_runs",
    )
    assert verdict == "outside_supported_scope_present"


def test_lineage_identity_anchor_gaps() -> None:
    fragment = SimpleNamespace(
        stored_fragment_id=None,
        fragment_id="f1",
        run_id="other",
        manifest_id="other",
    )
    gaps = _fragment_anchor_gaps(fragment, "run-1", "man-1")  # type: ignore[arg-type]
    assert "fragment_run:f1" in gaps
    assert "fragment_manifest:f1" in gaps
    edge = SimpleNamespace(
        run_id="x",
        manifest_id="y",
        source=SimpleNamespace(node_id="n1"),
    )
    edge_gaps = _edge_anchor_gaps(edge, "run-1", "man-1")  # type: ignore[arg-type]
    assert "edge_run:n1" in edge_gaps
    assert "edge_manifest:n1" in edge_gaps
    node = SimpleNamespace(
        node_type=LineageNodeType.RUN,
        node_id="run:bad",
        attributes={},
    )
    assert _special_node_gap(node, "run-1", "man-1") == "run_node:run:bad"  # type: ignore[arg-type]


def test_legacy_increment_kwargs_signature_failure() -> None:
    assert _legacy_increment_kwargs(object(), 1, {"k": "v"}) == {}  # type: ignore[arg-type]

    def _increment(*, value: float, tags: dict[str, str] | None = None) -> None:
        del value, tags

    kwargs = _legacy_increment_kwargs(_increment, 3, {"job": "bioetl"})
    assert kwargs["value"] == 3.0
    assert kwargs["tags"] == {"job": "bioetl"}


@pytest.mark.asyncio
async def test_record_processor_span_operation_error() -> None:
    executor = RecordProcessorSpanExecutor(tracer=None)  # type: ignore[arg-type]
    seen: list[str] = []

    async def _boom() -> object:
        raise ValueError("span-fail")

    with pytest.raises(ValueError, match="span-fail"):
        await executor.execute_with_span(
            "stage",
            _boom(),
            "batch-1",  # type: ignore[arg-type]
            1,
            on_error=lambda exc: seen.append(type(exc).__name__),
        )
    assert seen == ["ValueError"]
