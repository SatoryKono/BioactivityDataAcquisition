# import pandas as pd

from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


@pytest.fixture
def common_dependencies():
    config = MagicMock()
    config.entity_name = "test"
    config.provider = "chembl"
    config.hashing = MagicMock()
    config.hashing.business_key_fields = []
    config.fields = []
    config.normalization = MagicMock()
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.get_fields.side_effect = lambda: config.fields
    config.get_normalization.side_effect = lambda: config.normalization

    normalization_service = MagicMock()
    normalization_service.normalize.side_effect = lambda df: df.copy()
    normalization_service.normalize_record.side_effect = lambda record: record
    normalization_service.ensure_numeric_columns.side_effect = lambda df: df

    record_source = MagicMock()
    record_source.iter_records.return_value = iter([])

    return {
        "config": config,
        "logger": MagicMock(),
        "validation_service": MagicMock(),
        "loader": MagicMock(),
        "extraction_service": MagicMock(),
        "hash_service": MagicMock(),
        "normalization_service": normalization_service,
        "record_source": record_source,
    }


@pytest.mark.parametrize(
    "pipeline_info",
    [
        ("activity", "activity_id"),
        ("assay", "assay_chembl_id"),
        ("publication", "document_chembl_id"),
        ("target", "target_chembl_id"),
        ("molecule", "molecule_chembl_id"),
    ],
)
def test_pipeline_instantiation(pipeline_info, common_dependencies):
    """Smoke test: pipelines can be instantiated and config works."""
    entity_name, id_col = pipeline_info

    config = MagicMock()
    config.entity_name = entity_name
    config.provider = "chembl"
    config.primary_key = id_col
    config.serialization_mode = "pipe"

    pipeline = ChemblPipelineBase(
        config=config,
        logger=common_dependencies["logger"],
        validation_service=common_dependencies["validation_service"],
        loader=common_dependencies["loader"],
        extraction_service=common_dependencies["extraction_service"],
        hash_service=common_dependencies["hash_service"],
        normalization_service=common_dependencies["normalization_service"],
        record_source=common_dependencies["record_source"],
    )

    assert pipeline.ID_COLUMN == id_col
    assert pipeline.API_FILTER_KEY == f"{id_col}__in"

    # Test transform (coverage for _do_transform)
    df = pd.DataFrame({"id": [1], "chembl_release": [{"chembl_release": "34"}]})
    result = pipeline.transform(df)
    assert isinstance(result, pd.DataFrame)
