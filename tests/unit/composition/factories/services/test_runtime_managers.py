"""Unit tests for runtime manager assembly helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.core.runner_flow import extract_checkpoint_offset
from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.composition.factories.services.runtime_managers import (
    build_runtime_managers,
)
from bioetl.domain.config import MemoryConfig
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata


def _make_pipeline(*, batch_size: int | None = 50) -> SimpleNamespace:
    """Build a minimal pipeline stub for runtime manager tests."""
    return SimpleNamespace(
        config=SimpleNamespace(batch_size=batch_size),
        services=SimpleNamespace(
            logger=MagicMock(name="logger"),
            metrics=MagicMock(name="metrics"),
            data_source=MagicMock(name="data_source"),
        ),
        context=MagicMock(name="context"),
        pipeline_name="test_pipeline",
        runtime=SimpleNamespace(exact_replay=False),
    )


@pytest.mark.unit
class TestBuildRuntimeManagers:
    """Behavioural tests for runtime manager assembly."""

    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchExecutionRunService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchExecutionLifecycleService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchCheckpointRecoveryService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchProgressService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchTracingManagerService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchMemoryManagerService"
    )
    @patch("bioetl.composition.factories.services.runtime_managers.resolve_tracer")
    def test_uses_pipeline_batch_size_and_injected_batch_id_factory(
        self,
        mock_resolve_tracer: MagicMock,
        mock_memory_manager_cls: MagicMock,
        mock_tracing_manager_cls: MagicMock,
        mock_progress_cls: MagicMock,
        mock_checkpoint_recovery_cls: MagicMock,
        mock_lifecycle_cls: MagicMock,
        mock_run_service_cls: MagicMock,
    ) -> None:
        """Assembly should honor explicit pipeline/runtime injections."""
        pipeline = _make_pipeline(batch_size=77)
        processor_config = MagicMock(name="processor_config")
        checkpoint_manager = MagicMock(name="checkpoint_manager")
        memory_monitor = MagicMock(name="memory_monitor")
        memory_config = MagicMock(name="memory_config")
        tracer = MagicMock(name="tracer")
        resolved_tracer = MagicMock(name="resolved_tracer")
        batch_id_factory = MagicMock(name="batch_id_factory")
        mock_resolve_tracer.return_value = resolved_tracer

        memory_manager = MagicMock(name="memory_manager")
        memory_manager.enabled = True
        mock_memory_manager_cls.return_value = memory_manager
        tracing_manager = MagicMock(name="tracing_manager")
        progress_service = MagicMock(name="progress_service")
        checkpoint_recovery = MagicMock(name="checkpoint_recovery")
        lifecycle = MagicMock(name="lifecycle")
        execution_run = MagicMock(name="execution_run")
        mock_tracing_manager_cls.return_value = tracing_manager
        mock_progress_cls.return_value = progress_service
        mock_checkpoint_recovery_cls.return_value = checkpoint_recovery
        mock_lifecycle_cls.return_value = lifecycle
        mock_run_service_cls.return_value = execution_run

        result = build_runtime_managers(
            pipeline=pipeline,
            processor_config=processor_config,
            checkpoint_manager=checkpoint_manager,
            memory_monitor=memory_monitor,
            memory_config=memory_config,
            tracer=tracer,
            batch_id_factory=batch_id_factory,
        )

        assert result == (
            memory_manager,
            tracing_manager,
            batch_id_factory,
            progress_service,
            checkpoint_recovery,
            execution_run,
        )
        mock_memory_manager_cls.assert_called_once_with(
            initial_batch_size=77,
            memory_monitor=memory_monitor,
            memory_config=memory_config,
            logger=pipeline.services.logger,
            metrics=pipeline.services.metrics,
            pipeline_name="test_pipeline",
        )
        mock_checkpoint_recovery_cls.assert_called_once_with(
            checkpoint_manager=checkpoint_manager,
            logger=pipeline.services.logger,
            metrics=pipeline.services.metrics,
            tracer=resolved_tracer,
            pipeline_name="test_pipeline",
            memory_manager=memory_manager,
        )
        mock_resolve_tracer.assert_called_once_with(tracer)
        mock_tracing_manager_cls.assert_called_once_with(
            tracer=resolved_tracer,
            context=pipeline.context,
            config=processor_config,
            initial_batch_size=77,
            adaptive_sizing_enabled=True,
        )

    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchExecutionRunService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchExecutionLifecycleService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchCheckpointRecoveryService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchProgressService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchTracingManagerService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchMemoryManagerService"
    )
    @patch("bioetl.composition.factories.services.runtime_managers.resolve_tracer")
    def test_exact_replay_disables_adaptive_memory_sizing(
        self,
        mock_resolve_tracer: MagicMock,
        mock_memory_manager_cls: MagicMock,
        mock_tracing_manager_cls: MagicMock,
        mock_progress_cls: MagicMock,
        mock_checkpoint_recovery_cls: MagicMock,
        mock_lifecycle_cls: MagicMock,
        mock_run_service_cls: MagicMock,
    ) -> None:
        """Exact replay uses fixed batch shape instead of host-memory adaptation."""
        pipeline = _make_pipeline(batch_size=77)
        pipeline.runtime.exact_replay = True
        processor_config = MagicMock(name="processor_config")
        checkpoint_manager = MagicMock(name="checkpoint_manager")
        memory_monitor = MagicMock(name="memory_monitor")
        memory_config = MemoryConfig(enable_adaptive_sizing=True)
        resolved_tracer = MagicMock(name="resolved_tracer")
        mock_resolve_tracer.return_value = resolved_tracer

        memory_manager = MagicMock(name="memory_manager")
        memory_manager.enabled = False
        mock_memory_manager_cls.return_value = memory_manager
        mock_tracing_manager_cls.return_value = MagicMock(name="tracing_manager")
        mock_progress_cls.return_value = MagicMock(name="progress_service")
        mock_checkpoint_recovery_cls.return_value = MagicMock(name="checkpoint")
        mock_lifecycle_cls.return_value = MagicMock(name="lifecycle")
        mock_run_service_cls.return_value = MagicMock(name="run_service")

        build_runtime_managers(
            pipeline=pipeline,
            processor_config=processor_config,
            checkpoint_manager=checkpoint_manager,
            memory_monitor=memory_monitor,
            memory_config=memory_config,
            tracer=None,
            batch_id_factory=None,
        )

        call_kwargs = mock_memory_manager_cls.call_args.kwargs
        assert call_kwargs["memory_monitor"] is None
        assert call_kwargs["memory_config"].enable_adaptive_sizing is False
        assert memory_config.enable_adaptive_sizing is True
        mock_tracing_manager_cls.assert_called_once_with(
            tracer=resolved_tracer,
            context=pipeline.context,
            config=processor_config,
            initial_batch_size=77,
            adaptive_sizing_enabled=False,
        )

    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchExecutionRunService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchExecutionLifecycleService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchCheckpointRecoveryService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchProgressService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchTracingManagerService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchMemoryManagerService"
    )
    @patch("bioetl.composition.factories.services.runtime_managers.resolve_tracer")
    def test_exact_replay_resume_uses_checkpoint_offset_and_fixed_batch_shape(
        self,
        mock_resolve_tracer: MagicMock,
        mock_memory_manager_cls: MagicMock,
        mock_tracing_manager_cls: MagicMock,
        mock_progress_cls: MagicMock,
        mock_checkpoint_recovery_cls: MagicMock,
        mock_lifecycle_cls: MagicMock,
        mock_run_service_cls: MagicMock,
    ) -> None:
        """Resume after a resize continues from checkpoint offset with adaptation off."""
        prior_memory = BatchMemoryManagerService(
            initial_batch_size=1000,
            memory_config=MemoryConfig(
                enable_adaptive_sizing=True,
                max_batch_memory_mb=1,
                min_batch_size=50,
            ),
        )
        prior_memory.check_pressure(
            current_size=2000,
            check_interval=100,
            records_fetched=100,
        )
        checkpoint_metadata = CheckpointMetadata(
            records_processed=125,
            exact_replay=True,
            input_snapshot_ids=("snapshot-1",),
            memory_decision_trace=prior_memory.decision_trace_dicts(),
        )
        persisted_checkpoint = CheckpointMetadata.from_dict(
            checkpoint_metadata.to_dict()
        )

        assert extract_checkpoint_offset(persisted_checkpoint) == 125
        assert persisted_checkpoint.memory_decision_trace[0]["old_batch_size"] == 2000
        assert persisted_checkpoint.memory_decision_trace[0]["new_batch_size"] == 1000
        assert persisted_checkpoint.memory_decision_trace[0]["reason"] == (
            "config_budget_exceeded"
        )

        pipeline = _make_pipeline(batch_size=77)
        pipeline.runtime.exact_replay = True
        processor_config = MagicMock(name="processor_config")
        checkpoint_manager = MagicMock(name="checkpoint_manager")
        memory_monitor = MagicMock(name="memory_monitor")
        memory_config = MemoryConfig(enable_adaptive_sizing=True)
        resolved_tracer = MagicMock(name="resolved_tracer")
        mock_resolve_tracer.return_value = resolved_tracer

        memory_manager = MagicMock(name="memory_manager")
        memory_manager.enabled = False
        mock_memory_manager_cls.return_value = memory_manager
        mock_tracing_manager_cls.return_value = MagicMock(name="tracing_manager")
        mock_progress_cls.return_value = MagicMock(name="progress_service")
        mock_checkpoint_recovery_cls.return_value = MagicMock(name="checkpoint")
        mock_lifecycle_cls.return_value = MagicMock(name="lifecycle")
        mock_run_service_cls.return_value = MagicMock(name="run_service")

        build_runtime_managers(
            pipeline=pipeline,
            processor_config=processor_config,
            checkpoint_manager=checkpoint_manager,
            memory_monitor=memory_monitor,
            memory_config=memory_config,
            tracer=None,
            batch_id_factory=None,
        )

        call_kwargs = mock_memory_manager_cls.call_args.kwargs
        assert call_kwargs["memory_monitor"] is None
        assert call_kwargs["memory_config"].enable_adaptive_sizing is False
        assert memory_config.enable_adaptive_sizing is True

    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchExecutionRunService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchExecutionLifecycleService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchCheckpointRecoveryService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchProgressService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchTracingManagerService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.BatchMemoryManagerService"
    )
    @patch(
        "bioetl.composition.factories.services.runtime_managers.UuidBatchIdGenerator"
    )
    @patch("bioetl.composition.factories.services.runtime_managers.resolve_tracer")
    def test_falls_back_to_default_batch_size_and_uuid_factory(
        self,
        mock_resolve_tracer: MagicMock,
        mock_uuid_batch_id_generator: MagicMock,
        mock_memory_manager_cls: MagicMock,
        mock_tracing_manager_cls: MagicMock,
        mock_progress_cls: MagicMock,
        mock_checkpoint_recovery_cls: MagicMock,
        mock_lifecycle_cls: MagicMock,
        mock_run_service_cls: MagicMock,
    ) -> None:
        """Assembly should provide safe runtime defaults when optional inputs are absent."""
        pipeline = _make_pipeline(batch_size=None)
        processor_config = MagicMock(name="processor_config")
        checkpoint_manager = MagicMock(name="checkpoint_manager")
        resolved_tracer = MagicMock(name="resolved_tracer")
        fallback_batch_id_factory = MagicMock(name="fallback_batch_id_factory")
        mock_resolve_tracer.return_value = resolved_tracer
        mock_uuid_batch_id_generator.return_value = fallback_batch_id_factory

        memory_manager = MagicMock(name="memory_manager")
        memory_manager.enabled = False
        mock_memory_manager_cls.return_value = memory_manager
        tracing_manager = MagicMock(name="tracing_manager")
        progress_service = MagicMock(name="progress_service")
        checkpoint_recovery = MagicMock(name="checkpoint_recovery")
        lifecycle = MagicMock(name="lifecycle")
        execution_run = MagicMock(name="execution_run")
        mock_tracing_manager_cls.return_value = tracing_manager
        mock_progress_cls.return_value = progress_service
        mock_checkpoint_recovery_cls.return_value = checkpoint_recovery
        mock_lifecycle_cls.return_value = lifecycle
        mock_run_service_cls.return_value = execution_run

        result = build_runtime_managers(
            pipeline=pipeline,
            processor_config=processor_config,
            checkpoint_manager=checkpoint_manager,
            memory_monitor=None,
            memory_config=None,
            tracer=None,
            batch_id_factory=None,
        )

        assert result[2] is fallback_batch_id_factory
        mock_memory_manager_cls.assert_called_once_with(
            initial_batch_size=BatchExecutor.DEFAULT_BATCH_SIZE,
            memory_monitor=None,
            memory_config=None,
            logger=pipeline.services.logger,
            metrics=pipeline.services.metrics,
            pipeline_name="test_pipeline",
        )
        mock_checkpoint_recovery_cls.assert_called_once_with(
            checkpoint_manager=checkpoint_manager,
            logger=pipeline.services.logger,
            metrics=pipeline.services.metrics,
            tracer=resolved_tracer,
            pipeline_name="test_pipeline",
            memory_manager=memory_manager,
        )
        mock_uuid_batch_id_generator.assert_called_once_with()
