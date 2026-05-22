"""Unit tests for CheckpointRuntimeService."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointRuntimeService,
)
from bioetl.application.services.checkpoint_compatibility_service import (
    CheckpointCompatibilityService,
)
from bioetl.domain.types.checkpoint_metadata import (
    CheckpointCompatibilityResult,
    CheckpointMetadata,
)
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite


@pytest.fixture
def mock_checkpoint_port():
    """Create mock checkpoint port."""
    port = AsyncMock()
    port.load = AsyncMock(return_value=None)
    port.save = AsyncMock()
    port.delete = AsyncMock()
    port.list_all = AsyncMock(return_value=["pipeline_a", "pipeline_b"])
    return port


@pytest.fixture
def mock_logger():
    """Create mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Create mock MetricsPort."""
    metrics = MagicMock()
    metrics.increment_counter = MagicMock()
    return metrics


@pytest.fixture
def compatible_checkpoint_compatibility_service():
    """Create checkpoint compatibility service that accepts loaded checkpoints."""
    service = MagicMock()
    service.validate_checkpoint_compatibility.return_value = (
        CheckpointCompatibilityResult.compatible_result()
    )
    return service


@pytest.fixture
def checkpoint_manager(mock_checkpoint_port, mock_logger):
    """Create CheckpointRuntimeService instance."""
    run_id = deterministic_uuid_from_callsite("replay-sensitive")
    return CheckpointRuntimeService(
        checkpoint_port=mock_checkpoint_port,
        logger=mock_logger,
        pipeline_name="test_pipeline",
        run_id=run_id,
        resume=True,
    )


@pytest.mark.unit
class TestCheckpointManagerInit:
    """Tests for CheckpointRuntimeService initialization."""

    def test_init_with_all_params(self, mock_checkpoint_port, mock_logger):
        """Test initialization with all parameters."""
        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="my_pipeline",
            run_id=run_id,
            resume=False,
        )

        assert manager._pipeline_name == "my_pipeline"
        assert manager._run_id == run_id
        assert manager._resume is False


@pytest.mark.unit
class TestCheckpointManagerLoadCheckpoint:
    """Tests for CheckpointRuntimeService.load_checkpoint method."""

    async def test_load_checkpoint_when_resume_true_and_exists(
        self,
        mock_checkpoint_port,
        mock_logger,
        compatible_checkpoint_compatibility_service,
    ):
        """Test load_checkpoint when resuming and checkpoint exists."""
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
            checkpoint_compatibility_service=(
                compatible_checkpoint_compatibility_service
            ),
            current_metadata=CheckpointMetadata(records_processed=0),
        )

        result = await manager.load_checkpoint()

        assert result is not None
        mock_checkpoint_port.load.assert_called_once_with("test_pipeline")
        mock_logger.info.assert_called()

    async def test_load_checkpoint_preserves_memory_decision_trace(
        self,
        mock_checkpoint_port,
        mock_logger,
        compatible_checkpoint_compatibility_service,
    ) -> None:
        """Typed resume metadata keeps adaptive-memory trace entries for replay."""
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {
                "records_processed": 1000,
                "exact_replay": True,
                "input_snapshot_ids": ["snapshot-1"],
                "memory_decision_trace": [
                    {
                        "decision_index": 1,
                        "record_index": 100,
                        "stage": "pressure_check",
                        "old_batch_size": 1000,
                        "new_batch_size": 500,
                        "adaptive_sizing_enabled": True,
                        "monitor_available": True,
                        "config_available": True,
                        "pressure_state": True,
                        "monitor_mode": "psutil",
                        "reason": "monitor_recommended_reduction",
                    }
                ],
            },
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            checkpoint_compatibility_service=(
                compatible_checkpoint_compatibility_service
            ),
            current_metadata=CheckpointMetadata(records_processed=0),
        )

        result = await manager.load_checkpoint()

        assert result is not None
        assert result.exact_replay is True
        assert result.input_snapshot_ids == ("snapshot-1",)
        assert result.memory_decision_trace[0]["new_batch_size"] == 500
        assert result.memory_decision_trace[0]["reason"] == (
            "monitor_recommended_reduction"
        )

    async def test_load_checkpoint_emits_loaded_metric(
        self,
        mock_checkpoint_port,
        mock_logger,
        mock_metrics,
        compatible_checkpoint_compatibility_service,
    ):
        """Successful resume emits bounded checkpoint load status."""
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            checkpoint_compatibility_service=(
                compatible_checkpoint_compatibility_service
            ),
            current_metadata=CheckpointMetadata(records_processed=0),
        )

        result = await manager.load_checkpoint()

        assert result is not None
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "test_pipeline", "status": "loaded"},
        )

    async def test_load_checkpoint_when_resume_true_but_no_checkpoint(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint when resuming but no checkpoint exists."""
        mock_checkpoint_port.load.return_value = None

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_checkpoint_port.load.assert_called_once()

    async def test_load_checkpoint_fails_closed_without_compatibility_context(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
        )

        result = await manager.load_checkpoint()

        assert result is None
        warning_extra = mock_logger.warning.call_args.kwargs
        assert warning_extra["resume_rejected"] is True
        assert warning_extra["compatibility_disposition"] == ("missing_context_blocked")
        assert warning_extra["compatibility_service_available"] is False
        assert warning_extra["current_identity"]["manifest_id"] is None
        assert any(
            "Missing current checkpoint metadata" in message
            for message in warning_extra["messages"]
        )
        assert any(
            "Missing checkpoint compatibility service" in message
            for message in warning_extra["messages"]
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {
                "pipeline": "test_pipeline",
                "status": "missing_compatibility_context",
            },
        )

    async def test_load_checkpoint_emits_missing_metric_when_not_found(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ):
        """Missing checkpoint emits bounded missing status."""
        mock_checkpoint_port.load.return_value = None

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "test_pipeline", "status": "missing"},
        )

    async def test_load_checkpoint_when_resume_false(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint when not resuming."""
        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=False,
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_checkpoint_port.load.assert_not_called()


@pytest.mark.unit
class TestCheckpointManagerSaveCheckpoint:
    """Tests for CheckpointRuntimeService.save_checkpoint method."""

    async def test_save_checkpoint_saves_metadata(
        self, checkpoint_manager, mock_checkpoint_port
    ):
        """Test save_checkpoint saves metadata correctly."""
        await checkpoint_manager.save_checkpoint(
            CheckpointMetadata(records_processed=500)
        )

        mock_checkpoint_port.save.assert_called_once()
        call_kwargs = mock_checkpoint_port.save.call_args.kwargs
        assert call_kwargs["pipeline"] == "test_pipeline"
        assert call_kwargs["metadata"] == {"records_processed": 500}


@pytest.mark.unit
class TestCheckpointManagerDeleteCheckpoint:
    """Tests for CheckpointRuntimeService.delete_checkpoint method."""

    async def test_delete_checkpoint(self, checkpoint_manager, mock_checkpoint_port):
        """Test delete_checkpoint calls port.delete."""
        await checkpoint_manager.delete_checkpoint()

        mock_checkpoint_port.delete.assert_called_once_with("test_pipeline")


@pytest.mark.unit
class TestCheckpointManagerListAll:
    """Tests for CheckpointRuntimeService.list_all method."""

    async def test_list_all_delegates_to_port(
        self, checkpoint_manager, mock_checkpoint_port
    ):
        """Test list_all delegates directly to checkpoint port."""
        result = await checkpoint_manager.list_all()

        mock_checkpoint_port.list_all.assert_called_once_with()
        assert result == ["pipeline_a", "pipeline_b"]


@pytest.mark.unit
class TestCheckpointManagerFullScanOnly:
    """Tests for CheckpointRuntimeService loading_strategy=FULL_SCAN_ONLY behavior (ADR-031)."""

    async def test_load_checkpoint_blocked_when_full_scan_only(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint returns None when loading_strategy=FULL_SCAN_ONLY."""
        from bioetl.domain.medallion import LoadingStrategy

        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        result = await manager.load_checkpoint()

        mock_checkpoint_port.load.assert_not_called()
        assert result is None
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert "full_scan_only" in warning_call[0][0].lower()

    async def test_load_checkpoint_emits_blocked_metric_when_full_scan_only(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        """Blocked resume path emits bounded blocked status."""
        from bioetl.domain.medallion import LoadingStrategy

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
            metrics=mock_metrics,
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "chembl_publication", "status": "blocked"},
        )

    async def test_load_checkpoint_warning_includes_pipeline_name(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test that warning includes pipeline name in extra context."""
        from bioetl.domain.medallion import LoadingStrategy

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="pubmed_publication",
            run_id=run_id,
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        await manager.load_checkpoint()

        warning_call = mock_logger.warning.call_args
        assert warning_call.kwargs["pipeline"] == "pubmed_publication"

    async def test_load_checkpoint_works_normally_without_strategy(
        self,
        mock_checkpoint_port,
        mock_logger,
        compatible_checkpoint_compatibility_service,
    ):
        """Test load_checkpoint works normally when no loading_strategy set."""
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=run_id,
            resume=True,
            checkpoint_compatibility_service=(
                compatible_checkpoint_compatibility_service
            ),
            current_metadata=CheckpointMetadata(records_processed=0),
        )

        result = await manager.load_checkpoint()

        mock_checkpoint_port.load.assert_called_once()
        assert result is not None
        assert result.records_processed == 1000
        mock_logger.warning.assert_not_called()

    async def test_load_checkpoint_no_warning_when_resume_false(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test no warning when resume=False, even with full_scan_only."""
        from bioetl.domain.medallion import LoadingStrategy

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=False,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        result = await manager.load_checkpoint()

        mock_logger.warning.assert_not_called()
        assert result is None

    async def test_default_loading_strategy_is_none(
        self,
        mock_checkpoint_port,
        mock_logger,
        compatible_checkpoint_compatibility_service,
    ):
        """Test that loading_strategy defaults to None (allows resume)."""
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 500},
        )

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
            checkpoint_compatibility_service=(
                compatible_checkpoint_compatibility_service
            ),
            current_metadata=CheckpointMetadata(records_processed=0),
        )

        result = await manager.load_checkpoint()

        mock_checkpoint_port.load.assert_called_once()
        assert result is not None


@pytest.mark.unit
class TestCheckpointManagerLoadingStrategy:
    """Tests for CheckpointRuntimeService loading_strategy behavior (ADR-031)."""

    async def test_load_checkpoint_blocked_when_loading_strategy_full_scan_only(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test load_checkpoint returns None when loading_strategy=FULL_SCAN_ONLY."""
        from bioetl.domain.medallion import LoadingStrategy

        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        result = await manager.load_checkpoint()

        # Checkpoint load should NOT be called - blocked immediately
        mock_checkpoint_port.load.assert_not_called()
        assert result is None
        mock_logger.warning.assert_called_once()

    async def test_loading_strategy_none_allows_checkpoint_resume(
        self,
        mock_checkpoint_port,
        mock_logger,
        compatible_checkpoint_compatibility_service,
    ):
        """Test loading_strategy=None allows normal checkpoint resume."""

        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 1000},
        )

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
            loading_strategy=None,
            checkpoint_compatibility_service=(
                compatible_checkpoint_compatibility_service
            ),
            current_metadata=CheckpointMetadata(records_processed=0),
        )

        assert manager._loading_strategy is None

        result = await manager.load_checkpoint()
        assert result is not None
        assert result.records_processed == 1000

    async def test_loading_strategy_warning_references_adr_031(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test that warning message references ADR-031."""
        from bioetl.domain.medallion import LoadingStrategy

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_publication",
            run_id=run_id,
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        await manager.load_checkpoint()

        warning_call = mock_logger.warning.call_args
        assert "ADR-031" in warning_call[0][0]

    async def test_loading_strategy_string_conversion(
        self, mock_checkpoint_port, mock_logger
    ):
        """Test that string loading_strategy is converted to enum."""
        await asyncio.sleep(0)
        from bioetl.domain.medallion import LoadingStrategy

        run_id = deterministic_uuid_from_callsite("replay-sensitive")
        # Note: CheckpointRuntimeService receives LoadingStrategy enum from PipelineConfig
        # This test verifies the enum-based behavior
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="test_pipeline",
            run_id=run_id,
            resume=True,
            loading_strategy=LoadingStrategy.FULL_SCAN_ONLY,
        )

        assert manager._loading_strategy == LoadingStrategy.FULL_SCAN_ONLY


@pytest.mark.unit
class TestCheckpointManagerCompatibilityPolicy:
    """Tests for checkpoint compatibility policy behavior."""

    async def test_soft_fail_policy_blocks_resume_on_incompatibility(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 42, "effective_config_hash": "old"},
        )
        compatibility_service = MagicMock()
        compatibility_service.validate_checkpoint_compatibility.return_value = (
            CheckpointCompatibilityResult.incompatible_result(
                dq_compatible=False,
                pipeline_compatible=True,
                execution_identity_compatible=False,
                messages=["effective config mismatch"],
            )
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            checkpoint_compatibility_service=compatibility_service,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                effective_config_hash="new",
            ),
            compatibility_policy="soft_fail",
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_logger.warning.assert_called()
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "chembl_activity", "status": "incompatible"},
        )

    async def test_observe_policy_allows_resume_on_incompatibility(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 84, "effective_config_hash": "old"},
        )
        compatibility_service = MagicMock()
        compatibility_service.validate_checkpoint_compatibility.return_value = (
            CheckpointCompatibilityResult.incompatible_result(
                dq_compatible=True,
                pipeline_compatible=True,
                execution_identity_compatible=False,
                messages=["execution fingerprint mismatch"],
            )
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            checkpoint_compatibility_service=compatibility_service,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                execution_fingerprint="new-fp",
            ),
            compatibility_policy="observe",
        )

        result = await manager.load_checkpoint()

        assert result is None
        mock_logger.warning.assert_called()
        warning_call = mock_logger.warning.call_args
        assert "resume blocked despite degraded observe policy" in warning_call.args[0]
        assert warning_call.kwargs["resume_rejected"] is True
        assert warning_call.kwargs["execution_identity_compatible"] is False
        assert (
            warning_call.kwargs["compatibility_disposition"]
            == "observe_blocked_identity"
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "chembl_activity", "status": "observe_blocked_identity"},
        )

    async def test_observe_policy_still_allows_resume_on_non_identity_mismatch(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 84, "dq_contract_compatibility_hash": "old"},
        )
        compatibility_service = MagicMock()
        compatibility_service.validate_checkpoint_compatibility.return_value = (
            CheckpointCompatibilityResult.incompatible_result(
                dq_compatible=False,
                pipeline_compatible=True,
                execution_identity_compatible=True,
                messages=["dq mismatch"],
            )
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            checkpoint_compatibility_service=compatibility_service,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                dq_contract_compatibility_hash="new",
            ),
            compatibility_policy="observe",
        )

        result = await manager.load_checkpoint()

        assert result is not None
        assert result.records_processed == 84
        warning_call = mock_logger.warning.call_args
        assert "resume continues" in warning_call.args[0]
        assert warning_call.kwargs["resume_rejected"] is False
        assert (
            warning_call.kwargs["compatibility_disposition"]
            == "observe_loaded_degraded"
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "chembl_activity", "status": "observe_loaded_degraded"},
        )

    async def test_observe_policy_blocks_non_identity_mismatch_for_strict_profiles(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {
                "records_processed": 84,
                "dq_contract_compatibility_hash": "old",
                "required_persistence_profile": "replay_ready",
            },
        )
        compatibility_service = MagicMock()
        compatibility_service.validate_checkpoint_compatibility.return_value = (
            CheckpointCompatibilityResult.incompatible_result(
                dq_compatible=False,
                pipeline_compatible=True,
                execution_identity_compatible=True,
                messages=["dq mismatch"],
            )
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            checkpoint_compatibility_service=compatibility_service,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                dq_contract_compatibility_hash="new",
                required_persistence_profile="replay_ready",
            ),
            compatibility_policy="observe",
        )

        result = await manager.load_checkpoint()

        assert result is None
        warning_call = mock_logger.warning.call_args
        assert "resume blocked despite degraded observe policy" in warning_call.args[0]
        assert warning_call.kwargs["resume_rejected"] is True
        assert (
            warning_call.kwargs["compatibility_disposition"]
            == "observe_blocked_identity"
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "chembl_activity", "status": "observe_blocked_identity"},
        )

    async def test_hard_fail_policy_raises_on_incompatibility(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 84, "effective_config_hash": "old"},
        )
        compatibility_service = MagicMock()
        compatibility_service.validate_checkpoint_compatibility.return_value = (
            CheckpointCompatibilityResult.incompatible_result(
                dq_compatible=False,
                pipeline_compatible=False,
                execution_identity_compatible=False,
                messages=["dq mismatch", "pipeline mismatch"],
            )
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            checkpoint_compatibility_service=compatibility_service,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                dq_contract_compatibility_hash="new",
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(
            ValueError,
            match="hard_fail policy",
        ):
            await manager.load_checkpoint()
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "chembl_activity", "status": "incompatible_hard_fail"},
        )

    async def test_save_checkpoint_enriches_execution_identity(
        self, mock_checkpoint_port, mock_logger
    ) -> None:
        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=False,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                dq_contract_compatibility_hash="dq-hash",
                pipeline_version="1.2.3",
                effective_config_hash="cfg-hash",
                effective_config_artifact_id="artifact-1",
                execution_fingerprint="exec-fp",
                composite_run_identity="run-1",
                manifest_id="manifest-1",
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                exact_replay=True,
                input_snapshot_ids=("snapshot-1",),
                memory_decision_trace=(
                    {
                        "decision_index": 1,
                        "record_index": 100,
                        "stage": "pressure_check",
                        "old_batch_size": 1000,
                        "new_batch_size": 500,
                        "adaptive_sizing_enabled": True,
                        "monitor_available": True,
                        "config_available": True,
                        "pressure_state": True,
                        "monitor_mode": "psutil",
                        "reason": "monitor_recommended_reduction",
                    },
                ),
            ),
        )

        await manager.save_checkpoint(123)

        call_kwargs = mock_checkpoint_port.save.call_args.kwargs
        assert call_kwargs["metadata"]["records_processed"] == 123
        assert call_kwargs["metadata"]["dq_contract_compatibility_hash"] == "dq-hash"
        assert call_kwargs["metadata"]["pipeline_version"] == "1.2.3"
        assert call_kwargs["metadata"]["effective_config_hash"] == "cfg-hash"
        assert call_kwargs["metadata"]["effective_config_artifact_id"] == "artifact-1"
        assert call_kwargs["metadata"]["execution_fingerprint"] == "exec-fp"
        assert call_kwargs["metadata"]["composite_run_identity"] == "run-1"
        assert call_kwargs["metadata"]["manifest_id"] == "manifest-1"
        assert call_kwargs["metadata"]["contract_ref"] == "chembl.activity"
        assert call_kwargs["metadata"]["contract_version"] == "1.0.0"
        assert call_kwargs["metadata"]["exact_replay"] is True
        assert call_kwargs["metadata"]["input_snapshot_ids"] == ["snapshot-1"]
        assert (
            call_kwargs["metadata"]["memory_decision_trace"][0]["new_batch_size"] == 500
        )

    async def test_soft_fail_resume_logs_checkpoint_identity_payload(
        self, mock_checkpoint_port, mock_logger
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {
                "records_processed": 42,
                "composite_run_identity": "run-old",
                "manifest_id": "manifest-old",
                "contract_ref": "chembl.activity",
                "contract_version": "1.0.0",
                "exact_replay": True,
                "input_snapshot_ids": ["snapshot-old"],
            },
        )
        compatibility_service = MagicMock()
        compatibility_service.validate_checkpoint_compatibility.return_value = (
            CheckpointCompatibilityResult.incompatible_result(
                dq_compatible=True,
                pipeline_compatible=True,
                execution_identity_compatible=False,
                messages=["manifest mismatch"],
            )
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            checkpoint_compatibility_service=compatibility_service,
            current_metadata=CheckpointMetadata(
                records_processed=0,
                composite_run_identity="run-new",
                manifest_id="manifest-new",
                effective_config_hash="cfg-new",
                execution_fingerprint="fp-new",
            ),
            compatibility_policy="soft_fail",
        )

        result = await manager.load_checkpoint()

        assert result is None
        warning_extra = mock_logger.warning.call_args.kwargs
        assert warning_extra["resume_rejected"] is True
        assert warning_extra["current_identity"]["composite_run_identity"] == "run-new"
        assert warning_extra["current_identity"]["manifest_id"] == "manifest-new"
        assert warning_extra["current_identity"]["effective_config_hash"] == "cfg-new"
        assert warning_extra["current_identity"]["execution_fingerprint"] == "fp-new"
        assert (
            warning_extra["checkpoint_identity"]["composite_run_identity"] == "run-old"
        )
        assert warning_extra["checkpoint_identity"]["manifest_id"] == "manifest-old"
        assert warning_extra["checkpoint_identity"]["exact_replay"] is True

    async def test_soft_fail_resume_blocks_when_current_metadata_is_missing(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 42, "manifest_id": "manifest-old"},
        )
        compatibility_service = MagicMock()

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            checkpoint_compatibility_service=compatibility_service,
            compatibility_policy="soft_fail",
        )

        result = await manager.load_checkpoint()

        assert result is None
        compatibility_service.validate_checkpoint_compatibility.assert_not_called()
        warning_extra = mock_logger.warning.call_args.kwargs
        assert warning_extra["resume_rejected"] is True
        assert warning_extra["compatibility_disposition"] == ("missing_context_blocked")
        assert warning_extra["compatibility_service_available"] is True
        assert any(
            "Missing current checkpoint metadata" in message
            for message in warning_extra["messages"]
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {
                "pipeline": "chembl_activity",
                "status": "missing_compatibility_context",
            },
        )

    async def test_hard_fail_resume_raises_when_context_missing(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 42},
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            compatibility_policy="hard_fail",
        )

        with pytest.raises(
            ValueError,
            match="requires compatibility context",
        ):
            await manager.load_checkpoint()
        mock_logger.warning.assert_not_called()
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {
                "pipeline": "chembl_activity",
                "status": "missing_compatibility_context_hard_fail",
            },
        )

    async def test_observe_resume_blocks_unproven_identity_with_diagnostic(
        self, mock_checkpoint_port, mock_logger, mock_metrics
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 42},
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            metrics=mock_metrics,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=mock_logger
            ),
            current_metadata=CheckpointMetadata(records_processed=0),
            compatibility_policy="observe",
        )

        result = await manager.load_checkpoint()

        assert result is None
        warning_extra = mock_logger.warning.call_args.kwargs
        assert warning_extra["resume_rejected"] is True
        assert warning_extra["identity_continuity_proven"] is False
        assert any(
            "Execution identity continuity not proven" in message
            for message in warning_extra["messages"]
        )
        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_checkpoint_load_events_total",
            1,
            {"pipeline": "chembl_activity", "status": "observe_blocked_identity"},
        )

    async def test_hard_fail_policy_raises_on_manifest_identity_mismatch(
        self, mock_checkpoint_port, mock_logger
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {"records_processed": 100, "manifest_id": "manifest-old"},
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=mock_logger
            ),
            current_metadata=CheckpointMetadata(
                records_processed=0,
                manifest_id="manifest-new",
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(ValueError, match="Manifest identity mismatch"):
            await manager.load_checkpoint()

    async def test_hard_fail_policy_raises_on_contract_reference_mismatch(
        self, mock_checkpoint_port, mock_logger
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {
                "records_processed": 100,
                "contract_ref": "chembl.activity",
                "contract_version": "1.0.0",
            },
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=mock_logger
            ),
            current_metadata=CheckpointMetadata(
                records_processed=0,
                contract_ref="chembl.assay",
                contract_version="1.0.0",
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(ValueError, match="Contract reference mismatch"):
            await manager.load_checkpoint()

    async def test_hard_fail_policy_raises_on_exact_replay_snapshot_mismatch(
        self, mock_checkpoint_port, mock_logger
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {
                "records_processed": 100,
                "exact_replay": True,
                "input_snapshot_ids": ["bronze:chembl.activity:2025-01-01"],
            },
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=mock_logger
            ),
            current_metadata=CheckpointMetadata(
                records_processed=0,
                exact_replay=True,
                input_snapshot_ids=("bronze:chembl.activity:2025-01-02",),
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(ValueError, match="Input snapshot identity mismatch"):
            await manager.load_checkpoint()

    async def test_hard_fail_policy_allows_exact_replay_resume_with_memory_trace(
        self, mock_checkpoint_port, mock_logger
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        decision_trace = [
            {
                "decision_index": 1,
                "stage": "pressure_check",
                "old_batch_size": 100,
                "new_batch_size": 50,
                "reason": "monitor_recommended_reduction",
                "pressure_state": True,
                "monitor_mode": "psutil",
            }
        ]
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {
                "records_processed": 125,
                "execution_fingerprint": "fingerprint-stable",
                "manifest_id": "manifest-stable",
                "effective_config_hash": "effective-config-stable",
                "effective_config_artifact_id": "artifact-stable",
                "contract_ref": "chembl.activity",
                "contract_version": "1.0.0",
                "dq_contract_compatibility_hash": "dq-hash-stable",
                "pipeline_version": "1.0.0",
                "git_commit": "abc1234",
                "dependency_lock_hash": "lock-hash-stable",
                "normalization_profile_ref": "chembl.activity",
                "normalization_profile_version": "2026.03",
                "normalization_profile_hash": "norm-hash-stable",
                "exact_replay": True,
                "input_snapshot_ids": ["bronze:chembl.activity:2025-01-01"],
                "input_snapshot_fingerprint": "snapshot-fingerprint-stable",
                "memory_decision_trace": decision_trace,
            },
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=mock_logger
            ),
            current_metadata=CheckpointMetadata(
                records_processed=0,
                execution_fingerprint="fingerprint-stable",
                manifest_id="manifest-stable",
                effective_config_hash="effective-config-stable",
                effective_config_artifact_id="artifact-stable",
                contract_ref="chembl.activity",
                contract_version="1.0.0",
                dq_contract_compatibility_hash="dq-hash-stable",
                pipeline_version="1.0.0",
                git_commit="abc1234",
                dependency_lock_hash="lock-hash-stable",
                normalization_profile_ref="chembl.activity",
                normalization_profile_version="2026.03",
                normalization_profile_hash="norm-hash-stable",
                exact_replay=True,
                input_snapshot_ids=("bronze:chembl.activity:2025-01-01",),
                input_snapshot_fingerprint="snapshot-fingerprint-stable",
            ),
            compatibility_policy="hard_fail",
        )

        result = await manager.load_checkpoint()

        assert result is not None
        assert result.records_processed == 125
        assert result.exact_replay is True
        assert result.input_snapshot_ids == ("bronze:chembl.activity:2025-01-01",)
        assert result.memory_decision_trace == (decision_trace[0],)

    async def test_hard_fail_policy_raises_on_composite_run_identity_mismatch(
        self, mock_checkpoint_port, mock_logger
    ) -> None:
        saved_run_id = deterministic_uuid_from_callsite("replay-sensitive")
        mock_checkpoint_port.load.return_value = (
            saved_run_id,
            {
                "records_processed": 100,
                "composite_run_identity": "composite-run-old",
            },
        )

        manager = CheckpointRuntimeService(
            checkpoint_port=mock_checkpoint_port,
            logger=mock_logger,
            pipeline_name="chembl_activity",
            run_id=deterministic_uuid_from_callsite("replay-sensitive"),
            resume=True,
            checkpoint_compatibility_service=CheckpointCompatibilityService(
                logger=mock_logger
            ),
            current_metadata=CheckpointMetadata(
                records_processed=0,
                composite_run_identity="composite-run-new",
            ),
            compatibility_policy="hard_fail",
        )

        with pytest.raises(
            ValueError, match="Execution identity continuity not proven"
        ):
            await manager.load_checkpoint()
