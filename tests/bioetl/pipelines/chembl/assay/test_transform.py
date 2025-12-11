"""Tests for ChemblPipelineBase (Assay context)."""

from unittest.mock import MagicMock

import pandas as pd
import pandera as pa
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry
from bioetl.infrastructure.validation.schemas.chembl.assay import AssayTableSchema


@pytest.fixture
def pipeline():
    """Create pipeline fixture with mocked dependencies for assay entity."""
    config = MagicMock()
    config.provider = "chembl"
    config.entity_name = "assay"
    config.primary_key = "assay_chembl_id"
    config.serialization_mode = "pipe"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []
    config.normalization = MagicMock()
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.get_fields.side_effect = lambda: config.fields
    config.get_normalization.side_effect = lambda: config.normalization

    validation_service = MagicMock()
    validation_service.get_schema.return_value = AssayTableSchema
    validation_service.get_schema_columns.return_value = list(
        AssayTableSchema.to_schema().columns.keys()
    )

    normalization_service = MagicMock()
    normalization_service.apply_normalize_dataframe.side_effect = lambda df: df.copy()
    normalization_service.apply_normalize_batch.side_effect = lambda df: df.copy()
    normalization_service.apply_normalize_fields.side_effect = lambda df, *_: df
    normalization_service.normalize.side_effect = lambda df: df.copy()
    normalization_service.apply_normalize.side_effect = lambda record: record

    index_generator = MagicMock()
    index_generator.next_index.return_value = 0
    timestamp_provider = MagicMock()
    timestamp_provider.get_extraction_timestamp.return_value = "2024-01-01T00:00:00Z"

    return ChemblPipelineBase(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
        loader=MagicMock(),
        extraction_service=MagicMock(),
        hash_service=MagicMock(),
        index_generator=index_generator,
        timestamp_provider=timestamp_provider,
        normalization_service=normalization_service,
        entity_model_registry=get_chembl_model_registry(),
    )


def test_transform_nested_fields_assay_parameters(pipeline):
    """Nested assay fields are serialized deterministically."""

    class MockSchema(pa.DataFrameModel):
        assay_chembl_id: pa.typing.Series[str] = pa.Field(nullable=False)
        assay_parameters: pa.typing.Series[str] = pa.Field(nullable=True)
        hash_row: pa.typing.Series[str] = pa.Field(nullable=True)

    pipeline._validation_service.get_schema.return_value = MockSchema
    pipeline._validation_service.get_schema_columns.return_value = list(
        MockSchema.to_schema().columns.keys()
    )

    pipeline._config.fields = [
        {"name": "assay_chembl_id", "data_type": "string"},
        {"name": "assay_parameters", "data_type": "array"},
    ]

    df = pd.DataFrame(
        {
            "assay_chembl_id": ["CHEMBL_ASSAY_1", "CHEMBL_ASSAY_2"],
            "assay_parameters": [
                [
                    {"param": "pH", "value": "7.4"},
                    {"param": "temperature", "value": "25"},
                ],
                None,
            ],
        }
    )

    result = pipeline.transform(df)

    # First row: serialized dict list
    params = result.iloc[0]["assay_parameters"]
    assert "param:pH" in params
    assert "value:7.4" in params
    assert "param:temperature" in params
    assert "value:25" in params

    # Second row: preserved as NaN
    assert pd.isna(result.iloc[1]["assay_parameters"])

    # hash_row column is present (added by enforce_schema)
    assert "hash_row" in result.columns
