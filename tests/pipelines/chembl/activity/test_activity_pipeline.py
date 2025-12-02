import pytest
import pandas as pd
from unittest.mock import MagicMock
from bioetl.application.pipelines.chembl.activity.run import ChemblActivityPipeline

@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "activity"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []
    
    return ChemblActivityPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=MagicMock(),
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
    )

def test_transform_nested_fields(pipeline):
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
    # Note: dict order might vary, but assuming insertion order for simple dicts
    # serialize_dict joins key:value|key:value
    
    props = result.iloc[0]["activity_properties"]
    assert "relation:=" in props
    assert "text_value:active" in props
    
    le = result.iloc[0]["ligand_efficiency"]
    assert "bei:12.3" in le
    assert "lle:5.0" in le
    
    # Empty/None cases
    assert pd.isna(result.iloc[1]["activity_properties"])
    assert pd.isna(result.iloc[1]["ligand_efficiency"])

