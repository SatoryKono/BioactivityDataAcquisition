# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for DependencyCoordinatorService.

Covers chained dependencies where one dependency provides keys for another.
See ADR-026 for architectural context.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pyarrow as pa
import pytest

from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.dependency_key_resolvers import (
    create_chained_key_resolver,
    create_seed_key_resolver,
)
from bioetl.application.composite.dependency_progress_tracker import (
    DependencyProgressService,
)
from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultService,
)
from bioetl.domain.composite.config import DependencyConfig
from bioetl.domain.composite.result import DependencyResult, DependencyStatus
from tests.helpers.clock import FixedClock

pytestmark = pytest.mark.unit

if TYPE_CHECKING:
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort


def _make_coordinator(
    logger: LoggerPort,
    delta_reader: DeltaReaderPort | None = None,
) -> DependencyCoordinatorService:
    """Build coordinator with explicit resolver injection for tests."""
    return DependencyCoordinatorService(
        logger=logger,
        seed_key_resolver=create_seed_key_resolver(logger),
        chained_key_resolver=create_chained_key_resolver(logger),
        progress_service=DependencyProgressService(logger),
        result_service=DependencyResultService(logger),
        delta_reader=delta_reader,
        clock=FixedClock(datetime(2026, 4, 28, 12, 0, tzinfo=UTC)),
    )


@pytest.fixture
def mock_logger() -> LoggerPort:
    """Create mock logger."""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_delta_reader() -> DeltaReaderPort:
    """Create mock delta reader."""
    reader = MagicMock()
    reader.read_table = AsyncMock()
    return reader


@pytest.fixture
def seed_keys() -> pl.DataFrame:
    """Create seed keys DataFrame."""
    return pl.DataFrame(
        {
            "target_id": ["CHEMBL1", "CHEMBL2", "CHEMBL3"],
            "component_id": [100, 200, 300],
        }
    )


class TestGetEffectiveKeys:
    """Tests for _get_effective_keys method."""

    async def test_standard_dependency_uses_seed_keys(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        """Standard dependency (uses_seed_keys=True) should return seed keys."""
        coordinator = _make_coordinator(mock_logger, mock_delta_reader)

        config = DependencyConfig(
            pipeline="chembl_target_component",
            join_keys=("component_id",),
            key_source=None,  # uses seed keys
        )

        result = await coordinator._get_effective_keys(
            dependency=config,
            seed_keys=seed_keys,
            dep_config_lookup={config.pipeline: config},
        )

        assert result is seed_keys
        mock_delta_reader.read_table.assert_not_called()

    async def test_chained_dependency_reads_from_silver(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        """Chained dependency should read keys from source Silver table."""
        # Setup mock to return PyArrow table
        source_data = pa.table(
            {
                "component_id": [100, 200],
                "protein_classification_id": [1, 2],
            }
        )
        mock_delta_reader.read_table.return_value = source_data

        coordinator = _make_coordinator(mock_logger, mock_delta_reader)

        source_config = DependencyConfig(
            pipeline="chembl_target_component",
            join_keys=("component_id",),
            silver_table="silver/chembl/target_component",
        )

        chained_config = DependencyConfig(
            pipeline="chembl_protein_class",
            join_keys=("protein_classification_id",),
            key_source="chembl_target_component",  # chained!
            silver_table="silver/chembl/protein_class",
        )

        result = await coordinator._get_effective_keys(
            dependency=chained_config,
            seed_keys=seed_keys,
            dep_config_lookup={
                source_config.pipeline: source_config,
                chained_config.pipeline: chained_config,
            },
        )

        # Should have read from Silver
        mock_delta_reader.read_table.assert_called_once_with(
            "silver/chembl/target_component"
        )

        # Result should be Polars DataFrame
        assert isinstance(result, pl.DataFrame)
        assert "protein_classification_id" in result.columns
        assert len(result) == 2

    async def test_chained_dependency_validates_join_key_column(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        """Chained dependency should raise if join key column missing."""
        # Source table missing the required column
        source_data = pa.table(
            {
                "component_id": [100, 200],
                "wrong_column": ["a", "b"],
            }
        )
        mock_delta_reader.read_table.return_value = source_data

        coordinator = _make_coordinator(mock_logger, mock_delta_reader)

        source_config = DependencyConfig(
            pipeline="chembl_target_component",
            join_keys=("component_id",),
            silver_table="silver/chembl/target_component",
        )

        chained_config = DependencyConfig(
            pipeline="chembl_protein_class",
            join_keys=("protein_classification_id",),  # Not in source!
            key_source="chembl_target_component",
            silver_table="silver/chembl/protein_class",
        )

        with pytest.raises(ValueError, match=r"protein_classification_id.*not found"):
            await coordinator._get_effective_keys(
                dependency=chained_config,
                seed_keys=seed_keys,
                dep_config_lookup={
                    source_config.pipeline: source_config,
                    chained_config.pipeline: chained_config,
                },
            )

    async def test_chained_dependency_requires_delta_reader(
        self,
        mock_logger: LoggerPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        """Chained dependency should raise if no delta_reader."""
        coordinator = _make_coordinator(mock_logger, None)  # No reader!

        chained_config = DependencyConfig(
            pipeline="chembl_protein_class",
            join_keys=("protein_classification_id",),
            key_source="chembl_target_component",
            silver_table="silver/chembl/protein_class",
        )

        with pytest.raises(ValueError, match="requires delta_reader"):
            await coordinator._get_effective_keys(
                dependency=chained_config,
                seed_keys=seed_keys,
                dep_config_lookup={chained_config.pipeline: chained_config},
            )

    async def test_chained_dependency_requires_valid_key_source(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        """Chained dependency should raise if key_source not found."""
        coordinator = _make_coordinator(mock_logger, mock_delta_reader)

        chained_config = DependencyConfig(
            pipeline="chembl_protein_class",
            join_keys=("protein_classification_id",),
            key_source="nonexistent_pipeline",  # Invalid!
            silver_table="silver/chembl/protein_class",
        )

        with pytest.raises(ValueError, match="unknown key_source"):
            await coordinator._get_effective_keys(
                dependency=chained_config,
                seed_keys=seed_keys,
                dep_config_lookup={chained_config.pipeline: chained_config},
            )

    async def test_chained_dependency_fallback_on_file_not_found(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        """Chained dependency should fallback to seed if table not found (first run)."""
        mock_delta_reader.read_table.side_effect = FileNotFoundError("Table not found")

        coordinator = _make_coordinator(mock_logger, mock_delta_reader)

        source_config = DependencyConfig(
            pipeline="chembl_target_component",
            join_keys=("component_id",),
            silver_table="silver/chembl/target_component",
        )

        chained_config = DependencyConfig(
            pipeline="chembl_protein_class",
            join_keys=("protein_classification_id",),
            key_source="chembl_target_component",
            silver_table="silver/chembl/protein_class",
        )

        result = await coordinator._get_effective_keys(
            dependency=chained_config,
            seed_keys=seed_keys,
            dep_config_lookup={
                source_config.pipeline: source_config,
                chained_config.pipeline: chained_config,
            },
        )

        # Should fallback to seed keys
        assert result is seed_keys
        mock_logger.warning.assert_called()

    async def test_chained_dependency_empty_source_fallback_to_seed(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        """Chained dependency should fallback to seed if source table empty."""
        # Empty table
        mock_delta_reader.read_table.return_value = pa.table(
            {
                "protein_classification_id": pa.array([], type=pa.int64()),
            }
        )

        coordinator = _make_coordinator(mock_logger, mock_delta_reader)

        source_config = DependencyConfig(
            pipeline="chembl_target_component",
            join_keys=("component_id",),
            silver_table="silver/chembl/target_component",
        )

        chained_config = DependencyConfig(
            pipeline="chembl_protein_class",
            join_keys=("protein_classification_id",),
            key_source="chembl_target_component",
            silver_table="silver/chembl/protein_class",
        )

        result = await coordinator._get_effective_keys(
            dependency=chained_config,
            seed_keys=seed_keys,
            dep_config_lookup={
                source_config.pipeline: source_config,
                chained_config.pipeline: chained_config,
            },
        )

        # Should fallback to seed keys
        assert result is seed_keys
        mock_logger.warning.assert_called()

    async def test_chained_dependency_raises_on_other_errors(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        """Chained dependency should raise on unexpected errors (not silent fallback)."""
        mock_delta_reader.read_table.side_effect = RuntimeError("Unexpected error")

        coordinator = _make_coordinator(mock_logger, mock_delta_reader)

        source_config = DependencyConfig(
            pipeline="chembl_target_component",
            join_keys=("component_id",),
            silver_table="silver/chembl/target_component",
        )

        chained_config = DependencyConfig(
            pipeline="chembl_protein_class",
            join_keys=("protein_classification_id",),
            key_source="chembl_target_component",
            silver_table="silver/chembl/protein_class",
        )

        with pytest.raises(ValueError, match="Failed to read keys"):
            await coordinator._get_effective_keys(
                dependency=chained_config,
                seed_keys=seed_keys,
                dep_config_lookup={
                    source_config.pipeline: source_config,
                    chained_config.pipeline: chained_config,
                },
            )

        mock_logger.error.assert_called()


@pytest.mark.unit
class TestDependencyExecution:
    """Tests for dependency execution and orchestration paths."""

    @pytest.mark.asyncio
    async def test_run_dependencies_returns_empty_when_no_dependencies(
        self,
        mock_logger: LoggerPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        coordinator = _make_coordinator(mock_logger)

        result = await coordinator.run_dependencies(
            keys=seed_keys,
            dependencies=[],
            completed=frozenset(),
            runner_factory=lambda _name, _keys: MagicMock(),
        )

        assert result == {}
        mock_logger.debug.assert_called()

    @pytest.mark.asyncio
    async def test_run_dependencies_marks_completed_dependency_as_skipped(
        self,
        mock_logger: LoggerPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        coordinator = _make_coordinator(mock_logger)
        dependency = DependencyConfig(
            pipeline="chembl_publication_term",
            join_keys=("document_chembl_id",),
            required=False,
        )

        result = await coordinator.run_dependencies(
            keys=seed_keys,
            dependencies=[dependency],
            completed=frozenset({dependency.pipeline}),
            runner_factory=lambda _name, _keys: MagicMock(),
        )

        assert dependency.pipeline in result
        assert result[dependency.pipeline].status == DependencyStatus.SKIPPED
        assert "Already completed" in (result[dependency.pipeline].error_message or "")

    @pytest.mark.asyncio
    async def test_run_dependencies_stops_after_required_failure(
        self,
        mock_logger: LoggerPort,
        seed_keys: pl.DataFrame,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        coordinator = _make_coordinator(mock_logger)
        dep_a = DependencyConfig(
            pipeline="chembl_publication_term",
            join_keys=("document_chembl_id",),
            required=True,
        )
        dep_b = DependencyConfig(
            pipeline="chembl_target_component",
            join_keys=("target_chembl_id",),
            required=False,
        )

        get_keys_mock = AsyncMock(return_value=seed_keys)
        run_single_mock = AsyncMock(
            side_effect=[
                DependencyResult.failed(dep_a.pipeline, "required failed"),
                DependencyResult.success(
                    dep_b.pipeline, records_extracted=1, records_silver=1
                ),
            ]
        )
        monkeypatch.setattr(coordinator, "_get_effective_keys", get_keys_mock)
        monkeypatch.setattr(coordinator, "_run_single_dependency", run_single_mock)

        result = await coordinator.run_dependencies(
            keys=seed_keys,
            dependencies=[dep_a, dep_b],
            completed=frozenset(),
            runner_factory=lambda _name, _keys: MagicMock(),
        )

        assert dep_a.pipeline in result
        assert dep_b.pipeline not in result
        assert run_single_mock.await_count == 1
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_run_single_dependency_success_uses_runner_execution_metrics(
        self,
        mock_logger: LoggerPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        coordinator = _make_coordinator(mock_logger)
        dependency = DependencyConfig(
            pipeline="chembl_publication_term",
            join_keys=("document_chembl_id",),
            required=False,
            timeout_seconds=30,
        )

        runner = MagicMock()
        runner.run = AsyncMock(return_value=None)
        runner.execution_metrics = {
            "records_fetched": 7,
            "records_silver": 5,
        }

        result = await coordinator._run_single_dependency(
            dependency=dependency,
            keys=seed_keys,
            runner_factory=lambda _pipeline, _keys: runner,
        )

        assert result.status == DependencyStatus.SUCCESS
        assert result.records_extracted == 7
        assert result.records_silver == 5
        assert result.duration_seconds >= 0.0
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds == pytest.approx(
            (result.completed_at - result.started_at).total_seconds(),
            abs=1e-6,
        )

    @pytest.mark.asyncio
    async def test_run_single_dependency_timeout_returns_timeout_result(
        self,
        mock_logger: LoggerPort,
        seed_keys: pl.DataFrame,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        coordinator = _make_coordinator(mock_logger)
        dependency = DependencyConfig(
            pipeline="chembl_publication_term",
            join_keys=("document_chembl_id",),
            required=False,
            timeout_seconds=5,
        )

        class _ImmediateTimeout:
            async def __aenter__(self) -> None:
                await asyncio.sleep(0)
                raise TimeoutError

            async def __aexit__(self, *_args: object) -> bool:
                await asyncio.sleep(0)
                return False

        monkeypatch.setattr(
            "bioetl.application.composite.helpers.dependency_coordinator_execution.asyncio.timeout",
            lambda _seconds: _ImmediateTimeout(),
        )

        result = await coordinator._run_single_dependency(
            dependency=dependency,
            keys=seed_keys,
            runner_factory=lambda _pipeline, _keys: MagicMock(),
        )

        assert result.status == DependencyStatus.TIMEOUT
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds == pytest.approx(
            (result.completed_at - result.started_at).total_seconds(),
            abs=1e-6,
        )
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_run_single_dependency_optional_failure_returns_failed(
        self,
        mock_logger: LoggerPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        coordinator = _make_coordinator(mock_logger)
        dependency = DependencyConfig(
            pipeline="chembl_publication_term",
            join_keys=("document_chembl_id",),
            required=False,
        )

        runner = MagicMock()
        runner.run = AsyncMock(side_effect=RuntimeError("boom"))

        result = await coordinator._run_single_dependency(
            dependency=dependency,
            keys=seed_keys,
            runner_factory=lambda _pipeline, _keys: runner,
        )

        assert result.status == DependencyStatus.FAILED
        assert "boom" in (result.error_message or "")
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds == pytest.approx(
            (result.completed_at - result.started_at).total_seconds(),
            abs=1e-6,
        )
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_run_single_dependency_required_failure_returns_failed_with_error_log(
        self,
        mock_logger: LoggerPort,
        seed_keys: pl.DataFrame,
    ) -> None:
        coordinator = _make_coordinator(mock_logger)
        dependency = DependencyConfig(
            pipeline="chembl_publication_term",
            join_keys=("document_chembl_id",),
            required=True,
        )

        runner = MagicMock()
        runner.run = AsyncMock(side_effect=RuntimeError("required boom"))

        result = await coordinator._run_single_dependency(
            dependency=dependency,
            keys=seed_keys,
            runner_factory=lambda _pipeline, _keys: runner,
        )

        assert result.status == DependencyStatus.FAILED
        assert "required boom" in (result.error_message or "")
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds == pytest.approx(
            (result.completed_at - result.started_at).total_seconds(),
            abs=1e-6,
        )
        mock_logger.error.assert_called()
