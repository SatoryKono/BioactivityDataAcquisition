"""End-to-end integration tests for pipeline execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from bioetl.application.mappers.chembl import ChemblRecordMapper
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)
from bioetl.interfaces.simple_container import SimplePipelineContainer


class TestPipelineDataFlow:
    """Test complete data flow through pipeline components."""

    @pytest.fixture(autouse=True)
    def setup_container(self) -> SimplePipelineContainer:
        """Bootstrap container for each test."""
        container = SimplePipelineContainer()
        container.bootstrap()
        yield container
        container.reset()

    @pytest.fixture
    def mock_api_responses(self) -> list[dict[str, Any]]:
        """Multiple API responses simulating pagination."""
        return [
            {
                "activities": [
                    {
                        "activity_id": 1,
                        "assay_chembl_id": "CHEMBL100",
                        "molecule_chembl_id": "CHEMBL25",
                        "standard_value": 5.0,
                        "standard_flag": True,
                        "target_chembl_id": "CHEMBL204",
                    },
                    {
                        "activity_id": 2,
                        "assay_chembl_id": "CHEMBL200",
                        "molecule_chembl_id": "CHEMBL50",
                        "standard_value": 10.0,
                        "standard_flag": True,
                        "target_chembl_id": "CHEMBL204",
                    },
                ],
                "page_meta": {
                    "total_count": 4,
                    "offset": 0,
                    "limit": 2,
                    "next": "/api/data/activity?offset=2",
                },
            },
            {
                "activities": [
                    {
                        "activity_id": 3,
                        "assay_chembl_id": "CHEMBL300",
                        "molecule_chembl_id": "CHEMBL75",
                        "standard_value": 15.0,
                        "standard_flag": False,
                        "target_chembl_id": "CHEMBL205",
                    },
                    {
                        "activity_id": 4,
                        "assay_chembl_id": "CHEMBL400",
                        "molecule_chembl_id": "CHEMBL100",
                        "standard_value": 20.0,
                        "standard_flag": True,
                        "target_chembl_id": "CHEMBL205",
                    },
                ],
                "page_meta": {
                    "total_count": 4,
                    "offset": 2,
                    "limit": 2,
                    "next": None,
                },
            },
        ]

    def test_parse_map_transform_flow(
        self, mock_api_responses: list[dict[str, Any]]
    ) -> None:
        """Test full parse → map → transform flow."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper()

        all_records = []
        for response in mock_api_responses:
            # Parse
            raw_records = parser.parse_to_records(response)
            assert isinstance(raw_records, list)
            assert all(isinstance(r, dict) for r in raw_records)

            # Map
            typed_records = mapper.map_records(raw_records, "activity")
            all_records.extend(typed_records)

        # Transform to DataFrame
        df = pd.DataFrame([r.model_dump() for r in all_records])

        assert len(df) == 4
        assert list(df["activity_id"]) == ["1", "2", "3", "4"]
        assert "assay_chembl_id" in df.columns
        assert "molecule_chembl_id" in df.columns

    def test_pagination_handling(
        self, mock_api_responses: list[dict[str, Any]]
    ) -> None:
        """Test that pagination metadata is correctly extracted."""
        parser = ChemblGenericResponseParser()

        # First page
        pagination1 = parser.extract_pagination(mock_api_responses[0])
        assert pagination1["total_count"] == 4
        assert pagination1["offset"] == 0
        assert pagination1["next"] is not None

        # Last page
        pagination2 = parser.extract_pagination(mock_api_responses[1])
        assert pagination2["offset"] == 2
        assert pagination2["next"] is None


class TestBatchProcessing:
    """Test batch processing scenarios."""

    @pytest.fixture(autouse=True)
    def setup_container(self) -> SimplePipelineContainer:
        """Bootstrap container for each test."""
        container = SimplePipelineContainer()
        container.bootstrap()
        yield container
        container.reset()

    def test_process_empty_batch(self) -> None:
        """Empty batch should be handled gracefully."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper()

        response = {"activities": [], "page_meta": {"total_count": 0}}

        raw_records = parser.parse_to_records(response)
        typed_records = mapper.map_records(raw_records, "activity")

        assert raw_records == []
        assert typed_records == []

    def test_process_large_batch(self) -> None:
        """Large batch should be processed correctly."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper()

        # Create 1000 records
        activities = [
            {
                "activity_id": i,
                "standard_flag": i % 2 == 0,
            }
            for i in range(1, 1001)
        ]
        response = {
            "activities": activities,
            "page_meta": {"total_count": 1000},
        }

        raw_records = parser.parse_to_records(response)
        typed_records = mapper.map_records(raw_records, "activity")

        assert len(raw_records) == 1000
        assert len(typed_records) == 1000
        # Verify first and last records
        assert typed_records[0].activity_id == "1"
        assert typed_records[-1].activity_id == "1000"

    def test_batch_with_null_values(self) -> None:
        """Batch with null values should be handled correctly."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper()

        response = {
            "activities": [
                {
                    "activity_id": 1,
                    "standard_flag": True,
                    "standard_value": None,
                    "standard_units": None,
                },
                {
                    "activity_id": 2,
                    "standard_flag": False,
                    "standard_value": 5.0,
                    "standard_units": "nM",
                },
            ],
        }

        raw_records = parser.parse_to_records(response)
        typed_records = mapper.map_records(raw_records, "activity")

        assert len(typed_records) == 2
        assert typed_records[0].standard_value is None
        assert typed_records[1].standard_value == 5.0


class TestMultiEntityFlow:
    """Test processing multiple entity types."""

    @pytest.fixture(autouse=True)
    def setup_container(self) -> SimplePipelineContainer:
        """Bootstrap container for each test."""
        container = SimplePipelineContainer()
        container.bootstrap()
        yield container
        container.reset()

    @pytest.fixture
    def entity_responses(self) -> dict[str, dict[str, Any]]:
        """Sample responses for different entity types."""
        return {
            "activity": {
                "activities": [
                    {"activity_id": 1, "standard_flag": True},
                    {"activity_id": 2, "standard_flag": False},
                ],
            },
            "molecule": {
                "molecules": [
                    {"molecule_chembl_id": "CHEMBL25", "pref_name": "ASPIRIN"},
                    {"molecule_chembl_id": "CHEMBL50", "pref_name": "CAFFEINE"},
                ],
            },
            "target": {
                "targets": [
                    {
                        "target_chembl_id": "CHEMBL204",
                        "pref_name": "Cyclooxygenase-2",
                        "organism": "Homo sapiens",
                    },
                ],
            },
            "assay": {
                "assays": [
                    {
                        "assay_chembl_id": "CHEMBL1217643",
                        "assay_type": "B",
                        "description": "Binding assay",
                    },
                ],
            },
            "document": {
                "documents": [
                    {
                        "document_chembl_id": "CHEMBL1125443",
                        "journal": "J. Med. Chem.",
                        "year": 2007,
                    },
                ],
            },
        }

    def test_process_all_entity_types(
        self, entity_responses: dict[str, dict[str, Any]]
    ) -> None:
        """All entity types should be processable through the same flow."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper()

        results = {}
        for entity, response in entity_responses.items():
            raw_records = parser.parse_to_records(response)
            typed_records = mapper.map_records(raw_records, entity)
            results[entity] = typed_records

        # Verify each entity type
        assert len(results["activity"]) == 2
        assert len(results["molecule"]) == 2
        assert len(results["target"]) == 1
        assert len(results["assay"]) == 1
        assert len(results["document"]) == 1

        # Verify record types
        assert results["activity"][0].activity_id == "1"
        assert results["molecule"][0].molecule_chembl_id == "CHEMBL25"
        assert results["target"][0].target_chembl_id == "CHEMBL204"
        assert results["assay"][0].assay_chembl_id == "CHEMBL1217643"
        assert results["document"][0].document_chembl_id == "CHEMBL1125443"


class TestContainerIntegration:
    """Test container-based integration scenarios."""

    def test_container_provides_consistent_components(self) -> None:
        """Container should provide the same component instances."""
        container = SimplePipelineContainer()
        container.bootstrap()

        try:
            # Get components multiple times
            parser1 = container.response_parser
            parser2 = container.response_parser
            mapper1 = container.record_mapper
            mapper2 = container.record_mapper

            # Should be the same instances (lazy singleton)
            assert parser1 is parser2
            assert mapper1 is mapper2
        finally:
            container.reset()

    def test_container_reset_creates_new_components(self) -> None:
        """Reset should create new component instances."""
        container = SimplePipelineContainer()
        container.bootstrap()
        parser_before = container.response_parser
        mapper_before = container.record_mapper

        container.reset()
        container.bootstrap()

        parser_after = container.response_parser
        mapper_after = container.record_mapper

        # Should be different instances after reset
        assert parser_before is not parser_after
        assert mapper_before is not mapper_after

        # Clean up
        container.reset()

    def test_components_work_without_bootstrap_for_lazy_init(self) -> None:
        """Parser and mapper should work without bootstrap (lazy init)."""
        container = SimplePipelineContainer()

        # These should work without bootstrap
        parser = container.response_parser
        mapper = container.record_mapper

        response = {"activities": [{"activity_id": 1, "standard_flag": True}]}

        raw_records = parser.parse_to_records(response)
        typed_records = mapper.map_records(raw_records, "activity")

        assert len(typed_records) == 1

    def test_schema_contract_requires_bootstrap(self) -> None:
        """Schema contract provider should require bootstrap."""
        container = SimplePipelineContainer()

        with pytest.raises(RuntimeError, match="not bootstrapped"):
            _ = container.schema_contract_provider


class TestDataFrameOutput:
    """Test DataFrame output generation."""

    @pytest.fixture(autouse=True)
    def setup_container(self) -> SimplePipelineContainer:
        """Bootstrap container for each test."""
        container = SimplePipelineContainer()
        container.bootstrap()
        yield container
        container.reset()

    def test_dataframe_preserves_all_fields(self) -> None:
        """DataFrame should preserve all record fields."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper()

        response = {
            "activities": [
                {
                    "activity_id": 1,
                    "assay_chembl_id": "CHEMBL123",
                    "molecule_chembl_id": "CHEMBL456",
                    "standard_value": 5.5,
                    "standard_units": "nM",
                    "standard_flag": True,
                    "standard_type": "IC50",
                    "pchembl_value": 8.26,
                },
            ],
        }

        raw_records = parser.parse_to_records(response)
        typed_records = mapper.map_records(raw_records, "activity")
        df = pd.DataFrame([r.model_dump() for r in typed_records])

        # Check key columns exist
        assert "activity_id" in df.columns
        assert "assay_chembl_id" in df.columns
        assert "molecule_chembl_id" in df.columns
        assert "standard_value" in df.columns
        assert "standard_flag" in df.columns

    def test_dataframe_dtypes_are_correct(self) -> None:
        """DataFrame should have correct data types."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper()

        response = {
            "activities": [
                {
                    "activity_id": 1,
                    "standard_value": 5.5,
                    "standard_flag": True,
                },
            ],
        }

        raw_records = parser.parse_to_records(response)
        typed_records = mapper.map_records(raw_records, "activity")
        df = pd.DataFrame([r.model_dump() for r in typed_records])

        # Check specific dtypes
        assert df["standard_flag"].dtype == bool

    def test_dataframe_export_to_csv(self, tmp_path: Path) -> None:
        """DataFrame should be exportable to CSV."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper()

        response = {
            "activities": [
                {"activity_id": 1, "standard_flag": True},
                {"activity_id": 2, "standard_flag": False},
            ],
        }

        raw_records = parser.parse_to_records(response)
        typed_records = mapper.map_records(raw_records, "activity")
        df = pd.DataFrame([r.model_dump() for r in typed_records])

        # Export to CSV
        csv_path = tmp_path / "output.csv"
        df.to_csv(csv_path, index=False)

        # Verify file exists and is readable
        assert csv_path.exists()
        df_read = pd.read_csv(csv_path)
        assert len(df_read) == 2
        assert list(df_read["activity_id"]) == [1, 2]
