"""Unit tests for the LineageTracker class."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from bioetl.infrastructure.observability.lineage import (
    BatchLineage,
    LineageRecord,
    LineageTracker,
)


@pytest.mark.unit
class TestLineageRecord:
    """Tests for LineageRecord dataclass."""

    def test_to_dict(self):
        """Test LineageRecord.to_dict conversion."""
        ts = datetime.now(UTC)
        record = LineageRecord(
            lineage_id="line-001",
            pipeline_name="test_pipeline",
            run_id="run-001",
            source_layer="bronze",
            target_layer="silver",
            source_batch_id="batch-001",
            entity_ids=["entity1", "entity2"],
            transformation="normalize",
            record_count=100,
            success_count=95,
            failure_count=5,
            metadata={"key": "value"},
            timestamp=ts,
        )

        result = record.to_dict()

        assert result["lineage_id"] == "line-001"
        assert result["pipeline_name"] == "test_pipeline"
        assert result["entity_ids"] == ["entity1", "entity2"]
        assert result["timestamp"] == ts.isoformat()

    def test_immutability(self):
        """Test that LineageRecord is immutable."""
        record = LineageRecord(
            lineage_id="line-001",
            pipeline_name="test",
            run_id="run-001",
            source_layer="bronze",
            target_layer="silver",
            source_batch_id="batch-001",
            entity_ids=[],
            transformation="test",
            record_count=0,
            success_count=0,
            failure_count=0,
            metadata={},
            timestamp=datetime.now(UTC),
        )

        with pytest.raises(AttributeError):
            record.lineage_id = "new-id"


@pytest.mark.unit
class TestBatchLineage:
    """Tests for BatchLineage dataclass."""

    def test_to_dict(self):
        """Test BatchLineage.to_dict conversion."""
        ts = datetime.now(UTC)
        batch = BatchLineage(
            batch_id="batch-001",
            pipeline_name="chembl_activity",
            run_id="run-001",
            provider="chembl",
            entity_type="activity",
            layer="bronze",
            record_count=1000,
            file_path="s3://bucket/path",
            watermark="2025-01-01",
            metadata={"source": "api"},
            timestamp=ts,
        )

        result = batch.to_dict()

        assert result["batch_id"] == "batch-001"
        assert result["provider"] == "chembl"
        assert result["watermark"] == "2025-01-01"
        assert result["timestamp"] == ts.isoformat()

    def test_to_dict_with_none_watermark(self):
        """Test BatchLineage.to_dict with None watermark."""
        batch = BatchLineage(
            batch_id="batch-001",
            pipeline_name="test",
            run_id="run-001",
            provider="test",
            entity_type="test",
            layer="bronze",
            record_count=100,
            file_path="path",
            watermark=None,
            metadata={},
            timestamp=datetime.now(UTC),
        )

        result = batch.to_dict()

        assert result["watermark"] is None


@pytest.fixture
def temp_delta_path():
    """Create a temporary directory for Delta tables."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def lineage_tracker(temp_delta_path):
    """Create a LineageTracker instance."""
    return LineageTracker(
        delta_path=temp_delta_path,
        pipeline_name="test_pipeline",
    )


@pytest.fixture
def mock_write_deltalake():
    """Mock write_deltalake function."""
    with patch("bioetl.infrastructure.observability.lineage.write_deltalake") as mock:
        yield mock


@pytest.fixture
def mock_delta_table():
    """Mock DeltaTable class."""
    with patch("bioetl.infrastructure.observability.lineage.DeltaTable") as mock:
        yield mock


@pytest.mark.unit
class TestLineageTrackerInit:
    """Tests for LineageTracker initialization."""

    def test_init_with_string_path(self, temp_delta_path):
        """Test initialization with string path."""
        tracker = LineageTracker(
            delta_path=str(temp_delta_path),
            pipeline_name="test",
        )
        assert tracker.delta_path == temp_delta_path
        assert tracker.pipeline_name == "test"

    def test_init_with_path_object(self, temp_delta_path):
        """Test initialization with Path object."""
        tracker = LineageTracker(
            delta_path=temp_delta_path,
            pipeline_name="test",
        )
        assert tracker.delta_path == temp_delta_path

    def test_table_paths_set_correctly(self, lineage_tracker, temp_delta_path):
        """Test that table paths are set correctly."""
        assert lineage_tracker.batch_table_path == temp_delta_path / "batch_lineage"
        assert (
            lineage_tracker.transformation_table_path
            == temp_delta_path / "transformation_lineage"
        )


@pytest.mark.unit
class TestLineageTrackerRecordBronze:
    """Tests for LineageTracker.record_bronze method."""

    def test_record_bronze_basic(self, lineage_tracker, mock_write_deltalake):
        """Test basic bronze recording."""
        lineage_tracker.record_bronze(
            batch_id="batch-001",
            run_id="run-001",
            provider="chembl",
            entity_type="activity",
            record_count=1000,
            file_path="s3://bucket/bronze/file.jsonl.zst",
        )

        mock_write_deltalake.assert_called_once()
        call_args = mock_write_deltalake.call_args
        assert "append" in str(call_args)

    def test_record_bronze_with_watermark(self, lineage_tracker, mock_write_deltalake):
        """Test bronze recording with watermark."""
        lineage_tracker.record_bronze(
            batch_id="batch-001",
            run_id="run-001",
            provider="chembl",
            entity_type="activity",
            record_count=500,
            file_path="path",
            watermark="2025-01-15T00:00:00Z",
        )

        mock_write_deltalake.assert_called_once()

    def test_record_bronze_with_metadata(self, lineage_tracker, mock_write_deltalake):
        """Test bronze recording with metadata."""
        lineage_tracker.record_bronze(
            batch_id="batch-001",
            run_id="run-001",
            provider="chembl",
            entity_type="activity",
            record_count=100,
            file_path="path",
            metadata={"source_url": "https://api.chembl.com"},
        )

        mock_write_deltalake.assert_called_once()

    def test_record_bronze_raises_on_write_error(
        self, lineage_tracker, mock_write_deltalake
    ):
        """Test that errors during write are raised."""
        mock_write_deltalake.side_effect = RuntimeError("Write failed")

        with pytest.raises(RuntimeError, match="Write failed"):
            lineage_tracker.record_bronze(
                batch_id="batch-001",
                run_id="run-001",
                provider="test",
                entity_type="test",
                record_count=100,
                file_path="path",
            )


@pytest.mark.unit
class TestLineageTrackerRecordTransformation:
    """Tests for LineageTracker.record_transformation method."""

    def test_record_transformation_basic(self, lineage_tracker, mock_write_deltalake):
        """Test basic transformation recording."""
        lineage_tracker.record_transformation(
            run_id="run-001",
            source_layer="bronze",
            target_layer="silver",
            source_batch_id="batch-001",
            entity_ids=["entity1", "entity2"],
            transformation="normalize_activity",
            record_count=100,
            success_count=95,
            failure_count=5,
        )

        mock_write_deltalake.assert_called_once()

    def test_record_transformation_with_metadata(
        self, lineage_tracker, mock_write_deltalake
    ):
        """Test transformation recording with metadata."""
        lineage_tracker.record_transformation(
            run_id="run-001",
            source_layer="silver",
            target_layer="gold",
            source_batch_id="batch-001",
            entity_ids=["entity1"],
            transformation="enrich",
            record_count=50,
            success_count=50,
            failure_count=0,
            metadata={"enrichment_source": "pubchem"},
        )

        mock_write_deltalake.assert_called_once()

    def test_record_transformation_entity_ids_joined(
        self, lineage_tracker, mock_write_deltalake
    ):
        """Test that entity_ids are joined into string."""
        lineage_tracker.record_transformation(
            run_id="run-001",
            source_layer="bronze",
            target_layer="silver",
            source_batch_id="batch-001",
            entity_ids=["e1", "e2", "e3"],
            transformation="test",
            record_count=3,
            success_count=3,
            failure_count=0,
        )

        mock_write_deltalake.assert_called_once()


@pytest.mark.unit
class TestLineageTrackerQueryBatchHistory:
    """Tests for LineageTracker.query_batch_history method."""

    def test_query_batch_history_returns_empty_on_error(
        self, lineage_tracker, mock_delta_table
    ):
        """Test query returns empty DataFrame on error."""
        mock_delta_table.side_effect = Exception("Table not found")

        result = lineage_tracker.query_batch_history()

        assert isinstance(result, pl.DataFrame)
        assert result.height == 0

    def test_query_batch_history_with_filters(self, lineage_tracker, mock_delta_table):
        """Test query with layer and provider filters."""
        mock_table = MagicMock()
        mock_df = pl.DataFrame(
            {
                "pipeline_name": ["test_pipeline", "test_pipeline"],
                "layer": ["bronze", "silver"],
                "provider": ["chembl", "chembl"],
                "timestamp": ["2025-01-01", "2025-01-02"],
            }
        )
        mock_table.to_polars.return_value = mock_df
        mock_delta_table.return_value = mock_table

        result = lineage_tracker.query_batch_history(
            layer="bronze", provider="chembl", limit=10
        )

        assert isinstance(result, pl.DataFrame)

    def test_query_batch_history_default_limit(self, lineage_tracker, mock_delta_table):
        """Test query respects default limit."""
        mock_table = MagicMock()
        mock_df = pl.DataFrame(
            {
                "pipeline_name": ["test_pipeline"] * 150,
                "layer": ["bronze"] * 150,
                "provider": ["chembl"] * 150,
                "timestamp": [f"2025-01-{i:02d}" for i in range(1, 151)],
            }
        )
        mock_table.to_polars.return_value = mock_df
        mock_delta_table.return_value = mock_table

        result = lineage_tracker.query_batch_history()

        assert result.height <= 100


@pytest.mark.unit
class TestLineageTrackerQueryTransformationHistory:
    """Tests for LineageTracker.query_transformation_history method."""

    def test_query_transformation_history_returns_empty_on_error(
        self, lineage_tracker, mock_delta_table
    ):
        """Test query returns empty DataFrame on error."""
        mock_delta_table.side_effect = Exception("Error")

        result = lineage_tracker.query_transformation_history()

        assert isinstance(result, pl.DataFrame)
        assert result.height == 0

    def test_query_transformation_history_with_filters(
        self, lineage_tracker, mock_delta_table
    ):
        """Test query with source_layer, target_layer, and transformation filters."""
        mock_table = MagicMock()
        mock_df = pl.DataFrame(
            {
                "pipeline_name": ["test_pipeline"],
                "source_layer": ["bronze"],
                "target_layer": ["silver"],
                "transformation": ["normalize"],
                "timestamp": ["2025-01-01"],
            }
        )
        mock_table.to_polars.return_value = mock_df
        mock_delta_table.return_value = mock_table

        result = lineage_tracker.query_transformation_history(
            source_layer="bronze",
            target_layer="silver",
            transformation="normalize",
            limit=50,
        )

        assert isinstance(result, pl.DataFrame)


@pytest.mark.unit
class TestLineageTrackerGetEntityLineage:
    """Tests for LineageTracker.get_entity_lineage method."""

    def test_get_entity_lineage_returns_empty_on_error(
        self, lineage_tracker, mock_delta_table
    ):
        """Test get_entity_lineage returns empty DataFrame on error."""
        mock_delta_table.side_effect = Exception("Error")

        result = lineage_tracker.get_entity_lineage(entity_id="entity-001")

        assert isinstance(result, pl.DataFrame)
        assert result.height == 0

    def test_get_entity_lineage_filters_by_entity(
        self, lineage_tracker, mock_delta_table
    ):
        """Test get_entity_lineage filters by entity_id."""
        mock_table = MagicMock()
        mock_df = pl.DataFrame(
            {
                "pipeline_name": ["test_pipeline", "test_pipeline"],
                "entity_ids": ["entity-001,entity-002", "entity-003"],
                "timestamp": ["2025-01-01", "2025-01-02"],
            }
        )
        mock_table.to_polars.return_value = mock_df
        mock_delta_table.return_value = mock_table

        result = lineage_tracker.get_entity_lineage(entity_id="entity-001")

        assert isinstance(result, pl.DataFrame)


@pytest.mark.unit
class TestLineageTrackerGetBatchStatistics:
    """Tests for LineageTracker.get_batch_statistics method."""

    def test_get_batch_statistics_returns_zeros_on_error(
        self, lineage_tracker, mock_delta_table
    ):
        """Test get_batch_statistics returns zeros on error."""
        mock_delta_table.side_effect = Exception("Error")

        result = lineage_tracker.get_batch_statistics(layer="bronze", days=7)

        assert result["total_batches"] == 0
        assert result["total_records"] == 0
        assert result["avg_batch_size"] == 0.0

    def test_get_batch_statistics_returns_zeros_for_empty(
        self, lineage_tracker, mock_delta_table
    ):
        """Test get_batch_statistics returns zeros for empty result."""
        mock_table = MagicMock()
        mock_df = pl.DataFrame(
            {
                "pipeline_name": pl.Series([], dtype=pl.Utf8),
                "layer": pl.Series([], dtype=pl.Utf8),
                "timestamp": pl.Series([], dtype=pl.Float64),
                "record_count": pl.Series([], dtype=pl.Int64),
            }
        )
        mock_table.to_polars.return_value = mock_df
        mock_delta_table.return_value = mock_table

        result = lineage_tracker.get_batch_statistics(layer="bronze")

        assert result["total_batches"] == 0

    def test_get_batch_statistics_calculates_correctly(
        self, lineage_tracker, mock_delta_table
    ):
        """Test get_batch_statistics calculates statistics correctly."""
        mock_table = MagicMock()
        # Create timestamps as floats (Unix timestamps)
        import time

        current_time = time.time()
        mock_df = pl.DataFrame(
            {
                "pipeline_name": ["test_pipeline", "test_pipeline", "test_pipeline"],
                "layer": ["bronze", "bronze", "bronze"],
                "timestamp": [
                    current_time - 100,
                    current_time - 200,
                    current_time - 300,
                ],
                "record_count": [100, 200, 300],
            }
        )
        mock_table.to_polars.return_value = mock_df
        mock_delta_table.return_value = mock_table

        result = lineage_tracker.get_batch_statistics(layer="bronze", days=7)

        assert result["total_batches"] == 3
        assert result["total_records"] == 600
        assert result["avg_batch_size"] == 200.0
