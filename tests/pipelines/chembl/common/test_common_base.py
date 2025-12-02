import pytest
import pandas as pd
from unittest.mock import MagicMock
from bioetl.pipelines.chembl.common.base import ChemblCommonPipeline

class ConcreteCommonPipeline(ChemblCommonPipeline):
    pass

@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "test_entity"
    config.pipeline = {"filter_a": 1}
    config.model_dump.return_value = {}
    
    extraction_service = MagicMock()
    logger = MagicMock()
    
    # Initialize via base constructor (mocking deps)
    p = ConcreteCommonPipeline(
        config=config,
        logger=logger,
        validation_service=MagicMock(),
        output_writer=MagicMock(),
        extraction_service=extraction_service
    )
    return p

def test_extract_flow(pipeline):
    pipeline._extraction_service.extract_all.return_value = pd.DataFrame()
    
    pipeline.extract(extra_filter=2)
    
    pipeline._extraction_service.extract_all.assert_called_with(
        "test_entity",
        filter_a=1,
        extra_filter=2
    )
    pipeline._logger.info.assert_called()

def test_do_transform_flow(pipeline):
    df = pd.DataFrame({"a": [1]})
    result = pipeline._do_transform(df)
    pd.testing.assert_frame_equal(df, result)
