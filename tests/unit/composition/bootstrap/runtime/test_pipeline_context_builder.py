"""Tests for replay-critical pipeline context timestamp wiring."""

from __future__ import annotations

from datetime import UTC, datetime

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
        started_at=started_at,
    )

    assert context.started_at == started_at
    assert context.exact_replay is True
    assert context.cached_bronze.enabled is True


def test_build_pipeline_context_requires_clock_when_started_at_missing() -> None:
    """Implicit system-time fallback must stay forbidden for replay-critical seams."""
    with pytest.raises(RuntimeError, match="ClockPort is required"):
        build_pipeline_context("chembl_activity", RunOptions())
