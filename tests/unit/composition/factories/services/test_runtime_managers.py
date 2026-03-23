"""Unit tests for runtime manager assembly helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.composition.factories.services.runtime_managers import (
    build_runtime_managers,
)


def _make_pipeline(*, batch_size: int | None = 50) -> SimpleNamespace:
    """Build a minimal pipeline stub for runtime manager tests."""
    return SimpleNamespace(
        config=SimpleNamespace(batch_size=batch_size),
        services=SimpleNamespace(
            logger=MagicMock(name="logger"),
            data_source=MagicMock(name="data_source"),
        ),
        context=MagicMock(name="context"),
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
        )
        mock_uuid_batch_id_generator.assert_called_once_with()
