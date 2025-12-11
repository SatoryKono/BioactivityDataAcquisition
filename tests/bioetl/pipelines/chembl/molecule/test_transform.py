"""Tests for ChemblPipelineBase (Molecule context)."""

from unittest.mock import MagicMock

import pandas as pd
import pandera as pa
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.infrastructure.chembl.model_registry import get_chembl_model_registry
from bioetl.infrastructure.validation.schemas.chembl.molecule import MoleculeTableSchema


@pytest.fixture
def pipeline():  # pylint: disable=redefined-outer-name
    """Create pipeline fixture with mocked dependencies for molecule entity."""
    config = MagicMock()
    config.provider = "chembl"
    config.entity_name = "molecule"
    config.primary_key = "molecule_chembl_id"
    config.serialization_mode = "pipe"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []
    config.normalization = MagicMock()
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.normalization.custom_normalizers = {}
    config.get_fields.side_effect = lambda: config.fields
    config.get_normalization.side_effect = lambda: config.normalization

    validation_service = MagicMock()
    validation_service.get_schema.return_value = MoleculeTableSchema
    validation_service.get_schema_columns.return_value = list(
        MoleculeTableSchema.to_schema().columns.keys()
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


def test_transform_columns_preserved(pipeline):
    """Test that transform() preserves columns through transformation."""
    pipeline._config.fields = [
        {"name": "molecule_chembl_id", "data_type": "string"},
        {"name": "max_phase", "data_type": "integer"},
    ]
    pipeline._validation_service.get_schema_columns.return_value = [
        "molecule_chembl_id",
        "max_phase",
    ]

    df = pd.DataFrame(
        {
            "molecule_chembl_id": ["CHEMBL1", "CHEMBL2"],
            "extra_col": [1, 2],
            "max_phase": [4, None],
        }
    )

    result = pipeline.transform(df)

    assert "molecule_chembl_id" in result.columns
    assert "max_phase" in result.columns
    assert "extra_col" not in result.columns


def test_transform_max_phase(pipeline):
    """Test max_phase type conversion."""
    pipeline._config.fields = [
        {"name": "max_phase", "data_type": "integer"},
        {"name": "molecule_chembl_id", "data_type": "string"},
    ]
    pipeline._validation_service.get_schema_columns.return_value = [
        "molecule_chembl_id",
        "max_phase",
    ]

    df = pd.DataFrame(
        {
            "max_phase": [4, "3", None, "invalid"],
            "molecule_chembl_id": ["CHEMBL1", "CHEMBL2", "CHEMBL3", "CHEMBL4"],
        }
    )

    result = pipeline.transform(df)

    assert len(result) == 4


def test_transform_nested_fields_molecule(pipeline):
    """Nested molecule fields are serialized deterministically."""

    class MockSchema(pa.DataFrameModel):
        molecule_chembl_id: pa.typing.Series[str] = pa.Field(nullable=False)
        molecule_properties: pa.typing.Series[str] = pa.Field(nullable=True)
        atc_classifications: pa.typing.Series[str] = pa.Field(nullable=True)
        hash_row: pa.typing.Series[str] = pa.Field(nullable=True)

    pipeline._validation_service.get_schema.return_value = MockSchema
    pipeline._validation_service.get_schema_columns.return_value = list(
        MockSchema.to_schema().columns.keys()
    )

    pipeline._config.fields = [
        {"name": "molecule_chembl_id", "data_type": "string"},
        {"name": "molecule_properties", "data_type": "object"},
        {"name": "atc_classifications", "data_type": "array"},
    ]

    df = pd.DataFrame(
        {
            "molecule_chembl_id": ["CHEMBL1"],
            "molecule_properties": [
                {"alogp": 2.5, "hbd": 1},
            ],
            "atc_classifications": [["L01", "A02"]],
        }
    )

    result = pipeline.transform(df)

    props = result.iloc[0]["molecule_properties"]
    assert "alogp:2.5" in props
    assert "hbd:1" in props

    atc = result.iloc[0]["atc_classifications"]
    assert atc == "L01|A02"

    assert "hash_row" in result.columns
