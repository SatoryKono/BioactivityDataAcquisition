"""Tests for ChemblTestitemPipeline."""
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.testitem.run import (
    ChemblTestitemPipeline,
)
from bioetl.domain.schemas.chembl.testitem import TestitemSchema


@pytest.fixture
def pipeline():  # pylint: disable=redefined-outer-name
    config = MagicMock()
    config.entity_name = "testitem"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []

    validation_service = MagicMock()
    validation_service.get_schema.return_value = TestitemSchema
    validation_service.get_schema_columns.return_value = list(
        TestitemSchema.to_schema().columns.keys()
    )

    return ChemblTestitemPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
    )


def test_transform_columns_preserved(pipeline):
    """Test that transform() preserves columns through transformation."""
    # Setup config fields for normalization
    pipeline._config.fields = [
        {"name": "molecule_chembl_id", "data_type": "string"},
        {"name": "max_phase", "data_type": "integer"},
    ]

    df = pd.DataFrame({
        "molecule_chembl_id": ["CHEMBL1", "CHEMBL2"],
        "extra_col": [1, 2],
        "max_phase": [4, None]
    })

    # Transform processes fields but doesn't filter columns
    result = pipeline.transform(df)

    assert "molecule_chembl_id" in result.columns
    assert "max_phase" in result.columns


def test_transform_max_phase(pipeline):
    """Test max_phase type conversion."""
    df = pd.DataFrame({
        "max_phase": [4, "3", None, "invalid"],
        "molecule_chembl_id": ["CHEMBL1", "CHEMBL2", "CHEMBL3", "CHEMBL4"]
    })

    result = pipeline._do_transform(df)  # pylint: disable=protected-access

    assert pd.api.types.is_integer_dtype(result["max_phase"])
    assert result.iloc[0]["max_phase"] == 4
    assert result.iloc[1]["max_phase"] == 3
    assert result.iloc[2]["max_phase"] is pd.NA
    assert result.iloc[3]["max_phase"] is pd.NA


def test_transform_nested_fields(pipeline):
    """Test nested field normalization."""
    # Treat atc_classifications as ID field to preserve/enforce uppercase
    pipeline._config.normalization.id_fields = ["atc_classifications"]
    pipeline._config.fields = [
        {"name": "atc_classifications", "data_type": "array"},
        {"name": "molecule_properties", "data_type": "object"},
        {"name": "molecule_chembl_id", "data_type": "string"},
    ]

    df = pd.DataFrame({
        "molecule_chembl_id": ["CHEMBL1"],
        "atc_classifications": [["L01", "A02"]],
        "molecule_properties": [{"alogp": 2.5}]
    })

    result = pipeline.transform(df)

    assert result.iloc[0]["atc_classifications"] == "L01|A02"
    assert result.iloc[0]["molecule_properties"] == "alogp:2.5"
