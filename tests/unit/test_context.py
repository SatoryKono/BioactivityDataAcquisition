"""Tests for PipelineContext."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType


class TestPipelineContext:
    """Tests for the PipelineContext class."""

    @pytest.fixture
    def mock_logger(self) -> MagicMock:
        """Create a mock logger with bind() method."""
        logger = MagicMock()
        # bind() should return a new logger
        logger.bind.return_value = MagicMock()
        return logger

    @pytest.fixture
    def run_id(self) -> RunID:
        """Create a test RunID."""
        return uuid4()

    @pytest.fixture
    def context(self, run_id: RunID, mock_logger: MagicMock) -> PipelineContext:
        """Create a PipelineContext instance."""
        return PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

    def test_context_creation(self, context: PipelineContext, run_id: RunID) -> None:
        """Context should be created with correct attributes."""
        assert context.run_id == run_id
        assert context.run_type == RunType.INCREMENTAL
        assert context.logger is not None

    def test_context_is_frozen(self, context: PipelineContext) -> None:
        """Context should be immutable (frozen dataclass)."""
        from dataclasses import FrozenInstanceError

        with pytest.raises(FrozenInstanceError):
            context.run_type = RunType.BACKFILL  # type: ignore[misc]

    def test_bind_logger_returns_new_context(
        self, context: PipelineContext, run_id: RunID
    ) -> None:
        """bind_logger should return a new context with bound logger."""
        new_context = context.bind_logger(entity="activity", batch=1)

        # Should return a new context
        assert new_context is not context

        # Original context should be unchanged
        assert context.run_id == run_id

        # New context should have same run_id and run_type
        assert new_context.run_id == run_id
        assert new_context.run_type == RunType.INCREMENTAL

    def test_bind_logger_calls_logger_bind(
        self, context: PipelineContext, mock_logger: MagicMock
    ) -> None:
        """bind_logger should call logger.bind with kwargs."""
        context.bind_logger(entity="activity", batch_num=42)

        mock_logger.bind.assert_called_once_with(entity="activity", batch_num=42)

    def test_bind_logger_uses_bound_logger(
        self, context: PipelineContext, mock_logger: MagicMock
    ) -> None:
        """New context should use the bound logger."""
        bound_logger = MagicMock()
        mock_logger.bind.return_value = bound_logger

        new_context = context.bind_logger(key="value")

        assert new_context.logger is bound_logger

    def test_context_with_different_run_types(
        self, run_id: RunID, mock_logger: MagicMock
    ) -> None:
        """Context should work with all RunType values."""
        for run_type in RunType:
            ctx = PipelineContext(
                run_id=run_id,
                run_type=run_type,
                logger=mock_logger,
            )
            assert ctx.run_type == run_type


class TestPipelineContextEquality:
    """Tests for PipelineContext equality and hashing."""

    def test_contexts_with_same_values_are_equal(self) -> None:
        """Contexts with same values should be equal."""
        run_id = uuid4()
        logger = MagicMock()
        started_at = datetime.now(UTC)

        ctx1 = PipelineContext(
            run_id=run_id, run_type=RunType.INCREMENTAL, logger=logger, started_at=started_at
        )
        ctx2 = PipelineContext(
            run_id=run_id, run_type=RunType.INCREMENTAL, logger=logger, started_at=started_at
        )

        assert ctx1 == ctx2

    def test_contexts_with_different_run_id_not_equal(self) -> None:
        """Contexts with different run_id should not be equal."""
        logger = MagicMock()

        ctx1 = PipelineContext(
            run_id=uuid4(), run_type=RunType.INCREMENTAL, logger=logger
        )
        ctx2 = PipelineContext(
            run_id=uuid4(), run_type=RunType.INCREMENTAL, logger=logger
        )

        assert ctx1 != ctx2

    def test_contexts_with_different_run_type_not_equal(self) -> None:
        """Contexts with different run_type should not be equal."""
        run_id = uuid4()
        logger = MagicMock()

        ctx1 = PipelineContext(
            run_id=run_id, run_type=RunType.INCREMENTAL, logger=logger
        )
        ctx2 = PipelineContext(run_id=run_id, run_type=RunType.BACKFILL, logger=logger)

        assert ctx1 != ctx2
