from unittest.mock import MagicMock

import pandas as pd
import pandera as pa
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.schemas.chembl.activity import ActivityTableSchema


@pytest.fixture
def pipeline():
    config = MagicMock()
    config.id = "activity_chembl"
    config.provider = "chembl"
    config.entity_name = "activity"
    config.primary_key = "activity_id"
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
    validation_service.get_schema.return_value = ActivityTableSchema
    validation_service.get_schema_columns.return_value = list(
        ActivityTableSchema.to_schema().columns.keys()
    )

    metadata_builder = MagicMock()
    normalization_service = MagicMock()
    normalization_service.apply_normalize_dataframe.side_effect = lambda df: df.copy()
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
        metadata_builder=metadata_builder,
        normalization_service=normalization_service,
    )


def test_transform_nested_fields_activity_properties(pipeline):
    class MockSchema(pa.DataFrameModel):
        activity_properties: pa.typing.Series[str] = pa.Field(nullable=True)
        ligand_efficiency: pa.typing.Series[str] = pa.Field(nullable=True)
        assay_chembl_id: pa.typing.Series[str] = pa.Field(nullable=True)
        hash_row: pa.typing.Series[str] = pa.Field(nullable=False)

    pipeline._validation_service.get_schema.return_value = MockSchema
    pipeline._validation_service.get_schema_columns.return_value = list(
        MockSchema.to_schema().columns.keys()
    )

    pipeline._config.fields = [
        {"name": "activity_properties", "data_type": "array"},
        {"name": "ligand_efficiency", "data_type": "object"},
        {"name": "assay_chembl_id", "data_type": "string"},
    ]

    df = pd.DataFrame(
        {
            "assay_chembl_id": ["CHEMBL1", "CHEMBL2"],
            "activity_properties": [[{"relation": "=", "text_value": "active"}], None],
            "ligand_efficiency": [{"bei": 12.3, "lle": 5.0}, {}],
        }
    )

    result = pipeline.transform(df)

    props = result.iloc[0]["activity_properties"]
    assert "relation:=" in props
    assert "text_value:active" in props

    le = result.iloc[0]["ligand_efficiency"]
    assert "bei:12.3" in le
    assert "lle:5.0" in le

    assert pd.isna(result.iloc[1]["activity_properties"])
    assert pd.isna(result.iloc[1]["ligand_efficiency"])

    assert "hash_row" in result.columns
    assert result["hash_row"].isna().all()
    assert len(result) == 2


def test_transform_drops_invalid_rows(pipeline):
    class MockSchema(pa.DataFrameModel):
        required_col: pa.typing.Series[str] = pa.Field(nullable=False)
        optional_col: pa.typing.Series[str] = pa.Field(nullable=True)
        hash_row: pa.typing.Series[str] = pa.Field(nullable=False)

    pipeline._validation_service.get_schema.return_value = MockSchema
    pipeline._validation_service.get_schema_columns.return_value = list(
        MockSchema.to_schema().columns.keys()
    )

    pipeline._normalization_service = MagicMock()
    pipeline._normalization_service.apply_normalize_fields.side_effect = lambda x: x
    pipeline._normalization_service.apply_normalize.side_effect = lambda record: record
    pipeline._normalization_service.apply_normalize_dataframe.side_effect = (
        lambda df: df.copy()
    )
    pipeline._normalization_service.normalize.side_effect = lambda df: df.copy()

    df = pd.DataFrame(
        {
            "required_col": ["A", None, "C"],
            "optional_col": ["1", "2", None],
            "extra_col": [1, 2, 3],
        }
    )

    result = pipeline.transform(df)

    assert len(result) == 2
    assert result["required_col"].tolist() == ["A", "C"]

    assert result["hash_row"].isna().all()
