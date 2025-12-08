"""Tests for ChemblPipelineBase (Target context)."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.schemas.chembl.target import TargetTableSchema


@pytest.fixture
def pipeline():
    """Create pipeline fixture with mocked dependencies."""
    config = MagicMock()
    config.provider = "chembl"
    config.entity_name = "target"
    config.primary_key = "target_chembl_id"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []
    config.normalization = MagicMock()
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.get_fields.side_effect = lambda: config.fields
    config.get_normalization.side_effect = lambda: config.normalization

    validation_service = MagicMock()
    validation_service.get_schema.return_value = TargetTableSchema
    validation_service.get_schema_columns.return_value = list(
        TargetTableSchema.to_schema().columns.keys()
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
        loader=MagicMock(),
        extraction_service=MagicMock(),
        hash_service=MagicMock(),
        normalization_service=normalization_service,
    )


def test_transform_nested_fields_target_components(pipeline):
    """Test transformation of nested fields (serialization)."""
    pipeline._config.fields = [
        {"name": "target_components", "data_type": "array"},
        {"name": "cross_references", "data_type": "array"},
        {"name": "target_chembl_id", "data_type": "string"},
        {"name": "target_type", "data_type": "string"},  # Required field
    ]

    df = pd.DataFrame(
        {
            "target_chembl_id": ["CHEMBL1"],
            "target_type": ["SINGLE PROTEIN"],  # Required field
            "target_components": [
                [
                    {"component_id": 1, "accession": "P12345"},
                    {"component_id": 2, "accession": "Q67890"},
                ]
            ],
            "cross_references": [[{"xref_src": "PubMed", "xref_id": "123"}]],
        }
    )

    result = pipeline.transform(df)

    comps = result.iloc[0]["target_components"]
    # {"component_id": 1, "accession": "P12345"} ->
    # "accession:P12345|component_id:1" (keys sorted: accession first)
    # Serialization order ensures deterministic string output
    # Note: accession is normalized to uppercase by normalize_uniprot
    assert "accession:P12345|component_id:1" in comps
    assert "accession:Q67890|component_id:2" in comps
    assert "|" in comps

    xrefs = result.iloc[0]["cross_references"]
    assert "xref_src:PubMed" in xrefs
    assert "xref_id:123" in xrefs
