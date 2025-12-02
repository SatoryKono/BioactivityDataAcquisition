import pytest
import pandas as pd
from unittest.mock import MagicMock

from bioetl.application.pipelines.chembl.activity.run import ChemblActivityPipeline
from bioetl.application.pipelines.chembl.assay.run import ChemblAssayPipeline
from bioetl.application.pipelines.chembl.document.run import ChemblDocumentPipeline
from bioetl.application.pipelines.chembl.target.run import ChemblTargetPipeline
from bioetl.application.pipelines.chembl.testitem.run import ChemblTestitemPipeline


@pytest.fixture
def common_dependencies():
    config = MagicMock()
    config.entity_name = "test"
    config.provider = "chembl"
    config.business_key = []

    return {
        "config": config,
        "logger": MagicMock(),
        "validation_service": MagicMock(),
        "output_writer": MagicMock(),
        "extraction_service": MagicMock(),
    }


@pytest.mark.parametrize("pipeline_cls", [
    ChemblActivityPipeline,
    ChemblAssayPipeline,
    ChemblDocumentPipeline,
    ChemblTargetPipeline,
    ChemblTestitemPipeline,
])
def test_pipeline_instantiation(pipeline_cls, common_dependencies):
    # Act
    pipeline = pipeline_cls(
        config=common_dependencies["config"],
        logger=common_dependencies["logger"],
        validation_service=common_dependencies["validation_service"],
        output_writer=common_dependencies["output_writer"],
        extraction_service=common_dependencies["extraction_service"],
    )

    # Assert
    assert isinstance(pipeline, pipeline_cls)

    # Test transform (coverage for _do_transform)
    df = pd.DataFrame({
        "id": [1],
        "chembl_release": [{"chembl_release": "34"}]
    })
    result = pipeline.transform(df)
    assert isinstance(result, pd.DataFrame)
