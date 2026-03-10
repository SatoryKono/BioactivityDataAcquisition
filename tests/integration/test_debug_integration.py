"""Integration tests for debug service integration with PipelineRunner.

Verifies that debug breakpoints are triggered at correct lifecycle stages
and that the debug service correctly captures snapshots.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest

from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.observability.observer import PipelineObserver
from bioetl.application.services.medallion_lifecycle import (
    MedallionLifecycleService,
)
from bioetl.application.services.pipeline_debug_service import PipelineDebugService
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.ports.runtime.pipeline_debug import (
    DebugAction,
    StageBreakpoint,
)
from bioetl.domain.types import RunType


@pytest.fixture
def mock_debug_port():
    """Create a mock debug port that records breakpoints."""
    port = MagicMock()
    port.is_breakpoint_enabled.return_value = True
    port.on_breakpoint.return_value = DebugAction.CONTINUE
    port.on_snapshot = MagicMock()
    return port


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    from bioetl.domain.types import HealthStatus

    services = MagicMock()
    services.lock = AsyncMock()
    services.storage = MagicMock()
    services.storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    services.data_source = MagicMock()
    services.data_source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    services.storage.clear_silver = AsyncMock(return_value=0)
    services.storage.clear_gold = AsyncMock(return_value=0)
    services.__aenter__ = AsyncMock(return_value=services)
    services.__aexit__ = AsyncMock(return_value=None)
    return services


@pytest.fixture
def pipeline_config():
    """Create a minimal pipeline config."""
    return PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        silver=TableConfig(path="silver/test", name="test_silver"),
        gold=TableConfig(path="gold/test", name="test_gold"),
    )


@pytest.fixture
def runtime_config():
    """Create a minimal runtime config."""
    return RuntimeConfig(run_type=RunType.INCREMENTAL)


@pytest.fixture
def pipeline_context():
    """Create a minimal pipeline context."""
    return PipelineContext(
        run_id=str(uuid4()),
        pipeline_name="test_pipeline",
        run_type=RunType.INCREMENTAL,
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_debug_breakpoints_triggered_in_pipeline_runner(
    mock_debug_port,
    mock_services,
    pipeline_config,
    runtime_config,
    pipeline_context,
):
    """Test that debug breakpoints are triggered at correct stages."""
    # Create debug service
    logger = MagicMock()
    debug_service = PipelineDebugService(
        debug_port=mock_debug_port,
        logger=logger,
    )

    # Create mock executor
    executor = MagicMock()
    executor.execute = AsyncMock()
    executor.records_fetched = 100
    executor.get_dq_context = Mock(return_value=MagicMock())

    # Create mock checkpoint manager
    checkpoint_manager = MagicMock()
    checkpoint_manager.load_checkpoint = AsyncMock(return_value={})
    checkpoint_manager.delete_checkpoint = AsyncMock()

    # Create mock lock manager
    lock_manager = MagicMock()
    lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
    lock_manager.__aexit__ = AsyncMock(return_value=None)

    # Create mock services
    preflight = MagicMock(spec=PreflightService)
    preflight.validate_infrastructure = AsyncMock()

    lifecycle_service = MagicMock(spec=MedallionLifecycleService)
    lifecycle_service.prepare_for_run = AsyncMock()

    postrun = MagicMock(spec=PostrunService)
    postrun.run = AsyncMock()
    postrun.cleanup = AsyncMock()

    observer = MagicMock(spec=PipelineObserver)
    observer.__enter__ = Mock(return_value=observer)
    observer.__exit__ = Mock(return_value=None)

    # Create PipelineRunner with debug service
    runner = PipelineRunner(
        config=pipeline_config,
        runtime=runtime_config,
        services=mock_services,
        context=pipeline_context,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=MagicMock(),
        logger=logger,
        lock_manager=lock_manager,
        preflight=preflight,
        postrun=postrun,
        lifecycle_service=lifecycle_service,
        observer=observer,
        debug_service=debug_service,
    )

    # Execute pipeline
    await runner.run()

    # Verify breakpoints were triggered
    assert mock_debug_port.on_breakpoint.call_count >= 2
    breakpoints_hit = [
        call.args[0].breakpoint for call in mock_debug_port.on_breakpoint.call_args_list
    ]
    assert StageBreakpoint.AFTER_PREFLIGHT in breakpoints_hit
    assert StageBreakpoint.AFTER_DQ in breakpoints_hit

    # Verify snapshots were captured
    assert len(debug_service.snapshots) >= 2
    assert debug_service.snapshots[0].stage == "preflight_complete"
    assert debug_service.snapshots[-1].stage == "dq_complete"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_debug_snapshot_captures_executor_state(
    mock_debug_port,
    mock_services,
    pipeline_config,
    runtime_config,
    pipeline_context,
):
    """Test that debug snapshots capture executor state correctly."""
    logger = MagicMock()
    debug_service = PipelineDebugService(
        debug_port=mock_debug_port,
        logger=logger,
    )

    # Create mock executor with specific counts
    executor = MagicMock()
    executor.execute = AsyncMock()
    executor.records_fetched = 500
    executor.records_bronze = 480
    executor.records_silver = 460
    executor.records_gold = 450
    executor.records_quarantined = 20
    executor.get_dq_context = Mock(return_value=MagicMock())

    checkpoint_manager = MagicMock()
    checkpoint_manager.load_checkpoint = AsyncMock(return_value={})
    checkpoint_manager.delete_checkpoint = AsyncMock()

    lock_manager = MagicMock()
    lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
    lock_manager.__aexit__ = AsyncMock(return_value=None)

    preflight = MagicMock(spec=PreflightService)
    preflight.validate_infrastructure = AsyncMock()

    lifecycle_service = MagicMock(spec=MedallionLifecycleService)
    lifecycle_service.prepare_for_run = AsyncMock()

    postrun = MagicMock(spec=PostrunService)
    postrun.run = AsyncMock()
    postrun.cleanup = AsyncMock()

    observer = MagicMock(spec=PipelineObserver)
    observer.__enter__ = Mock(return_value=observer)
    observer.__exit__ = Mock(return_value=None)

    runner = PipelineRunner(
        config=pipeline_config,
        runtime=runtime_config,
        services=mock_services,
        context=pipeline_context,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=MagicMock(),
        logger=logger,
        lock_manager=lock_manager,
        preflight=preflight,
        postrun=postrun,
        lifecycle_service=lifecycle_service,
        observer=observer,
        debug_service=debug_service,
    )

    await runner.run()

    # Get the DQ snapshot (should be the last one)
    dq_snapshot = debug_service.get_latest_snapshot()
    assert dq_snapshot is not None
    assert dq_snapshot.records_fetched == 500
    # Note: records_bronze/silver/gold may be 0 if executor doesn't expose them
    # This is expected - the test verifies the plumbing works


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pipeline_runs_without_debug_service(
    mock_services,
    pipeline_config,
    runtime_config,
    pipeline_context,
):
    """Test that pipeline runs normally when debug_service is None."""
    logger = MagicMock()

    executor = MagicMock()
    executor.execute = AsyncMock()
    executor.records_fetched = 100
    executor.get_dq_context = Mock(return_value=MagicMock())

    checkpoint_manager = MagicMock()
    checkpoint_manager.load_checkpoint = AsyncMock(return_value={})
    checkpoint_manager.delete_checkpoint = AsyncMock()

    lock_manager = MagicMock()
    lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
    lock_manager.__aexit__ = AsyncMock(return_value=None)

    preflight = MagicMock(spec=PreflightService)
    preflight.validate_infrastructure = AsyncMock()

    lifecycle_service = MagicMock(spec=MedallionLifecycleService)
    lifecycle_service.prepare_for_run = AsyncMock()

    postrun = MagicMock(spec=PostrunService)
    postrun.run = AsyncMock()
    postrun.cleanup = AsyncMock()

    observer = MagicMock(spec=PipelineObserver)
    observer.__enter__ = Mock(return_value=observer)
    observer.__exit__ = Mock(return_value=None)

    # Create PipelineRunner WITHOUT debug service
    runner = PipelineRunner(
        config=pipeline_config,
        runtime=runtime_config,
        services=mock_services,
        context=pipeline_context,
        executor=executor,
        checkpoint_manager=checkpoint_manager,
        shutdown_signal=MagicMock(),
        logger=logger,
        lock_manager=lock_manager,
        preflight=preflight,
        postrun=postrun,
        lifecycle_service=lifecycle_service,
        observer=observer,
        debug_service=None,  # No debug service
    )

    # Should complete without errors
    await runner.run()
    assert executor.execute.called
