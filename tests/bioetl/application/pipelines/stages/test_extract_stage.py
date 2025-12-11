"""Unit tests for ExtractStage."""

from unittest.mock import MagicMock

import pandas as pd
from pydantic import ValidationError
import pytest

from bioetl.application.mappers.chembl import ChemblRecordMapper
from bioetl.application.mappers.contracts import RecordMapperABC
from bioetl.application.pipelines.stages.extract import ExtractStage
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.record_source import SourceRecordModel
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_extraction_service() -> MagicMock:
    """Create a mock extraction service."""
    return MagicMock(spec=ExtractionServiceABC)


@pytest.fixture
def mock_mapper() -> MagicMock:
    """Create a mock record mapper."""
    return MagicMock(spec=RecordMapperABC)


@pytest.fixture
def chembl_mapper() -> ChemblRecordMapper:
    """Create a real ChemblRecordMapper."""
    return ChemblRecordMapper(registry=get_chembl_model_registry())


# =============================================================================
# Test ExtractStage Initialization
# =============================================================================


class TestExtractStageInit:
    """Tests for ExtractStage initialization."""

    def test_init_with_mapper(
        self, mock_extraction_service: MagicMock, mock_mapper: MagicMock
    ) -> None:
        """ExtractStage initializes with extraction service and mapper."""
        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=mock_mapper,
        )

        assert stage.extraction_service is mock_extraction_service
        assert stage.record_mapper is mock_mapper

    def test_init_without_mapper(self, mock_extraction_service: MagicMock) -> None:
        """ExtractStage initializes without mapper (raw mode)."""
        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        assert stage.extraction_service is mock_extraction_service
        assert stage.record_mapper is None


# =============================================================================
# Test ExtractStage.extract() with Mapper
# =============================================================================


class TestExtractStageWithMapper:
    """Tests for ExtractStage.extract() with record mapping."""

    def test_extract_with_mapper_validates_records(
        self, mock_extraction_service: MagicMock, chembl_mapper: ChemblRecordMapper
    ) -> None:
        """Records are validated through mapper before DataFrame conversion."""
        raw_batch = [
            {"activity_id": 1, "standard_flag": True, "standard_value": 1.0},
            {"activity_id": 2, "standard_flag": False},
        ]
        mock_extraction_service.iter_extract.return_value = [raw_batch]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=chembl_mapper,
        )

        dfs = list(stage.extract("activity"))

        assert len(dfs) == 1
        assert len(dfs[0]) == 2
        # Verify activity_id is converted to string by model
        assert dfs[0]["activity_id"].tolist() == ["1", "2"]
        assert dfs[0]["standard_flag"].tolist() == [True, False]

    def test_extract_with_mapper_multiple_batches(
        self, mock_extraction_service: MagicMock, chembl_mapper: ChemblRecordMapper
    ) -> None:
        """Multiple batches are each converted to separate DataFrames."""
        batch1 = [{"activity_id": 1, "standard_flag": True, "standard_value": 1.0}]
        batch2 = [{"activity_id": 2, "standard_flag": False}]
        mock_extraction_service.iter_extract.return_value = [batch1, batch2]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=chembl_mapper,
        )

        dfs = list(stage.extract("activity"))

        assert len(dfs) == 2
        assert len(dfs[0]) == 1
        assert len(dfs[1]) == 1
        assert dfs[0]["activity_id"].iloc[0] == "1"
        assert dfs[1]["activity_id"].iloc[0] == "2"

    def test_extract_with_mapper_raises_validation_error(
        self, mock_extraction_service: MagicMock, chembl_mapper: ChemblRecordMapper
    ) -> None:
        """ValidationError is raised for invalid records."""
        # Missing required field 'standard_flag'
        invalid_batch = [{"activity_id": 1}]
        mock_extraction_service.iter_extract.return_value = [invalid_batch]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=chembl_mapper,
        )

        with pytest.raises(ValidationError):
            list(stage.extract("activity"))

    def test_extract_with_mapper_raises_for_unknown_entity(
        self, mock_extraction_service: MagicMock, chembl_mapper: ChemblRecordMapper
    ) -> None:
        """ValueError is raised for unknown entity type."""
        mock_extraction_service.iter_extract.return_value = [[{"id": 1}]]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=chembl_mapper,
        )

        with pytest.raises(ValueError, match="Unknown entity type"):
            list(stage.extract("unknown_entity"))

    def test_extract_passes_filters_to_service(
        self, mock_extraction_service: MagicMock, mock_mapper: MagicMock
    ) -> None:
        """Filters are passed to extraction service (limit handled internally)."""
        mock_extraction_service.iter_extract.return_value = []

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=mock_mapper,
        )

        # limit is handled internally by ExtractStage, not passed to iter_extract
        list(stage.extract("activity", target_chembl_id="CHEMBL25", limit=100))

        mock_extraction_service.iter_extract.assert_called_once_with(
            "activity",
            chunk_size=None,
            target_chembl_id="CHEMBL25",
        )

    def test_extract_passes_chunk_size_to_service(
        self, mock_extraction_service: MagicMock, mock_mapper: MagicMock
    ) -> None:
        """chunk_size parameter is passed to extraction service."""
        mock_extraction_service.iter_extract.return_value = []

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=mock_mapper,
        )

        list(stage.extract("activity", chunk_size=500))

        mock_extraction_service.iter_extract.assert_called_once_with(
            "activity",
            chunk_size=500,
        )


# =============================================================================
# Test ExtractStage.extract() without Mapper (Raw Mode)
# =============================================================================


class TestExtractStageRawMode:
    """Tests for ExtractStage.extract() without mapper (raw mode)."""

    def test_extract_without_mapper_converts_directly(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """Raw dicts are converted directly to DataFrame without validation."""
        raw_batch = [
            {"id": 1, "name": "Test 1"},
            {"id": 2, "name": "Test 2"},
        ]
        mock_extraction_service.iter_extract.return_value = [raw_batch]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        dfs = list(stage.extract("activity"))

        assert len(dfs) == 1
        assert len(dfs[0]) == 2
        # Data preserved as-is (no string conversion)
        assert dfs[0]["id"].tolist() == [1, 2]
        assert dfs[0]["name"].tolist() == ["Test 1", "Test 2"]

    def test_extract_without_mapper_accepts_any_fields(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """Raw mode accepts any field structure without validation."""
        raw_batch = [
            {"custom_field": "value", "nested": {"a": 1}},
        ]
        mock_extraction_service.iter_extract.return_value = [raw_batch]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        dfs = list(stage.extract("any_entity"))

        assert len(dfs) == 1
        assert "custom_field" in dfs[0].columns
        assert "nested" in dfs[0].columns


# =============================================================================
# Test ExtractStage.extract() Edge Cases
# =============================================================================


class TestExtractStageEdgeCases:
    """Tests for ExtractStage edge cases."""

    def test_extract_skips_empty_batches(
        self, mock_extraction_service: MagicMock, mock_mapper: MagicMock
    ) -> None:
        """Empty batches are skipped."""
        mock_extraction_service.iter_extract.return_value = [[], [{"id": 1}], []]
        mock_record = MagicMock(spec=SourceRecordModel)
        mock_record.model_dump.return_value = {"id": 1}
        mock_mapper.map_records.return_value = [mock_record]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=mock_mapper,
        )

        dfs = list(stage.extract("activity"))

        # Only non-empty batch produces a DataFrame
        assert len(dfs) == 1
        assert len(dfs[0]) == 1

    def test_extract_handles_no_batches(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """No batches returns empty iterator."""
        mock_extraction_service.iter_extract.return_value = []

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        dfs = list(stage.extract("activity"))

        assert dfs == []


# =============================================================================
# Test ExtractStage.extract_all()
# =============================================================================


class TestExtractStageExtractAll:
    """Tests for ExtractStage.extract_all() method."""

    def test_extract_all_with_mapper(
        self, mock_extraction_service: MagicMock, chembl_mapper: ChemblRecordMapper
    ) -> None:
        """extract_all with mapper validates all records."""
        all_records = [
            {"activity_id": 1, "standard_flag": True, "standard_value": 1.0},
            {"activity_id": 2, "standard_flag": False},
        ]
        mock_extraction_service.extract_all.return_value = all_records

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=chembl_mapper,
        )

        df = stage.extract_all("activity")

        assert len(df) == 2
        assert df["activity_id"].tolist() == ["1", "2"]

    def test_extract_all_without_mapper(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """extract_all without mapper converts directly."""
        all_records = [
            {"id": 1, "name": "Test"},
        ]
        mock_extraction_service.extract_all.return_value = all_records

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        df = stage.extract_all("activity")

        assert len(df) == 1
        assert df["id"].iloc[0] == 1

    def test_extract_all_empty_returns_empty_dataframe(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """extract_all with no records returns empty DataFrame."""
        mock_extraction_service.extract_all.return_value = []

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        df = stage.extract_all("activity")

        assert isinstance(df, pd.DataFrame)
        assert df.empty

    def test_extract_all_passes_filters(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """extract_all passes filters to extraction service."""
        mock_extraction_service.extract_all.return_value = []

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        stage.extract_all("activity", target_chembl_id="CHEMBL25")

        mock_extraction_service.extract_all.assert_called_once_with(
            "activity",
            target_chembl_id="CHEMBL25",
        )


# =============================================================================
# Test Integration: Extract → Map → DataFrame
# =============================================================================


class TestExtractStageIntegration:
    """Integration tests for ExtractStage with real mapper."""

    def test_full_flow_activity_extraction(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """Full extraction flow: service → mapper → DataFrame."""
        # Simulate real ChEMBL activity records
        raw_records = [
            {
                "activity_id": 12345,
                "standard_flag": True,
                "assay_chembl_id": "CHEMBL1217643",
                "molecule_chembl_id": "CHEMBL25",
                "standard_type": "IC50",
                "standard_value": 50.0,
                "standard_units": "nM",
            },
            {
                "activity_id": 12346,
                "standard_flag": False,
                "assay_chembl_id": "CHEMBL1217643",
                "molecule_chembl_id": "CHEMBL26",
                "standard_type": "Ki",
                "standard_value": 100.0,
                "standard_units": "nM",
            },
        ]
        mock_extraction_service.iter_extract.return_value = [raw_records]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=ChemblRecordMapper(registry=get_chembl_model_registry()),
        )

        dfs = list(stage.extract("activity"))

        assert len(dfs) == 1
        df = dfs[0]
        assert len(df) == 2

        # Verify domain model transformations applied
        assert df["activity_id"].dtype == object  # string type
        assert df["activity_id"].tolist() == ["12345", "12346"]
        assert df["standard_flag"].tolist() == [True, False]
        assert df["standard_type"].tolist() == ["IC50", "Ki"]

    def test_full_flow_molecule_extraction(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """Full extraction flow for molecule entity."""
        raw_records = [
            {
                "molecule_chembl_id": "CHEMBL25",
                "pref_name": "ASPIRIN",
                "molecule_type": "Small molecule",
                "max_phase": 4,
            },
        ]
        mock_extraction_service.iter_extract.return_value = [raw_records]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=ChemblRecordMapper(registry=get_chembl_model_registry()),
        )

        dfs = list(stage.extract("molecule"))

        assert len(dfs) == 1
        df = dfs[0]
        assert df["molecule_chembl_id"].iloc[0] == "CHEMBL25"
        assert df["pref_name"].iloc[0] == "ASPIRIN"
        assert df["max_phase"].iloc[0] == 4

    def test_multiple_entities_supported(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """ExtractStage supports all ChEMBL entity types."""
        mapper = ChemblRecordMapper(registry=get_chembl_model_registry())

        test_cases = [
            ("activity", {"activity_id": 1, "standard_flag": True, "standard_value": 1.0}),
            ("molecule", {"molecule_chembl_id": "CHEMBL1"}),
            ("target", {"target_chembl_id": "CHEMBL1"}),
            ("assay", {"assay_chembl_id": "CHEMBL1"}),
            ("document", {"document_chembl_id": "CHEMBL1"}),
        ]

        for entity, record in test_cases:
            mock_extraction_service.iter_extract.return_value = [[record]]

            stage = ExtractStage(
                extraction_service=mock_extraction_service,
                record_mapper=mapper,
            )

            dfs = list(stage.extract(entity))
            assert len(dfs) == 1, f"Failed for entity: {entity}"


# =============================================================================
# Test Properties
# =============================================================================


class TestExtractStageProperties:
    """Tests for ExtractStage properties."""

    def test_extraction_service_property(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """extraction_service property returns the service."""
        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        assert stage.extraction_service is mock_extraction_service

    def test_record_mapper_property_with_mapper(
        self, mock_extraction_service: MagicMock, mock_mapper: MagicMock
    ) -> None:
        """record_mapper property returns the mapper when set."""
        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=mock_mapper,
        )

        assert stage.record_mapper is mock_mapper

    def test_record_mapper_property_without_mapper(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """record_mapper property returns None when not set."""
        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        assert stage.record_mapper is None

    def test_entity_property_when_set(self, mock_extraction_service: MagicMock) -> None:
        """entity property returns the pre-configured entity."""
        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
            entity="activity",
        )

        assert stage.entity == "activity"

    def test_entity_property_when_not_set(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """entity property returns None when not set."""
        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        assert stage.entity is None


# =============================================================================
# Test Pre-configured Entity
# =============================================================================


class TestExtractStagePreConfiguredEntity:
    """Tests for ExtractStage with pre-configured entity."""

    def test_extract_uses_preconfigured_entity(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """extract() uses pre-configured entity when not provided."""
        raw_batch = [{"id": 1, "name": "Test"}]
        mock_extraction_service.iter_extract.return_value = [raw_batch]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
            entity="activity",
        )

        dfs = list(stage.extract())  # No entity argument

        mock_extraction_service.iter_extract.assert_called_once_with(
            "activity",
            chunk_size=None,
        )
        assert len(dfs) == 1

    def test_extract_argument_overrides_preconfigured_entity(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """Entity argument to extract() overrides pre-configured entity."""
        mock_extraction_service.iter_extract.return_value = []

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
            entity="activity",
        )

        list(stage.extract("molecule"))  # Override with different entity

        mock_extraction_service.iter_extract.assert_called_once_with(
            "molecule",
            chunk_size=None,
        )

    def test_extract_raises_when_no_entity_configured(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """extract() raises ValueError when entity not provided and not configured."""
        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        with pytest.raises(ValueError, match="Entity must be provided"):
            list(stage.extract())

    def test_extract_all_uses_preconfigured_entity(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """extract_all() uses pre-configured entity when not provided."""
        mock_extraction_service.extract_all.return_value = []

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
            entity="activity",
        )

        stage.extract_all()  # No entity argument

        mock_extraction_service.extract_all.assert_called_once_with("activity")


# =============================================================================
# Test Limit Handling
# =============================================================================


class TestExtractStageLimitHandling:
    """Tests for ExtractStage limit functionality."""

    def test_limit_restricts_total_records(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """limit parameter restricts total number of records returned."""
        batch1 = [{"id": 1}, {"id": 2}, {"id": 3}]
        batch2 = [{"id": 4}, {"id": 5}]
        mock_extraction_service.iter_extract.return_value = [batch1, batch2]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        dfs = list(stage.extract("activity", limit=4))
        total_records = sum(len(df) for df in dfs)

        assert total_records == 4

    def test_limit_stops_iteration_early(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """limit parameter stops iteration before processing all batches."""
        batch1 = [{"id": i} for i in range(5)]  # 5 records
        batch2 = [{"id": i} for i in range(5, 10)]  # Should not be fully processed
        mock_extraction_service.iter_extract.return_value = [batch1, batch2]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        dfs = list(stage.extract("activity", limit=7))
        total_records = sum(len(df) for df in dfs)

        assert total_records == 7  # Only 7 records despite 10 available

    def test_limit_with_single_batch_larger_than_limit(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """limit works correctly when first batch exceeds limit."""
        large_batch = [{"id": i} for i in range(100)]
        mock_extraction_service.iter_extract.return_value = [large_batch]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        dfs = list(stage.extract("activity", limit=10))

        assert len(dfs) == 1
        assert len(dfs[0]) == 10

    def test_no_limit_returns_all_records(
        self, mock_extraction_service: MagicMock
    ) -> None:
        """Without limit, all records are returned."""
        batch1 = [{"id": 1}, {"id": 2}]
        batch2 = [{"id": 3}, {"id": 4}]
        mock_extraction_service.iter_extract.return_value = [batch1, batch2]

        stage = ExtractStage(
            extraction_service=mock_extraction_service,
            record_mapper=None,
        )

        dfs = list(stage.extract("activity"))
        total_records = sum(len(df) for df in dfs)

        assert total_records == 4
