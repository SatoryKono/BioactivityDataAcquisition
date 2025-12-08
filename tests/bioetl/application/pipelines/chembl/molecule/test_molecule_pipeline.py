"""Tests for ChemblPipelineBase (Molecule context)."""

from unittest.mock import MagicMock

import pandas as pd
import pandera as pa
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema


@pytest.fixture
def pipeline():  # pylint: disable=redefined-outer-name
    """Create pipeline fixture with mocked dependencies for molecule entity."""
    config = MagicMock()
    config.provider = "chembl"
    config.entity_name = "molecule"
    config.primary_key = "molecule_chembl_id"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []
    config.normalization = MagicMock()
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.get_fields.side_effect = lambda: config.fields
    config.get_normalization.side_effect = lambda: config.normalization

    validation_service = MagicMock()
    validation_service.get_schema.return_value = MoleculeSchema
    validation_service.get_schema_columns.return_value = list(
        MoleculeSchema.to_schema().columns.keys()
    )

    normalization_service = MagicMock()
    normalization_service.apply_normalize_dataframe.side_effect = lambda df: df.copy()
    normalization_service.apply_normalize_batch.side_effect = lambda df: df.copy()
    normalization_service.apply_normalize_fields.side_effect = lambda df, *_: df
    normalization_service.apply_normalize.side_effect = lambda record: record

    return ChemblPipelineBase(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
        hash_service=MagicMock(),
        normalization_service=normalization_service,
    )


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
    # Serialized dict should contain key:value pairs
    assert "alogp:2.5" in props
    assert "hbd:1" in props

    atc = result.iloc[0]["atc_classifications"]
    # List should be joined with |
    assert atc == "L01|A02"

    assert "hash_row" in result.columns
