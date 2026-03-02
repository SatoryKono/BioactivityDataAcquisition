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


class TestPipelineContextStartedAt:
    """Tests for PipelineContext.started_at field."""

    def test_context_started_at_has_default(self) -> None:
        """Context should have started_at with automatic default."""
        run_id = uuid4()
        logger = MagicMock()
        before = datetime.now(UTC)

        ctx = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
        )

        after = datetime.now(UTC)
        assert ctx.started_at is not None
        assert before <= ctx.started_at <= after
        assert ctx.started_at.tzinfo == UTC

    def test_context_started_at_explicit(self) -> None:
        """Context should accept explicit started_at value."""
        run_id = uuid4()
        logger = MagicMock()
        explicit_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)

        ctx = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
            started_at=explicit_time,
        )

        assert ctx.started_at == explicit_time

    def test_context_create_factory_auto_timestamp(self) -> None:
        """create() factory should auto-generate started_at when not provided."""
        run_id = uuid4()
        logger = MagicMock()
        before = datetime.now(UTC)

        ctx = PipelineContext.create(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
        )

        after = datetime.now(UTC)
        assert before <= ctx.started_at <= after

    def test_context_create_factory_explicit_timestamp(self) -> None:
        """create() factory should use provided started_at."""
        run_id = uuid4()
        logger = MagicMock()
        explicit_time = datetime(2025, 6, 1, 10, 30, 0, tzinfo=UTC)

        ctx = PipelineContext.create(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
            started_at=explicit_time,
        )

        assert ctx.started_at == explicit_time

    def test_bind_logger_preserves_started_at(self) -> None:
        """bind_logger should preserve started_at in new context."""
        run_id = uuid4()
        logger = MagicMock()
        logger.bind.return_value = MagicMock()
        explicit_time = datetime(2025, 3, 20, 8, 0, 0, tzinfo=UTC)

        ctx = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
            started_at=explicit_time,
        )
        new_ctx = ctx.bind_logger(entity="test")

        assert new_ctx.started_at == explicit_time


class TestPipelineContextEquality:
    """Tests for PipelineContext equality and hashing."""

    def test_contexts_with_same_values_are_equal(self) -> None:
        """Contexts with same values should be equal."""
        run_id = uuid4()
        logger = MagicMock()
        started_at = datetime.now(UTC)

        ctx1 = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
            started_at=started_at,
        )
        ctx2 = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
            started_at=started_at,
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
