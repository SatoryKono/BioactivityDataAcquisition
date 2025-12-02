import pytest
import pandas as pd
from unittest.mock import MagicMock
from bioetl.application.pipelines.chembl.testitem.run import ChemblTestitemPipeline

@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "testitem"
    config.model_dump.return_value = {}
    
    return ChemblTestitemPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=MagicMock(),
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
    )

def test_transform_columns_selection(pipeline):
    df = pd.DataFrame({
        "molecule_chembl_id": ["M1", "M2"],
        "extra_col": [1, 2],
        "max_phase": [4, None]
    })
    
    result = pipeline._do_transform(df)
    
    assert "extra_col" not in result.columns
    assert "molecule_chembl_id" in result.columns
    assert "max_phase" in result.columns

def test_transform_max_phase(pipeline):
    df = pd.DataFrame({
        "max_phase": [4, "3", None, "invalid"]
    })
    
    result = pipeline._do_transform(df)
    
    assert pd.api.types.is_integer_dtype(result["max_phase"])
    assert result.iloc[0]["max_phase"] == 4
    assert result.iloc[1]["max_phase"] == 3
    assert result.iloc[2]["max_phase"] is pd.NA
    assert result.iloc[3]["max_phase"] is pd.NA
