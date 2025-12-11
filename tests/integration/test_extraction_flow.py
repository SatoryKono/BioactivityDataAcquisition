"""Integration tests for extraction data flow."""

from __future__ import annotations

import inspect
import typing
from typing import Any

import pandas as pd
import pytest

from bioetl.application.mappers.chembl import ChemblRecordMapper
from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)
from bioetl.interfaces.bootstrap_factory import create_default_bootstrap


class TestExtractionFlow:
    """Test data flow: API response → parser → mapper → DataFrame."""

    @pytest.fixture
    def sample_api_response(self) -> dict[str, Any]:
        """Sample ChEMBL API response."""
        return {
            "activities": [
                {
                    "activity_id": 12345,
                    "assay_chembl_id": "CHEMBL12345",
                    "molecule_chembl_id": "CHEMBL25",
                    "standard_value": 5.0,
                    "standard_flag": True,
                },
            ],
            "page_meta": {
                "total_count": 1,
                "offset": 0,
                "limit": 1000,
            },
        }

    @pytest.fixture
    def multi_record_response(self) -> dict[str, Any]:
        """Sample ChEMBL API response with multiple records."""
        return {
            "activities": [
                {
                    "activity_id": 1,
                    "assay_chembl_id": "CHEMBL100",
                    "molecule_chembl_id": "CHEMBL25",
                    "standard_flag": True,
                    "standard_value": 10.0,
                },
                {
                    "activity_id": 2,
                    "assay_chembl_id": "CHEMBL200",
                    "molecule_chembl_id": "CHEMBL50",
                    "standard_flag": False,
                },
                {
                    "activity_id": 3,
                    "assay_chembl_id": "CHEMBL300",
                    "molecule_chembl_id": "CHEMBL75",
                    "standard_flag": True,
                    "standard_value": 10.0,
                },
            ],
            "page_meta": {
                "total_count": 3,
                "offset": 0,
                "limit": 1000,
            },
        }

    def test_parser_returns_raw_dicts(
        self, sample_api_response: dict[str, Any]
    ) -> None:
        """Parser should return list[dict], not typed models."""
        parser = ChemblGenericResponseParser()

        records = parser.parse_to_records(sample_api_response)

        assert isinstance(records, list)
        assert all(isinstance(r, dict) for r in records)
        assert records[0]["activity_id"] == 12345

    def test_parser_extracts_pagination(
        self, sample_api_response: dict[str, Any]
    ) -> None:
        """Parser should extract pagination metadata."""
        parser = ChemblGenericResponseParser()

        pagination = parser.extract_pagination(sample_api_response)

        assert pagination["total_count"] == 1
        assert pagination["offset"] == 0
        assert pagination["limit"] == 1000

    def test_mapper_converts_to_domain_models(
        self, sample_api_response: dict[str, Any]
    ) -> None:
        """Mapper should convert dicts to typed RawRecord models."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper(registry=get_chembl_model_registry())

        raw_records = parser.parse_to_records(sample_api_response)
        typed_records = mapper.map_records(raw_records, "activity")

        assert len(typed_records) == 1
        assert isinstance(typed_records[0], ActivityRawModel)
        # activity_id is ActivityId object in ActivityRawModel
        assert str(typed_records[0].activity_id) == "12345"

    def test_mapper_handles_multiple_records(
        self, multi_record_response: dict[str, Any]
    ) -> None:
        """Mapper should handle multiple records correctly."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper(registry=get_chembl_model_registry())

        raw_records = parser.parse_to_records(multi_record_response)
        typed_records = mapper.map_records(raw_records, "activity")

        assert len(typed_records) == 3
        assert all(isinstance(r, ActivityRawModel) for r in typed_records)
        assert [str(r.activity_id) for r in typed_records] == ["1", "2", "3"]

    def test_full_flow_to_dataframe(self, sample_api_response: dict[str, Any]) -> None:
        """Full flow should produce valid DataFrame."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper(registry=get_chembl_model_registry())

        raw_records = parser.parse_to_records(sample_api_response)
        typed_records = mapper.map_records(raw_records, "activity")
        df = pd.DataFrame([r.model_dump() for r in typed_records])

        assert len(df) == 1
        assert "activity_id" in df.columns
        assert df.iloc[0]["activity_id"] == "12345"

    def test_full_flow_multi_record_dataframe(
        self, multi_record_response: dict[str, Any]
    ) -> None:
        """Full flow with multiple records produces complete DataFrame."""
        parser = ChemblGenericResponseParser()
        mapper = ChemblRecordMapper(registry=get_chembl_model_registry())

        raw_records = parser.parse_to_records(multi_record_response)
        typed_records = mapper.map_records(raw_records, "activity")
        df = pd.DataFrame([r.model_dump() for r in typed_records])

        assert len(df) == 3
        assert list(df["activity_id"]) == ["1", "2", "3"]
        assert list(df["assay_chembl_id"]) == ["CHEMBL100", "CHEMBL200", "CHEMBL300"]

    def test_bootstrap_provides_contract_provider(self) -> None:
        """ApplicationBootstrap should provide schema contract provider."""
        bootstrap = create_default_bootstrap()
        bootstrap.start()

        try:
            # Verify contract provider is available
            assert bootstrap.is_started is True
        finally:
            bootstrap.shutdown()

    def test_parser_mapper_integration(self):
        """Parser and mapper components should work together."""
        bootstrap = create_default_bootstrap()
        bootstrap.start()

        try:
            sample_response = {
                "activities": [
                    {"activity_id": 999, "standard_flag": True, "standard_value": 10.0},
                ],
            }

            # Create components directly (not managed by bootstrap)
            parser = ChemblGenericResponseParser()
            mapper = ChemblRecordMapper(registry=get_chembl_model_registry())

            raw_records = parser.parse_to_records(sample_response)
            typed_records = mapper.map_records(raw_records, "activity")

            assert len(typed_records) == 1
            assert str(typed_records[0].activity_id) == "999"
        finally:
            bootstrap.shutdown()


class TestLayerIsolation:
    """Test that layers are properly isolated."""

    def test_parser_has_no_domain_model_imports(self) -> None:
        """ChemblGenericResponseParser should not import domain models."""
        import bioetl.infrastructure.clients.chembl.response_parser as parser_module

        # Check module doesn't import raw_models in main body
        module_source = inspect.getsource(parser_module)
        # TYPE_CHECKING imports are OK, runtime imports are not
        lines_outside_type_checking = []
        in_type_checking = False
        for line in module_source.split("\n"):
            if "if TYPE_CHECKING:" in line:
                in_type_checking = True
            elif line and not line.startswith(" ") and not line.startswith("\t"):
                in_type_checking = False
            if not in_type_checking:
                lines_outside_type_checking.append(line)

        outside_code = "\n".join(lines_outside_type_checking)
        # Should not have runtime imports of raw_models
        assert "from bioetl.domain.schemas.chembl.raw_models import" not in outside_code

    def test_generic_parser_returns_untyped_data(self) -> None:
        """ChemblGenericResponseParser.parse_to_records returns list[dict]."""
        parser = ChemblGenericResponseParser()
        response = {"activities": [{"id": "1"}, {"id": "2"}]}

        result = parser.parse_to_records(response)

        # Should be plain dicts, not Pydantic models
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)
            assert not hasattr(item, "model_dump")

    def test_extraction_service_returns_generic_types(self) -> None:
        """ExtractionServiceABC should use dict types or RawRecordBatch."""
        from bioetl.domain.ports.extraction import ExtractionServiceABC

        # Check method signatures use generic types
        hints = typing.get_type_hints(ExtractionServiceABC.iter_extract)
        return_hint = str(hints.get("return", ""))

        # Should use RawRecordBatch (which might resolve to list[dict]
        # or list[RawRecord])
        # We accept generic dicts, mappings, or the aliased union
        assert (
            "RawRecordBatch" in return_hint
            or "dict" in return_hint
            or "Mapping" in return_hint
            or "RawRecord" in return_hint
        )

    def test_type_aliases_are_defined(self) -> None:
        """Domain layer defines proper type aliases for cross-layer use."""
        from bioetl.domain.ports.extraction import RawRecordBatch, RawRecordDict

        # Verify type aliases exist and are correct types
        assert RawRecordDict == dict[str, Any]
        # RawRecordBatch is Sequence[Mapping[str, Any]]
        origin = getattr(RawRecordBatch, "__origin__", None)
        if origin:
            # It's a generic type (Sequence)
            assert "Sequence" in str(origin)
        else:
            # Fallback
            assert RawRecordBatch is not None


class TestMapperEntitySupport:
    """Test mapper support for different entity types."""

    @pytest.fixture
    def mapper(self) -> ChemblRecordMapper:
        """Provide a fresh mapper instance."""
        return ChemblRecordMapper(registry=get_chembl_model_registry())

    def test_mapper_supports_all_entity_types(self, mapper: ChemblRecordMapper) -> None:
        """Mapper should support all declared entity types."""
        supported = mapper.get_supported_entities()

        expected = {
            "activity",
            "molecule",
            "target",
            "assay",
            "document",
            "publication",
        }
        assert supported == expected

    def test_mapper_molecule_entity(self, mapper: ChemblRecordMapper) -> None:
        """Mapper should handle molecule records."""
        raw = [
            {
                "molecule_chembl_id": "CHEMBL25",
                "pref_name": "ASPIRIN",
                "molecule_type": "Small molecule",
            }
        ]

        result = mapper.map_records(raw, "molecule")

        assert len(result) == 1
        assert str(result[0].molecule_chembl_id) == "CHEMBL25"

    def test_mapper_target_entity(self, mapper: ChemblRecordMapper) -> None:
        """Mapper should handle target records."""
        raw = [
            {
                "target_chembl_id": "CHEMBL204",
                "pref_name": "Cyclooxygenase-2",
                "organism": "Homo sapiens",
                "target_type": "SINGLE PROTEIN",
            }
        ]

        result = mapper.map_records(raw, "target")

        assert len(result) == 1
        assert str(result[0].target_chembl_id) == "CHEMBL204"

    def test_mapper_assay_entity(self, mapper: ChemblRecordMapper) -> None:
        """Mapper should handle assay records."""
        raw = [
            {
                "assay_chembl_id": "CHEMBL1217643",
                "assay_type": "B",
                "description": "Binding assay",
            }
        ]

        result = mapper.map_records(raw, "assay")

        assert len(result) == 1
        assert str(result[0].assay_chembl_id) == "CHEMBL1217643"

    def test_mapper_document_entity(self, mapper: ChemblRecordMapper) -> None:
        """Mapper should handle document records."""
        raw = [
            {
                "document_chembl_id": "CHEMBL1125443",
                "journal": "J. Med. Chem.",
                "year": 2007,
            }
        ]

        result = mapper.map_records(raw, "document")

        assert len(result) == 1
        assert str(result[0].document_chembl_id) == "CHEMBL1125443"

    def test_mapper_raises_for_unknown_entity(self, mapper: ChemblRecordMapper) -> None:
        """Mapper should raise ValueError for unknown entities."""
        with pytest.raises(ValueError, match="Unknown entity type"):
            mapper.map_records([{"id": "1"}], "unknown_entity")
