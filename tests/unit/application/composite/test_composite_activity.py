"""Unit tests for composite_activity pipeline.

Tests the composite pipeline that combines ChEMBL activity data
with compound record metadata via molecule_id join key.

See ADR-026 for architectural context.
"""

from __future__ import annotations

import asyncio
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
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.domain.composite.config import DependencyConfig, SeedConfig

if TYPE_CHECKING:
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort


# =============================================================================
# Fixtures
# =============================================================================


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
def activity_seed_keys() -> pl.DataFrame:
    """Sample seed keys from activity Silver table.

    Contains 3 activities with 2 unique molecule IDs.
    - ACT_001, ACT_002: CHEMBL25 (same molecule)
    - ACT_003: CHEMBL1201585 (different molecule)
    """
    return pl.DataFrame(
        {
            "activity_id": ["ACT_001", "ACT_002", "ACT_003"],
            "molecule_id": ["CHEMBL25", "CHEMBL25", "CHEMBL1201585"],
            "assay_id": ["CHEMBL123", "CHEMBL456", "CHEMBL789"],
            "target_id": ["CHEMBL1824", "CHEMBL1824", None],
        }
    )


@pytest.fixture
def compound_record_silver_data() -> pa.Table:
    """Sample compound record Silver data.

    Contains compound records matching the molecule IDs from seed.
    """
    return pa.table(
        {
            "record_id": [1001, 1002, 1003],
            "molecule_id": ["CHEMBL25", "CHEMBL25", "CHEMBL1201585"],
            "publication_id": ["CHEMBL_DOC_1", "CHEMBL_DOC_2", "CHEMBL_DOC_3"],
            "compound_name": ["Aspirin", "ASA", "Compound X"],
            "compound_key": ["CMP001", "CMP002", "CMP003"],
            "src_id": [1, 1, 2],
        }
    )


@pytest.fixture
def seed_config() -> SeedConfig:
    """Seed configuration for activity pipeline."""
    return SeedConfig(
        pipeline="chembl_activity",
        output_keys=(
            "activity_id",
            "molecule_id",
            "assay_id",
            "target_id",
        ),
        silver_table="silver/chembl/activity",
    )


@pytest.fixture
def compound_record_dep_config() -> DependencyConfig:
    """Dependency configuration for compound_record."""
    return DependencyConfig(
        pipeline="chembl_compound_record",
        join_keys=("molecule_id",),
        filter_field="molecule_id",
        required=False,
        timeout_seconds=600,
        silver_table="silver/chembl/compound_record",
    )


# =============================================================================
# Key Extraction Tests
# =============================================================================


class TestActivityKeyExtraction:
    """Tests for extracting join keys from activity seed."""

    async def test_extract_unique_molecule_ids(
        self,
        activity_seed_keys: pl.DataFrame,
    ) -> None:
        """Should extract deduplicated molecule IDs from activities.

        Given 3 activities with 2 unique molecule IDs,
        extraction should return only 2 unique IDs.
        """
        await asyncio.sleep(0)
        unique_ids = (
            activity_seed_keys.select("molecule_id").unique().to_series().to_list()
        )

        assert len(unique_ids) == 2
        assert set(unique_ids) == {"CHEMBL25", "CHEMBL1201585"}

    async def test_activity_has_multiple_join_keys(
        self,
        activity_seed_keys: pl.DataFrame,
        seed_config: SeedConfig,
    ) -> None:
        """Activity seed config extracts multiple output keys."""
        await asyncio.sleep(0)
        assert "activity_id" in seed_config.output_keys
        assert "molecule_id" in seed_config.output_keys
        assert "assay_id" in seed_config.output_keys
        assert "target_id" in seed_config.output_keys


class TestKeyExtractorServiceWithActivity:
    """Tests for KeyExtractorService with activity data."""

    async def test_extract_keys_from_activity_silver(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
    ) -> None:
        """KeyExtractorService should extract molecule_id from activity Silver."""
        # Setup mock to return activity data
        activity_data = pa.table(
            {
                "activity_id": ["ACT_001", "ACT_002", "ACT_003"],
                "molecule_id": ["CHEMBL25", "CHEMBL25", "CHEMBL1201585"],
                "assay_id": ["CHEMBL123", "CHEMBL456", "CHEMBL789"],
            }
        )
        mock_delta_reader.read_table.return_value = activity_data

        extractor = KeyExtractorService(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

        result = await extractor.extract(
            silver_table="silver/chembl/activity",
            keys=["molecule_id"],
        )

        # Should deduplicate
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 2
        assert "molecule_id" in result.columns

    async def test_extract_normalizes_trim_and_case_before_deduplication(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
    ) -> None:
        """KeyExtractorService should canonicalize join keys before deduping."""
        mock_delta_reader.read_table.return_value = pa.table(
            {
                "doi": [" 10.1000/ABC ", "10.1000/abc"],
                "title": ["  Mixed Case Title  ", "Mixed Case Title"],
            }
        )

        extractor = KeyExtractorService(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

        result = await extractor.extract(
            silver_table="silver/chembl/publication",
            keys=["doi", "title"],
        )

        assert result.to_dict(as_series=False) == {
            "doi": ["10.1000/abc"],
            "title": ["Mixed Case Title"],
        }


# =============================================================================
# Dependency Coordinator Tests
# =============================================================================


class TestDependencyWithMoleculeFilter:
    """Tests for dependency execution with molecule_id filter."""

    async def test_dependency_receives_molecule_filter_ids(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
        activity_seed_keys: pl.DataFrame,
        compound_record_dep_config: DependencyConfig,
    ) -> None:
        """Dependency should receive unique molecule IDs as filter."""
        coordinator = DependencyCoordinatorService(
            logger=mock_logger,
            seed_key_resolver=create_seed_key_resolver(mock_logger),
            chained_key_resolver=create_chained_key_resolver(mock_logger),
            progress_service=DependencyProgressService(mock_logger),
            result_service=DependencyResultService(mock_logger),
            delta_reader=mock_delta_reader,
        )

        # Get effective keys for compound_record dependency
        result = await coordinator._get_effective_keys(
            dependency=compound_record_dep_config,
            seed_keys=activity_seed_keys,
            dep_config_lookup={
                compound_record_dep_config.pipeline: compound_record_dep_config
            },
        )

        # Should return seed keys (standard dependency, not chained)
        assert result is activity_seed_keys

    async def test_dependency_config_has_filter_field(
        self,
        compound_record_dep_config: DependencyConfig,
    ) -> None:
        """Dependency config should specify filter_field for API calls."""
        await asyncio.sleep(0)
        assert compound_record_dep_config.filter_field == "molecule_id"
        assert compound_record_dep_config.join_keys == ("molecule_id",)


# =============================================================================
# Empty/Edge Case Tests
# =============================================================================


class TestEmptySeedScenarios:
    """Tests for edge cases with empty or missing data."""

    async def test_empty_seed_raises_value_error(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
    ) -> None:
        """Empty activity seed should raise ValueError.

        KeyExtractorService raises ValueError for empty tables to prevent
        executing dependencies with no filter keys (which would fetch all data).
        """
        # Empty activity table
        mock_delta_reader.read_table.return_value = pa.table(
            {
                "activity_id": pa.array([], type=pa.string()),
                "molecule_id": pa.array([], type=pa.string()),
            }
        )

        extractor = KeyExtractorService(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

        with pytest.raises(ValueError, match="Seed Silver table is empty"):
            await extractor.extract(
                silver_table="silver/chembl/activity",
                keys=["molecule_id"],
            )

    async def test_null_molecule_ids_excluded(
        self,
        mock_logger: LoggerPort,
        mock_delta_reader: DeltaReaderPort,
    ) -> None:
        """NULL molecule_id values should be excluded from keys."""
        # Activity with some null molecule IDs
        mock_delta_reader.read_table.return_value = pa.table(
            {
                "activity_id": ["ACT_001", "ACT_002", "ACT_003"],
                "molecule_id": ["CHEMBL25", None, "CHEMBL1201585"],
            }
        )

        extractor = KeyExtractorService(
            logger=mock_logger,
            delta_reader=mock_delta_reader,
        )

        result = await extractor.extract(
            silver_table="silver/chembl/activity",
            keys=["molecule_id"],
        )

        # KeyExtractorService filters rows where ALL keys are null
        # Single null in one-key extraction should be filtered
        molecule_ids = result["molecule_id"].to_list()
        assert None not in molecule_ids
        assert len(result) == 2


# =============================================================================
# Required Flag Tests
# =============================================================================


class TestDependencyRequiredFlag:
    """Tests for required=false behavior in compound_record dependency."""

    async def test_dependency_marked_as_optional(
        self,
        compound_record_dep_config: DependencyConfig,
    ) -> None:
        """compound_record dependency should be optional (required=false)."""
        await asyncio.sleep(0)
        assert compound_record_dep_config.required is False

    async def test_optional_dependency_does_not_use_seed_keys_flag(
        self,
        compound_record_dep_config: DependencyConfig,
    ) -> None:
        """Standard dependency uses seed keys (key_source=None)."""
        await asyncio.sleep(0)
        assert compound_record_dep_config.key_source is None
        assert compound_record_dep_config.uses_seed_keys is True


# =============================================================================
# Configuration Validation Tests
# =============================================================================


class TestCompositeActivityConfig:
    """Tests for composite_activity configuration structure."""

    def test_seed_config_structure(
        self,
        seed_config: SeedConfig,
    ) -> None:
        """Seed config should have correct structure."""
        assert seed_config.pipeline == "chembl_activity"
        assert seed_config.silver_table == "silver/chembl/activity"
        assert "activity_id" in seed_config.output_keys
        assert "molecule_id" in seed_config.output_keys

    def test_dependency_config_structure(
        self,
        compound_record_dep_config: DependencyConfig,
    ) -> None:
        """Dependency config should have correct structure."""
        assert compound_record_dep_config.pipeline == "chembl_compound_record"
        assert (
            compound_record_dep_config.silver_table == "silver/chembl/compound_record"
        )
        assert compound_record_dep_config.join_keys == ("molecule_id",)
        assert compound_record_dep_config.filter_field == "molecule_id"
        assert compound_record_dep_config.timeout_seconds == 600


# =============================================================================
# Join Semantics Tests
# =============================================================================


class TestActivityCompoundRecordJoin:
    """Tests for M:N join between activity and compound_record."""

    def test_many_activities_to_many_records(self) -> None:
        """Activity → CompoundRecord is M:N relationship.

        - One activity has one molecule_id
        - One molecule can have multiple compound records
        - Join should preserve all activities (left outer)
        """
        activities = pl.DataFrame(
            {
                "activity_id": ["ACT_001", "ACT_002"],
                "molecule_id": ["CHEMBL25", "CHEMBL25"],
            }
        )

        compound_records = pl.DataFrame(
            {
                "record_id": [1001, 1002],
                "molecule_id": ["CHEMBL25", "CHEMBL25"],
                "compound_name": ["Aspirin", "ASA"],
            }
        )

        # Left outer join - activities × records where molecule matches
        result = activities.join(
            compound_records,
            on="molecule_id",
            how="left",
        )

        # 2 activities × 2 records = 4 rows (cartesian for matching molecules)
        assert len(result) == 4

    def test_missing_compound_record_preserves_activity(self) -> None:
        """Activity without matching compound_record should still appear."""
        activities = pl.DataFrame(
            {
                "activity_id": ["ACT_001", "ACT_002"],
                "molecule_id": ["CHEMBL25", "CHEMBL_UNKNOWN"],
            }
        )

        compound_records = pl.DataFrame(
            {
                "record_id": [1001],
                "molecule_id": ["CHEMBL25"],
                "compound_name": ["Aspirin"],
            }
        )

        result = activities.join(
            compound_records,
            on="molecule_id",
            how="left",
        )

        # All activities preserved
        assert len(result) == 2
        # Unknown molecule has null compound_record fields
        unknown_row = result.filter(pl.col("molecule_id") == "CHEMBL_UNKNOWN")
        assert unknown_row["compound_name"][0] is None
