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
"""Tests for replay-critical pipeline context timestamp wiring."""

from __future__ import annotations

from datetime import UTC, datetime
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.services.execution.pipeline_runner_models import RunOptions
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    build_pipeline_context,
)
from bioetl.domain.types import ExecutionContext, RunType
from tests.helpers.clock import FixedClock


pytestmark = pytest.mark.unit


def test_build_pipeline_context_uses_injected_clock() -> None:
    """Pipeline context creation should accept deterministic ClockPort input."""
    started_at = datetime(2026, 5, 24, 12, 30, tzinfo=UTC)

    context = build_pipeline_context(
        "chembl_activity",
        RunOptions(run_type="backfill", execution_context="enricher"),
        clock=FixedClock(started_at),
    )

    assert context.pipeline_name == "chembl_activity"
    assert context.run_type == RunType.BACKFILL
    assert context.started_at == started_at
    assert context.execution_context == ExecutionContext.ENRICHER


def test_build_pipeline_context_prefers_explicit_started_at_over_clock() -> None:
    """Replay callers may provide a pre-captured timestamp anchor explicitly."""
    explicit_started_at = datetime(2026, 5, 24, 13, 0, tzinfo=UTC)
    clock_started_at = datetime(2026, 5, 24, 12, 30, tzinfo=UTC)

    context = build_pipeline_context(
        "chembl_activity",
        RunOptions(),
        clock=FixedClock(clock_started_at),
        started_at=explicit_started_at,
    )

    assert context.started_at == explicit_started_at


def test_build_pipeline_context_accepts_explicit_started_at_without_clock() -> None:
    """A caller-provided timestamp keeps the seam deterministic without wall-clock reads."""
    started_at = datetime(2026, 5, 24, 13, 30, tzinfo=UTC)

    context = build_pipeline_context(
        "chembl_activity",
        RunOptions(exact_replay=True, use_cached_bronze=True),
        run_id=deterministic_uuid_from_callsite("test_pipeline_context_builder"),
        started_at=started_at,
    )

    assert context.started_at == started_at
    assert context.exact_replay is True
    assert context.cached_bronze.enabled is True


def test_build_pipeline_context_requires_explicit_run_id_for_exact_replay() -> None:
    """Exact replay must not synthesize occurrence IDs implicitly."""
    with pytest.raises(
        ValueError,
        match="exact replay requires explicit run_id or run_id_factory",
    ):
        build_pipeline_context(
            "chembl_activity",
            RunOptions(exact_replay=True, use_cached_bronze=True),
            started_at=datetime(2026, 5, 24, 13, 30, tzinfo=UTC),
        )


def test_build_pipeline_context_accepts_injected_run_id_factory() -> None:
    """Replay callers may inject a deterministic occurrence-ID seam explicitly."""
    expected_run_id = deterministic_uuid_from_callsite("test_pipeline_context_builder")

    context = build_pipeline_context(
        "chembl_activity",
        RunOptions(exact_replay=True, use_cached_bronze=True),
        run_id_factory=lambda: expected_run_id,
        started_at=datetime(2026, 5, 24, 13, 30, tzinfo=UTC),
    )

    assert context.run_id == expected_run_id


def test_build_pipeline_context_propagates_workflow_id() -> None:
    """Workflow-owned runs must carry the workflow anchor into runtime context."""
    context = build_pipeline_context(
        "chembl_activity",
        RunOptions(
            debug_export_enabled=True,
            workflow_id="chembl_baseline",
        ),
        run_id=deterministic_uuid_from_callsite("test_pipeline_context_builder"),
        started_at=datetime(2026, 5, 24, 13, 30, tzinfo=UTC),
    )

    assert context.workflow_id == "chembl_baseline"


def test_build_pipeline_context_requires_clock_when_started_at_missing() -> None:
    """Implicit system-time fallback must stay forbidden for replay-critical seams."""
    with pytest.raises(RuntimeError, match="ClockPort is required"):
        build_pipeline_context("chembl_activity", RunOptions())
