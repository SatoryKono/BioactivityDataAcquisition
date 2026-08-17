# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
"""Focused fail-closed regressions for #8916 / #8918."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.join_execution import JoinExecutorService
from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_runtime_helpers import (
    run_with_managed_lock,
)
from bioetl.application.composite.runner_pkg.runner_stage_state_flow import (
    find_required_failures,
)
from bioetl.application.workflow.transforms.reconcile_foreign_keys import (
    _optional_key_tuple,
    _required_primary_keys,
)
from bioetl.domain.composite.result import DependencyResult, DependencyStatus, DependencyStatus
from bioetl.domain.control_plane._run_ledger_runtime import RunLedgerEntry
from bioetl.domain.control_plane._run_manifest_deserialization import (
    _load_artifacts,
    _load_source_refs,
)
from bioetl.domain.control_plane.run_ledger_replay import (
    RunLedgerReplayProjection,
    _mark_projection_unsupported,
)
from bioetl.infrastructure.schemas.workflow_config_fk import (
    _normalize_fk_required_names,
    _require_fk_key_pairs_present,
)
from bioetl.infrastructure.storage.support.retention_time_travel import (
    load_time_travel_table,
)

pytestmark = pytest.mark.unit


def test_join_key_strips_literal_dot_zero_after_string_cast() -> None:
    host = JoinExecutorService(logger=MagicMock(), join_type_resolver=lambda: "inner")
    left_df = pl.DataFrame({"id": [1], "payload": ["left"]})
    right_df = pl.DataFrame({"id": [1.0], "extra": ["right"]})

    result = host.execute_polars_join(
        left_df=left_df,
        right_df=right_df,
        left_key="id",
        right_key="id",
        pipeline_name="assay",
    )

    assert result.height == 1
    assert result["extra"][0] == "right"


def test_empty_composite_fk_keys_fail_closed() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        _normalize_fk_required_names([], "source_keys")
    with pytest.raises(ValueError, match="source_key/reference_key"):
        _require_fk_key_pairs_present(
            source_key=None,
            reference_key=None,
            source_keys=[],
            reference_keys=[],
        )


def test_blank_fk_keys_fail_closed_at_index() -> None:
    with pytest.raises(ValueError, match="blank entries"):
        _required_primary_keys({"primary_keys": ["target_id", ""]})
    with pytest.raises(ValueError, match="blank entries"):
        _optional_key_tuple({"source_keys": ["assay_id", " "]}, "source_keys")


def test_non_dict_manifest_entries_fail_closed() -> None:
    with pytest.raises(ValueError, match="source_refs\\[0\\] must be an object"):
        _load_source_refs(
            ["not-a-dict"],
            source_ref_type=lambda **kwargs: kwargs,
            snapshot_ref_type=lambda **kwargs: kwargs,
        )
    with pytest.raises(ValueError, match="artifacts\\[1\\] must be an object"):
        _load_artifacts(
            [{"layer": "silver", "path": "a.parquet"}, "bad"],
            artifact_type=lambda **kwargs: kwargs,
        )


def test_unsupported_replay_entries_sort_mixed_stage() -> None:
    projection = RunLedgerReplayProjection()
    first = RunLedgerEntry(
        entry_id="e1",
        manifest_id="m1",
        run_id="run-1",
        event_type="stage_completed",
        stage=None,
        occurred_at=datetime(2026, 8, 17, tzinfo=UTC),
    )
    second = RunLedgerEntry(
        entry_id="e1",
        manifest_id="m1",
        run_id="run-1",
        event_type="stage_completed",
        stage="postrun",
        occurred_at=datetime(2026, 8, 17, tzinfo=UTC),
    )
    marked = _mark_projection_unsupported(projection, first)
    marked = _mark_projection_unsupported(marked, second)
    assert marked.unsupported_replay_entries == (
        ("e1", "stage_completed", None),
        ("e1", "stage_completed", "postrun"),
    )


def test_terminal_metrics_use_warning_status() -> None:
    metrics = MagicMock()
    observer = CompositeLifecycleObserverService(logger=MagicMock(), metrics=metrics)
    observer.emit_run_completed(
        composite_name="demo",
        run_id="run-1",
        duration_seconds=1.0,
        had_warnings=True,
    )
    increment_labels = [
        call.kwargs.get("labels") or call.args[2]
        for call in metrics.increment_counter.call_args_list
        if call.args and call.args[0] == "bioetl_pipeline_runs_total"
    ]
    assert increment_labels
    assert any(
        labels.get("status") == "completed_with_warnings"
        for labels in increment_labels
        if isinstance(labels, dict)
    )


def test_missing_dependency_config_is_required_failure() -> None:
    host = SimpleNamespace(_config=SimpleNamespace(get_dependency=lambda _name: None))
    failed = find_required_failures(
        host,
        {
            "missing": DependencyResult(
                pipeline_name="missing",
                status=DependencyStatus.FAILED,
            )
        },
    )
    assert failed == ["missing"]


@pytest.mark.asyncio
async def test_heartbeat_stop_exception_still_releases_lock() -> None:
    lock_port = SimpleNamespace(
        acquire=AsyncMock(return_value=True),
        release=AsyncMock(),
    )
    heartbeat = SimpleNamespace(
        start=AsyncMock(),
        stop=AsyncMock(side_effect=RuntimeError("stop failed")),
    )

    def factory(**_kwargs: object) -> SimpleNamespace:
        return SimpleNamespace(heartbeat=heartbeat)

    with pytest.raises(RuntimeError, match="stop failed"):
        await run_with_managed_lock(
            lock_port=lock_port,
            lock_key="k",
            owner_id="o",
            lock_ttl_seconds=1,
            heartbeat_interval_seconds=1,
            logger=MagicMock(),
            run_while_locked=AsyncMock(return_value="ok"),
            lock_context_factory=factory,
        )

    lock_port.release.assert_awaited_once()


@pytest.mark.asyncio
async def test_time_travel_missing_timestamp_raises_value_error() -> None:
    with pytest.raises(ValueError, match="Must specify either version or timestamp"):
        await load_time_travel_table(base_path="/tmp", table_name="demo")
