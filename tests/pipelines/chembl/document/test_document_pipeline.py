import pytest
import pandas as pd
from unittest.mock import MagicMock

from bioetl.application.pipelines.chembl.document.run import (
    ChemblDocumentPipeline,
)
from bioetl.domain.schemas.chembl.document import DocumentSchema


@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "document"
    config.model_dump.return_value = {}

    validation_service = MagicMock()
    validation_service._schema_provider.get_schema.return_value = DocumentSchema

    return ChemblDocumentPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
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
    
    # pubmed_id is ID -> string usually? Or int? 
    # normalize_pmid returns int.
    # But pipeline base apply logic wraps it.
    # Let's expect int logic or nullable int (Int64)
    # assert pd.api.types.is_integer_dtype(result["pubmed_id"])
    # Wait, the failing test said: is_string_dtype failed.
    # And custom_types.py normalize_pmid returns int.
    # So it should be Int64.
    assert pd.api.types.is_integer_dtype(result["pubmed_id"])
    assert result.iloc[0]["pubmed_id"] == 12345
    assert result.iloc[1]["pubmed_id"] is pd.NA
