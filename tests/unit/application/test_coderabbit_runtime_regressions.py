"""Behavioral regressions for CodeRabbit issues 10572-10576."""

from __future__ import annotations

import asyncio
import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID
from weakref import ref

import pytest

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.core.batch_processing_support import (
    BatchProcessingSupportService,
)
from bioetl.application.observability import current_metrics_rehydrate as rehydrate
from bioetl.application.observability.control_plane_evidence.lineage_graph_validation import (
    cycle_nodes,
)
from bioetl.application.observability.rehydrate_models import (
    PipelineRunSnapshot,
    WorkflowRunSnapshot,
    WorkflowPipelineScopeInfo,
)
from bioetl.domain.composite import ColumnGroupConfig, LayerColumnConfig
from bioetl.domain.lineage import (
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
    LineageEdge,
    LineageEdgeType,
)
from tests.unit.application.composite.runner_pkg.test_runner_support_mixin import (
    _SupportMixinHarness,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("mode", ["explicit", "groups", "fallback", "missing_groups"])
@pytest.mark.parametrize("renames", [{"a": "b", "b": "c"}, {"a": "b", "b": "a"}])
def test_layer_rename_applies_once(mode, renames):
    groups = (
        [ColumnGroupConfig(name="core", fields=["a", "b"])]
        if mode == "groups"
        else None
    )
    orderer = ColumnOrderService(MagicMock(), column_groups=groups)
    config = LayerColumnConfig(
        columns=["a", "b"] if mode == "explicit" else None,
        include_groups=["core"] if mode in {"groups", "missing_groups"} else None,
        rename_fields=renames,
    )
    assert orderer.filter_by_layer_config(["a", "b"], config) == [
        renames["a"],
        renames["b"],
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cleanup_failure", [None, "set_attribute", "__exit__", "flush"]
)
@pytest.mark.parametrize("error_type", [RuntimeError, asyncio.CancelledError])
async def test_checkpoint_span_closes_on_propagated_error(error_type, cleanup_failure):
    host = _SupportMixinHarness()
    error = error_type("checkpoint interrupted")
    host._checkpoint_manager.save.side_effect = error
    if cleanup_failure is not None:
        target = host._tracing if cleanup_failure == "flush" else host._checkpoint_span
        getattr(target, cleanup_failure).side_effect = ValueError("cleanup unavailable")
    with pytest.raises(error_type) as caught:
        await host._save_checkpoint_safe(MagicMock(), "regression")
    assert caught.value is error
    host._checkpoint_span.__exit__.assert_called_once()
    host._tracing.flush.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["failure", "success", "no_emitter", "no_run_id"])
async def test_bronze_emitter_failure_is_observable_and_nonfatal(mode):
    logger, emitter, writer = MagicMock(), MagicMock(), MagicMock()
    writer.write_bronze = AsyncMock(return_value="written")
    if mode == "failure":
        emitter.emit_domain_event.side_effect = RuntimeError("bus unavailable")
    support = BatchProcessingSupportService(
        services=MagicMock(),
        logger=logger,
        batch_metrics=MagicMock(),
        transformer=MagicMock(),
        writer=writer,
        tracing=MagicMock(),
        quarantine_manager=MagicMock(),
        run_id=None if mode == "no_run_id" else UUID(int=1),
        domain_event_emitter=None if mode == "no_emitter" else emitter,
    )
    assert (
        await support.write_bronze_layer(
            records=[{"id": "audit"}],
            batch_id=UUID(int=2),
            start_index=0,
            ingestion_ts=datetime(2026, 1, 1, tzinfo=UTC),
            source_metadata=None,
        )
        == "written"
    )
    if mode == "failure":
        logger.warning.assert_called_once_with(
            "domain_event_emit_failed",
            error="bus unavailable",
            error_type="RuntimeError",
            event_type="BatchWritten",
        )
    else:
        logger.warning.assert_not_called()
    if mode in {"no_emitter", "no_run_id"}:
        emitter.emit_domain_event.assert_not_called()


def _graph(edges):
    nodes = {
        i: LineageNodeRef(LineageNodeType.DATASET, f"node-{i:04d}")
        for edge in edges
        for i in edge
    }
    return LineageGraphFragment(
        "regression",
        nodes=tuple(nodes.values()),
        edges=tuple(
            LineageEdge(LineageEdgeType.DERIVED_FROM, nodes[a], nodes[b])
            for a, b in edges
        ),
    )


def test_lineage_chain_exceeds_recursion_depth():
    assert cycle_nodes((_graph([(i, i + 1) for i in range(1500)]),)) == []


@pytest.mark.parametrize(
    "edges, expected",
    [
        ([], []),
        ([(0, 0)], ["node-0000"]),
        ([(0, 1), (1, 0), (2, 3), (3, 4)], ["node-0000", "node-0001"]),
        ([(0, 1), (0, 2), (1, 3), (2, 3)], []),
    ],
)
def test_lineage_cycle_semantics(edges, expected):
    assert cycle_nodes((_graph(edges),)) == expected
    assert cycle_nodes((_graph(list(reversed(edges))),)) == expected


def test_rehydrate_new_metrics_instance_seeds_all_families(monkeypatch):
    rehydrate.reset_rehydrate_seed_state()
    pipeline = PipelineRunSnapshot(
        "pipeline", "incremental", "success", "provider", "r", 100
    )
    workflow = WorkflowRunSnapshot(
        "workflow",
        "success",
        "provider",
        "w",
        (WorkflowPipelineScopeInfo("pipeline", "incremental", "provider"),),
    )
    monkeypatch.setattr(
        rehydrate, "collect_latest_terminal_anchors", lambda **kw: (pipeline,)
    )
    monkeypatch.setattr(
        rehydrate, "collect_latest_terminal_workflow_anchors", lambda **kw: (workflow,)
    )
    first, second = MagicMock(), MagicMock()
    for metrics in (first, second):
        result = rehydrate.rehydrate_current_pipeline_run_metrics(
            metrics, store=MagicMock()
        )
        assert (
            result.pipeline_runs_seeded,
            result.provider_universe_seeded,
            result.workflow_expected_seeded,
            result.workflow_pipeline_expected_seeded,
        ) == (1, 1, 1, 1)
        metrics.increment_counter.assert_called_once_with(
            "bioetl_pipeline_runs_total",
            0,
            {"pipeline": "pipeline", "run_type": "incremental", "status": "success"},
        )
        calls = list(metrics.mock_calls)
        again = rehydrate.rehydrate_current_pipeline_run_metrics(
            metrics, store=MagicMock()
        )
        assert again.pipeline_runs_seeded == again.provider_universe_seeded == 0
        assert (
            again.workflow_expected_seeded
            == again.workflow_pipeline_expected_seeded
            == 0
        )
        assert metrics.mock_calls == calls
    rehydrate.reset_rehydrate_seed_state()
    assert (
        rehydrate.rehydrate_current_pipeline_run_metrics(
            second, store=MagicMock()
        ).pipeline_runs_seeded
        == 1
    )


def test_rehydrate_does_not_retain_metrics_instances():
    rehydrate.reset_rehydrate_seed_state()
    metrics = MagicMock()
    reference = ref(metrics)
    anchor = PipelineRunSnapshot("p", "incremental", "success", "provider", "r", 100)
    rehydrate._seed_pipeline_runs_total(metrics, anchor)
    del metrics
    gc.collect()
    assert reference() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("cleanup_fails", [False, True])
async def test_checkpoint_does_not_capture_callers_exception(cleanup_fails):
    host = _SupportMixinHarness()
    if cleanup_fails:
        host._tracing.flush.side_effect = RuntimeError("cleanup failed")
    try:
        raise ValueError("caller fallback")
    except ValueError:
        assert await host._save_checkpoint_safe(MagicMock(), "fallback") is True
    if cleanup_fails:
        assert host._logger.warning.call_args.args == (
            "checkpoint_span_cleanup_failed",
        )
    host._checkpoint_span.record_exception.assert_not_called()
    host._checkpoint_span.__exit__.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("save_fails", [False, True])
@pytest.mark.parametrize("cleanup_failure", ["__exit__", "flush"])
async def test_checkpoint_cleanup_preserves_graceful_result(
    save_fails, cleanup_failure
):
    host = _SupportMixinHarness()
    if save_fails:
        host._checkpoint_manager.save.side_effect = OSError("save unavailable")
    target = host._tracing if cleanup_failure == "flush" else host._checkpoint_span
    getattr(target, cleanup_failure).side_effect = ValueError("cleanup unavailable")
    assert await host._save_checkpoint_safe(MagicMock(), "regression") is not save_fails
    host._checkpoint_span.__exit__.assert_called_once()
    host._tracing.flush.assert_called_once()
    assert host._logger.warning.call_args.args == ("checkpoint_span_cleanup_failed",)


class _PresenceMetrics:
    __slots__ = ("counter_values",)

    def __init__(self):
        self.counter_values = []

    def set_gauge(self, name, value, labels):
        pass

    def increment_counter(self, name, value, labels):
        self.counter_values.append(value)


class _EqualPresenceMetrics(_PresenceMetrics):
    __slots__ = ("__weakref__",)
    __hash__ = None

    def __eq__(self, other):
        return isinstance(other, _EqualPresenceMetrics)


def test_equal_unhashable_metrics_instances_seed_independently():
    rehydrate.reset_rehydrate_seed_state()
    anchor = PipelineRunSnapshot("p", "incremental", "success", "provider", "r", 100)
    first, second = _EqualPresenceMetrics(), _EqualPresenceMetrics()
    for metrics in (first, second):
        assert rehydrate._seed_pipeline_runs_total(metrics, anchor) == 1
        assert rehydrate._seed_pipeline_runs_total(metrics, anchor) == 0
        assert metrics.counter_values == [0]


def test_nonweakrefable_metrics_repeats_only_presence_writes():
    rehydrate.reset_rehydrate_seed_state()
    metrics = _PresenceMetrics()
    anchor = PipelineRunSnapshot("p", "incremental", "success", "provider", "r", 100)
    assert rehydrate._seed_pipeline_runs_total(metrics, anchor) == 1
    assert rehydrate._seed_pipeline_runs_total(metrics, anchor) == 1
    assert metrics.counter_values == [0, 0]
