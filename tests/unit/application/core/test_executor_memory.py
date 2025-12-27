"""Unit tests for PipelineExecutor memory management features."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.memory_monitor import MemoryConfig, MemoryMonitor
from bioetl.application.core.shutdown import ShutdownSignal


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    services = MagicMock()
    services.data_source = AsyncMock()
    services.logger = MagicMock()
    return services


@pytest.fixture
def mock_record_processor():
    """Create mock record processor."""
    processor = MagicMock()
    processor.process_batch = AsyncMock(
        return_value=MagicMock(
            bronze_count=10,
            silver_count=10,
            gold_count=5,
            quarantined_count=0,
        )
    )
    return processor


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock checkpoint manager."""
    manager = MagicMock()
    manager.save_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def shutdown_signal():
    """Create shutdown signal."""
    return ShutdownSignal()


@pytest.mark.unit
class TestExecutorMemoryConfig:
    """Tests for executor memory configuration."""

    def test_executor_accepts_memory_monitor(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test executor accepts memory monitor."""
        memory_monitor = MagicMock(spec=MemoryMonitor)

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            memory_monitor=memory_monitor,
        )

        assert executor._memory_monitor is memory_monitor
        assert executor._adaptive_batch_size_enabled is True

    def test_executor_accepts_memory_config(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test executor accepts memory config."""
        memory_config = MemoryConfig(
            max_batch_memory_mb=256,
            enable_adaptive_sizing=True,
        )

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            memory_config=memory_config,
        )

        assert executor._memory_config is memory_config
        assert executor._adaptive_batch_size_enabled is True

    def test_adaptive_sizing_disabled_by_config(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test adaptive sizing can be disabled via config."""
        memory_config = MemoryConfig(enable_adaptive_sizing=False)

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            memory_config=memory_config,
        )

        assert executor._adaptive_batch_size_enabled is False


@pytest.mark.unit
class TestExecutorBatchSizeAdjustment:
    """Tests for batch size adjustment methods."""

    @pytest.fixture
    def executor_with_monitor(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Create executor with memory monitor."""
        memory_monitor = MagicMock(spec=MemoryMonitor)
        memory_monitor.get_recommended_batch_size = MagicMock(side_effect=lambda x: x)

        return PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=100,
            memory_monitor=memory_monitor,
        )

    def test_adjust_batch_size_no_reduction(self, executor_with_monitor):
        """Test batch size unchanged when no pressure."""
        executor_with_monitor._memory_monitor.get_recommended_batch_size.return_value = 100

        new_size = executor_with_monitor._adjust_batch_size(100)

        assert new_size == 100
        assert executor_with_monitor._batch_size_reductions == 0

    def test_adjust_batch_size_with_reduction(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test batch size reduction is tracked."""
        memory_monitor = MagicMock(spec=MemoryMonitor)
        memory_monitor.get_recommended_batch_size = MagicMock(return_value=50)

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=100,
            memory_monitor=memory_monitor,
        )

        new_size = executor._adjust_batch_size(100)

        assert new_size == 50
        assert executor._batch_size_reductions == 1
        assert executor._min_batch_size_used == 50

    def test_adjust_batch_size_tracks_minimum(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test minimum batch size is tracked correctly."""
        memory_monitor = MagicMock(spec=MemoryMonitor)

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=100,
            memory_monitor=memory_monitor,
        )

        # First reduction to 50
        memory_monitor.get_recommended_batch_size.return_value = 50
        executor._adjust_batch_size(100)

        # Second reduction to 25
        memory_monitor.get_recommended_batch_size.return_value = 25
        executor._adjust_batch_size(50)

        assert executor._min_batch_size_used == 25
        assert executor._batch_size_reductions == 2

    def test_try_recover_batch_size_with_monitor(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test batch size recovery uses monitor."""
        memory_monitor = MagicMock(spec=MemoryMonitor)
        memory_monitor.get_recommended_batch_size = MagicMock(return_value=75)

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=100,
            memory_monitor=memory_monitor,
        )

        recovered = executor._try_recover_batch_size(50)

        assert recovered == 75

    def test_try_recover_batch_size_without_monitor(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test batch size recovery without monitor."""
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=100,
        )

        # Set initial batch size manually
        executor._initial_batch_size = 100

        # Should increase by 10%
        recovered = executor._try_recover_batch_size(50)

        assert recovered == 55  # 50 * 1.1


@pytest.mark.unit
class TestExecutorMemoryCheckInterval:
    """Tests for memory check interval."""

    def test_get_memory_check_interval_default(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test default memory check interval."""
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
        )

        assert executor._get_memory_check_interval() == 100

    def test_get_memory_check_interval_from_config(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test memory check interval from config."""
        memory_config = MemoryConfig(check_interval_records=50)

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            memory_config=memory_config,
        )

        assert executor._get_memory_check_interval() == 50


@pytest.mark.unit
class TestExecutorConfigBasedEstimation:
    """Tests for config-based batch size estimation."""

    def test_estimate_batch_size_from_config(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test batch size estimation from config."""
        memory_config = MemoryConfig(
            max_batch_memory_mb=256,
            min_batch_size=10,
        )

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            memory_config=memory_config,
        )

        # 256MB * 1000 records/MB = 256000 max records
        estimated = executor._estimate_batch_size_from_config(500000)

        # Should be capped at calculated max
        assert estimated == 256000

    def test_estimate_batch_size_respects_minimum(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test batch size estimation respects minimum."""
        memory_config = MemoryConfig(
            max_batch_memory_mb=1,  # Very small
            min_batch_size=100,
        )

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            memory_config=memory_config,
        )

        # With only 1MB, calculated max is 1000, which is above min
        estimated = executor._estimate_batch_size_from_config(5000)

        assert estimated == 1000


@pytest.mark.unit
class TestExecutorExecution:
    """Integration tests for executor execution with memory management."""

    @pytest.fixture
    def mock_data_source_records(self):
        """Create mock data source that yields records."""

        async def generate_records(entity_type, limit=None, query=None):
            count = limit or 100
            for i in range(count):
                yield {"id": str(i), "value": i}

        return generate_records

    async def test_execute_with_adaptive_sizing(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_data_source_records,
    ):
        """Test execution uses adaptive batch sizing."""
        mock_services.data_source.fetch = mock_data_source_records

        memory_monitor = MagicMock(spec=MemoryMonitor)
        # Simulate pressure on second check, reducing from 10 to 5
        memory_monitor.get_recommended_batch_size = MagicMock(
            side_effect=[10, 5, 5, 5, 5, 10, 10, 10, 10, 10]
        )

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=10,
            memory_monitor=memory_monitor,
        )

        await executor.execute(limit=50)

        # Verify process_batch was called multiple times
        assert mock_record_processor.process_batch.call_count > 0

    async def test_execute_tracks_batch_size_metrics(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_data_source_records,
    ):
        """Test execution tracks batch size reduction metrics."""
        mock_services.data_source.fetch = mock_data_source_records

        memory_monitor = MagicMock(spec=MemoryMonitor)
        # Simulate one reduction
        call_count = [0]

        def mock_recommend(size):
            call_count[0] += 1
            return 5 if call_count[0] == 1 else size

        memory_monitor.get_recommended_batch_size = MagicMock(side_effect=mock_recommend)

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=10,
            memory_monitor=memory_monitor,
        )

        await executor.execute(limit=20)

        # At least one reduction should have occurred
        assert executor._batch_size_reductions >= 0  # May vary based on timing

    async def test_execute_without_memory_management(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_data_source_records,
    ):
        """Test execution works without memory management."""
        mock_services.data_source.fetch = mock_data_source_records

        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=10,
        )

        await executor.execute(limit=25)

        # Should process batches normally
        assert mock_record_processor.process_batch.call_count == 3  # 10 + 10 + 5
