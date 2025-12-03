import pytest
import pandas as pd
import pandera as pa
from unittest.mock import MagicMock

from bioetl.application.pipelines.chembl.pipeline import (
    ChemblEntityPipeline,
)
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.transform.impl.normalize import NormalizationService
from bioetl.infrastructure.ingestion import NormalizationIngestionService


@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "activity"
    config.primary_key = "activity_id"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []

    validation_service = MagicMock()
    validation_service.get_schema.return_value = ActivitySchema
    validation_service.get_schema_columns.return_value = list(
        ActivitySchema.to_schema().columns.keys()
    )

    normalization_service = NormalizationService(config)
    ingestion_service = NormalizationIngestionService(
        normalization_service=normalization_service,
        validation_service=validation_service,
        logger=MagicMock(),
    )

    return ChemblEntityPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
        ingestion_service=ingestion_service,
    )

def test_transform_nested_fields(pipeline):
    # Mock schema to avoid dropping rows due to missing required fields
    class MockSchema(pa.DataFrameModel):
        activity_properties: pa.typing.Series[object] = pa.Field(nullable=True)
        ligand_efficiency: pa.typing.Series[object] = pa.Field(nullable=True)
        assay_chembl_id: pa.typing.Series[str] = pa.Field(nullable=True)
        hash_row: pa.typing.Series[str] = pa.Field(nullable=False) # Simulate required hash_row

    pipeline._validation_service.get_schema.return_value = MockSchema
    pipeline._validation_service.get_schema_columns.return_value = list(MockSchema.to_schema().columns.keys())

    pipeline._config.fields = [
        {"name": "activity_properties", "data_type": "array"},
        {"name": "ligand_efficiency", "data_type": "object"},
        {"name": "assay_chembl_id", "data_type": "string"},
    ]
    
    df = pd.DataFrame({
        "assay_chembl_id": ["CHEMBL1", "CHEMBL2"],
        "activity_properties": [
            [{"relation": "=", "text_value": "active"}], 
            None
        ],
        "ligand_efficiency": [
            {"bei": 12.3, "lle": 5.0}, 
            {}
        ]
    })
    
    result = pipeline.transform(df)
    
    # Check serialization
    props = result.iloc[0]["activity_properties"]
    assert "relation:=" in props
    assert "text_value:active" in props
    
    le = result.iloc[0]["ligand_efficiency"]
    assert "bei:12.3" in le
    assert "lle:5.0" in le
    
    # Empty/None cases
    assert pd.isna(result.iloc[1]["activity_properties"])
    assert pd.isna(result.iloc[1]["ligand_efficiency"])
    
    # Check that hash_row exists (added by enforce_schema) but is None
    # and rows were NOT dropped despite hash_row being required
    assert "hash_row" in result.columns
    assert result["hash_row"].isna().all()
    assert len(result) == 2


def test_transform_drops_invalid_rows(pipeline):
    """Verify that rows with nulls in required columns are dropped."""
    
    class MockSchema(pa.DataFrameModel):
        required_col: pa.typing.Series[str] = pa.Field(nullable=False)
        optional_col: pa.typing.Series[str] = pa.Field(nullable=True)
        hash_row: pa.typing.Series[str] = pa.Field(nullable=False) # Simulate required hash_row
        
    pipeline._validation_service.get_schema.return_value = MockSchema
    pipeline._validation_service.get_schema_columns.return_value = list(MockSchema.to_schema().columns.keys())
    
    pipeline._ingestion_service._normalization_service = MagicMock()
    pipeline._ingestion_service._normalization_service.normalize_fields.side_effect = lambda x: x
    
    df = pd.DataFrame({
        "required_col": ["A", None, "C"],
        "optional_col": ["1", "2", None],
        "extra_col": [1, 2, 3]
    })
    
    result = pipeline.transform(df)
    
    # Check rows
    assert len(result) == 2
    assert result["required_col"].tolist() == ["A", "C"]
    
    # Hash row should be None but rows preserved
    assert result["hash_row"].isna().all()
