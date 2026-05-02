"""Tests for PipelineContext."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.domain.context import (
    CachedBronzeContext,
    InputFilterContext,
    MISSING_RUNTIME_TIMESTAMP,
    PipelineContext,
    PipelineRunContext,
    VacuumSettings,
)
from bioetl.domain.types import BatchID, RunID, RunType
from tests.helpers.clock import FIXED_TEST_TIME

CACHED_BRONZE_PATH = "test-output/bronze"


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
            started_at=datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC),
        )

    def test_context_creation(self, context: PipelineContext, run_id: RunID) -> None:
        """Context should be created with correct attributes."""
        assert context.run_id == run_id
        assert context.run_type == RunType.INCREMENTAL
        assert context.logger is not None
        assert context.replay_timestamp_anchor is None

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
        """Direct construction uses deterministic sentinel when omitted."""
        run_id = uuid4()
        logger = MagicMock()

        ctx = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
        )

        assert ctx.started_at == MISSING_RUNTIME_TIMESTAMP

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

    def test_context_create_factory_explicit_replay_anchor(self) -> None:
        """create() should preserve an explicit deterministic replay timestamp."""
        run_id = uuid4()
        logger = MagicMock()
        replay_anchor = datetime(2025, 6, 1, 0, 0, 0, tzinfo=UTC)

        ctx = PipelineContext.create(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
            replay_timestamp_anchor=replay_anchor,
        )

        assert ctx.replay_timestamp_anchor == replay_anchor

    def test_context_create_factory_auto_timestamp(self) -> None:
        """create() carries deterministic sentinel when caller omits started_at."""
        run_id = uuid4()
        logger = MagicMock()

        ctx = PipelineContext.create(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
        )

        assert ctx.started_at == MISSING_RUNTIME_TIMESTAMP

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

    def test_bind_logger_preserves_replay_timestamp_anchor(self) -> None:
        """bind_logger must not lose deterministic replay anchors."""
        run_id = uuid4()
        logger = MagicMock()
        logger.bind.return_value = MagicMock()
        replay_anchor = datetime(2025, 3, 20, 0, 0, 0, tzinfo=UTC)

        ctx = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
            replay_timestamp_anchor=replay_anchor,
        )

        new_ctx = ctx.bind_logger(entity="test")

        assert new_ctx.replay_timestamp_anchor == replay_anchor

    def test_with_source_batch_id_sets_batch_lineage(self) -> None:
        """with_source_batch_id should return a copy with batch lineage attached."""
        run_id = uuid4()
        logger = MagicMock()
        ctx = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
        )
        batch_id = BatchID(uuid4())

        new_ctx = ctx.with_source_batch_id(batch_id)

        assert new_ctx is not ctx
        assert new_ctx.source_batch_id == batch_id
        assert ctx.source_batch_id is None

    def test_bind_logger_preserves_source_batch_id(self) -> None:
        """bind_logger should not drop active batch lineage."""
        run_id = uuid4()
        logger = MagicMock()
        logger.bind.return_value = MagicMock()
        batch_id = BatchID(uuid4())
        ctx = PipelineContext(
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            logger=logger,
            source_batch_id=batch_id,
        )

        new_ctx = ctx.bind_logger(entity="test")

        assert new_ctx.source_batch_id == batch_id


class TestPipelineContextEquality:
    """Tests for PipelineContext equality and hashing."""

    def test_contexts_with_same_values_are_equal(self) -> None:
        """Contexts with same values should be equal."""
        run_id = uuid4()
        logger = MagicMock()
        started_at = FIXED_TEST_TIME

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


class TestRunContextValidationAndProperties:
    """Coverage tests for context dataclasses used by orchestration."""

    def test_pipeline_run_context_log_correlation_fields_without_manifest(self) -> None:
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
        )

        assert ctx.log_correlation_fields() == {
            "run_id": str(ctx.run_id),
            "pipeline": "chembl_activity",
            "pipeline_name": "chembl_activity",
        }

    def test_pipeline_run_context_log_correlation_fields_with_manifest(self) -> None:
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            manifest_id="manifest-123",
        )

        assert ctx.log_correlation_fields() == {
            "run_id": str(ctx.run_id),
            "pipeline": "chembl_activity",
            "pipeline_name": "chembl_activity",
            "manifest_id": "manifest-123",
        }

    def test_cached_bronze_from_options_and_validation(self) -> None:
        ctx = CachedBronzeContext.from_options(
            path=CACHED_BRONZE_PATH, date="2026-01-20"
        )

        assert ctx.enabled is True
        assert ctx.bronze_path == CACHED_BRONZE_PATH
        assert ctx.bronze_date == "2026-01-20"

        # Exercise early return branch in _validate_date_format
        disabled = CachedBronzeContext.disabled()
        disabled._validate_date_format()

    def test_cached_bronze_invalid_date_raises(self) -> None:
        with pytest.raises(
            ValueError, match="bronze_date must be in YYYY-MM-DD format"
        ):
            CachedBronzeContext.from_options(date="2026/01/20")

    def test_input_filter_from_multi_ids_validation(self) -> None:
        ctx = InputFilterContext.from_multi_ids(
            {"molecule_chembl_id": ("CHEMBL1",), "document_chembl_id": ("DOC1",)}
        )
        assert ctx.filter_field == "molecule_chembl_id"

        with pytest.raises(ValueError, match="multi_filter_ids must be non-empty"):
            InputFilterContext.from_multi_ids({})

    def test_input_filter_direct_and_csv_validation(self) -> None:
        with pytest.raises(ValueError, match="filter_field is required"):
            InputFilterContext.from_ids(("P12345",), "")

        with pytest.raises(ValueError, match="source_path is required"):
            InputFilterContext.from_csv("", "accession", "accession")

    def test_vacuum_config_validation(self) -> None:
        with pytest.raises(ValueError, match="retention_days must be positive"):
            VacuumSettings(enabled=True, retention_days=0)

    def test_pipeline_run_context_properties(self) -> None:
        run_id = uuid4()
        ctx = PipelineRunContext(
            pipeline_name="chembl_publication",
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            input_filter=InputFilterContext.from_ids(("P12345",), "accession"),
            cached_bronze=CachedBronzeContext.from_options(),
            vacuum=VacuumSettings(enabled=True, retention_days=7),
        )

        assert ctx.has_input_filter is True
        assert ctx.has_cached_bronze is True
        assert ctx.vacuum_enabled_override is True

    def test_pipeline_run_context_replay_parentage_fields(self) -> None:
        ctx = PipelineRunContext(
            pipeline_name="chembl_activity",
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            replay_of_run_id="run-parent",
            replay_of_manifest_id="manifest-parent",
        )

        assert ctx.replay_of_run_id == "run-parent"
        assert ctx.replay_of_manifest_id == "manifest-parent"
