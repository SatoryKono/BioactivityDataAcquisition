import pytest
import pandas as pd
from unittest.mock import MagicMock

from bioetl.application.pipelines.chembl.testitem.run import (
    ChemblTestitemPipeline,
)
from bioetl.domain.schemas.chembl.testitem import TestitemSchema


@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "testitem"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []

    validation_service = MagicMock()
    validation_service.get_schema.return_value = TestitemSchema
    validation_service.get_schema_columns.return_value = list(
        TestitemSchema.to_schema().columns.keys()
    )

    return ChemblTestitemPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
    )

def test_transform_columns_selection(pipeline):
    df = pd.DataFrame({
        "molecule_chembl_id": ["CHEMBL1", "CHEMBL2"],
        "extra_col": [1, 2],
        "max_phase": [4, None]
    })
    
    result = pipeline._do_transform(df)
    
    assert "extra_col" not in result.columns
    assert "molecule_chembl_id" in result.columns
    assert "max_phase" in result.columns

def test_transform_max_phase(pipeline):
    df = pd.DataFrame({
        "max_phase": [4, "3", None, "invalid"],
        "molecule_chembl_id": ["CHEMBL1", "CHEMBL2", "CHEMBL3", "CHEMBL4"]
    })
    
    result = pipeline._do_transform(df)
    
    assert pd.api.types.is_integer_dtype(result["max_phase"])
    assert result.iloc[0]["max_phase"] == 4
    assert result.iloc[1]["max_phase"] == 3
    assert result.iloc[2]["max_phase"] is pd.NA
    assert result.iloc[3]["max_phase"] is pd.NA

def test_transform_nested_fields(pipeline):
    # Setup config fields for normalization
    # Treat atc_classifications as ID field to preserve/enforce uppercase
    pipeline._config.normalization.id_fields = ["atc_classifications"]
    
    pipeline._config.fields = [
        {"name": "atc_classifications", "data_type": "array"},
        {"name": "molecule_properties", "data_type": "object"},
        {"name": "molecule_chembl_id", "data_type": "string"},
    ]
    
    df = pd.DataFrame({
        "molecule_chembl_id": ["CHEMBL1"],
        "atc_classifications": [["L01", "A02"]],
        "molecule_properties": [{"alogp": 2.5}]
    })
    
    # Вызываем полный transform, который включает _do_transform и normalize_nested_fields
    result = pipeline.transform(df)
    
    assert result.iloc[0]["atc_classifications"] == "L01|A02"
    assert result.iloc[0]["molecule_properties"] == "alogp:2.5"
