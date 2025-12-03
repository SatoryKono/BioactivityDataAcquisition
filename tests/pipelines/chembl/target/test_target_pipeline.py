import pytest
import pandas as pd
from unittest.mock import MagicMock

from bioetl.application.pipelines.chembl.target.run import ChemblTargetPipeline
from bioetl.domain.schemas.chembl.target import TargetSchema


@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "target"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []

    validation_service = MagicMock()
    validation_service._schema_provider.get_schema.return_value = TargetSchema

    return ChemblTargetPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
    )

def test_transform_nested_fields(pipeline):
    pipeline._config.fields = [
        {"name": "target_components", "data_type": "array"},
        {"name": "cross_references", "data_type": "array"},
        {"name": "target_chembl_id", "data_type": "string"},
    ]
    
    df = pd.DataFrame({
        "target_chembl_id": ["CHEMBL1"],
        "target_components": [
            [
                {"component_id": 1, "accession": "P12345"},
                {"component_id": 2, "accession": "Q67890"}
            ]
        ],
        "cross_references": [
            [{"xref_src": "PubMed", "xref_id": "123"}]
        ]
    })
    
    result = pipeline.transform(df)
    
    comps = result.iloc[0]["target_components"]
    # The dictionary keys are sorted by default in serialization
    # {"component_id": 1, "accession": "P12345"} -> "accession:P12345|component_id:1"
    assert "accession:P12345|component_id:1" in comps
    assert "accession:Q67890|component_id:2" in comps
    assert "|" in comps
    
    xrefs = result.iloc[0]["cross_references"]
    assert "xref_src:PubMed" in xrefs
    assert "xref_id:123" in xrefs

