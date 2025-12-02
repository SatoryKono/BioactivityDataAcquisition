import pytest
import pandas as pd
from unittest.mock import MagicMock
from bioetl.pipelines.chembl.document.run import ChemblDocumentPipeline

@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "document"
    config.model_dump.return_value = {}
    
    return ChemblDocumentPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=MagicMock(),
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
    )

def test_transform_chembl_release(pipeline):
    df = pd.DataFrame({
        "chembl_release": [{"chembl_release": "chembl_33"}, "chembl_34"]
    })
    
    result = pipeline._do_transform(df)
    
    assert result.iloc[0]["chembl_release"] == "chembl_33"
    assert result.iloc[1]["chembl_release"] == "chembl_34"

def test_transform_int_columns(pipeline):
    df = pd.DataFrame({
        "year": [2020, None, 2021],
        "src_id": [1, 2, None],
        "other": ["a", "b", "c"]
    })
    
    result = pipeline._do_transform(df)
    
    assert pd.api.types.is_integer_dtype(result["year"])
    assert pd.api.types.is_integer_dtype(result["src_id"])
    
    assert result.iloc[1]["year"] is pd.NA
    assert result.iloc[2]["src_id"] is pd.NA

def test_transform_pubmed_id(pipeline):
    df = pd.DataFrame({
        "pubmed_id": [12345, None, 67890]
    })
    
    result = pipeline._do_transform(df)
    
    assert pd.api.types.is_string_dtype(result["pubmed_id"])
    assert result.iloc[0]["pubmed_id"] == "12345"
    assert result.iloc[1]["pubmed_id"] is pd.NA
