"""Tests for DependencyCoordinator.

Covers chained dependencies where one dependency provides keys for another.
See ADR-026 for architectural context.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pyarrow as pa
import pytest

from bioetl.application.composite.dependency_coordinator import DependencyCoordinator
from bioetl.domain.composite.config import DependencyConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort


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
        coordinator = DependencyCoordinator(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

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

        coordinator = DependencyCoordinator(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

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

        coordinator = DependencyCoordinator(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

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
        coordinator = DependencyCoordinator(
            logger=mock_logger,
            delta_reader=None,  # No reader!
        )

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
        coordinator = DependencyCoordinator(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

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

        coordinator = DependencyCoordinator(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

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

        coordinator = DependencyCoordinator(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

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

        coordinator = DependencyCoordinator(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

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
