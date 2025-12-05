import pytest
import pandas as pd
from unittest.mock import MagicMock

from bioetl.application.pipelines.chembl.pipeline import ChemblEntityPipeline

@pytest.fixture
def common_dependencies():
    config = MagicMock()
    config.entity_name = "test"
    config.provider = "chembl"
    config.hashing = MagicMock()
    config.hashing.business_key_fields = []

    return {
        "config": config,
        "logger": MagicMock(),
        "validation_service": MagicMock(),
        "output_writer": MagicMock(),
        "extraction_service": MagicMock(),
    }


@pytest.mark.parametrize("pipeline_info", [
    ("activity", "activity_id"),
    ("assay", "assay_chembl_id"),
    ("document", "document_chembl_id"),
    ("target", "target_chembl_id"),
    ("testitem", "molecule_chembl_id"),
])
def test_pipeline_instantiation(pipeline_info, common_dependencies):
    """Smoke test: pipelines can be instantiated and config works."""
    entity_name, id_col = pipeline_info
    
    config = MagicMock()
    config.entity_name = entity_name
    config.provider = "chembl"
    config.primary_key = id_col
    
    pipeline = ChemblEntityPipeline(
        config=config,
        logger=common_dependencies["logger"],
        validation_service=common_dependencies["validation_service"],
        output_writer=common_dependencies["output_writer"],
        extraction_service=common_dependencies["extraction_service"],
        hash_service=MagicMock(),
    )
    
    assert pipeline.ID_COLUMN == id_col
    assert pipeline.API_FILTER_KEY == f"{id_col}__in"

    # Test transform (coverage for _do_transform)
    df = pd.DataFrame({
        "id": [1],
        "chembl_release": [{"chembl_release": "34"}]
    })
    result = pipeline.transform(df)
    assert isinstance(result, pd.DataFrame)
