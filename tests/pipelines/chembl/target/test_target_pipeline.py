"""Tests for ChemblEntityPipeline (Target context)."""
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.pipeline import ChemblEntityPipeline
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.transform.impl.normalize import NormalizationService
from bioetl.infrastructure.ingestion import NormalizationIngestionService


@pytest.fixture
def pipeline():
    """Create pipeline fixture with mocked dependencies."""
    config = MagicMock()
    config.entity_name = "target"
    config.primary_key = "target_chembl_id"
    config.model_dump.return_value = {}
    config.pipeline = {}
    config.fields = []

    validation_service = MagicMock()
    validation_service.get_schema.return_value = TargetSchema
    validation_service.get_schema_columns.return_value = list(
        TargetSchema.to_schema().columns.keys()
    )

    normalization_service = NormalizationService(config)
    ingestion_service = NormalizationIngestionService(
        normalization_service=normalization_service,
        validation_service=validation_service,
        logger=MagicMock(),
    )

    return ChemblEntityPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
        ingestion_service=ingestion_service,
    )


def test_transform_nested_fields(pipeline):
    """Test transformation of nested fields (serialization)."""
    pipeline._config.fields = [
        {"name": "target_components", "data_type": "array"},
        {"name": "cross_references", "data_type": "array"},
        {"name": "target_chembl_id", "data_type": "string"},
    ]

    df = pd.DataFrame({
        "target_chembl_id": ["CHEMBL1"],
        "target_type": ["SINGLE PROTEIN"],  # Required field
        "target_components": [
            [
                {"component_id": 1, "accession": "P12345"},
                {"component_id": 2, "accession": "Q67890"}
            ]
        ],
        "cross_references": [
            [{"xref_src": "PubMed", "xref_id": "123"}]
        ]
    })

    result = pipeline.transform(df)

    comps = result.iloc[0]["target_components"]
    # {"component_id": 1, "accession": "P12345"} ->
    # "accession:P12345|component_id:1"
    # Serialization order ensures deterministic string output
    assert "accession:P12345|component_id:1" in comps
    assert "accession:Q67890|component_id:2" in comps
    assert "|" in comps

    xrefs = result.iloc[0]["cross_references"]
    assert "xref_src:PubMed" in xrefs
    assert "xref_id:123" in xrefs
