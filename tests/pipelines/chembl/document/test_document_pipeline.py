"""Tests for ChemblEntityPipeline (Document context)."""
import unittest
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.pipeline import (
    ChemblEntityPipeline,
)
from bioetl.domain.schemas.chembl.document import DocumentSchema
from bioetl.domain.transform.impl.normalize import NormalizationService
from bioetl.infrastructure.ingestion import NormalizationIngestionService


@pytest.fixture
def pipeline():
    config = MagicMock()
    config.entity_name = "document"
    config.primary_key = "document_chembl_id"
    config.model_dump.return_value = {}
    config.pipeline = {}
    # Setup fields for normalization
    config.fields = [
        {"name": "chembl_release", "data_type": "string"},
        {"name": "year", "data_type": "integer"},
        {"name": "src_id", "data_type": "integer"},
        {"name": "pubmed_id", "data_type": "integer"},
        {"name": "other", "data_type": "string"},
    ]
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.normalization.custom_normalizers = {}

    validation_service = MagicMock()
    validation_service.get_schema.return_value = DocumentSchema
    validation_service.get_schema_columns.return_value = list(
        DocumentSchema.to_schema().columns.keys()
    )

    normalization_service = NormalizationService(config)
    ingestion_service = NormalizationIngestionService(
        normalization_service=normalization_service,
        validation_service=validation_service,
        logger=MagicMock(),
    )

    # We need real normalization service logic or mocked?
    # ChemblPipelineBase initializes NormalizationService(config).
    # So we rely on that service working with our mock config.

    return ChemblEntityPipeline(
        config=config,
        logger=MagicMock(),
        validation_service=validation_service,
        output_writer=MagicMock(),
        extraction_service=MagicMock(),
        ingestion_service=ingestion_service,
    )


def test_transform_chembl_release(pipeline):
    """Test chembl_release field transformation (dict extraction)."""
    # We need a custom normalizer to extract 'chembl_release' from dict
    # because generic string normalizer expects scalars.
    
    df = pd.DataFrame({
        "chembl_release": [{"chembl_release": "chembl_33"}, "chembl_34"]
    })

    # Mock validation to return df as is
    pipeline._validation_service.get_schema_columns.return_value = [
        "chembl_release"
    ]

    # Define extraction logic
    def extract_release(val):
        if isinstance(val, dict):
            return val.get("chembl_release")
        return val

    # Patch get_normalizer to return our extractor for 'chembl_release'
    # Note: We patch where it is imported/used in NormalizationService
    with unittest.mock.patch(
        "bioetl.domain.transform.impl.normalize.get_normalizer"
    ) as mock_get:
        # Return extractor only for 'chembl_release', None for others
        mock_get.side_effect = lambda name: (
            extract_release if name == "chembl_release" else None
        )
        
        result = pipeline.transform(df)

    assert result.iloc[0]["chembl_release"] == "chembl_33"
    assert result.iloc[1]["chembl_release"] == "chembl_34"


def test_transform_int_columns(pipeline):
    """Test integer column conversion."""
    df = pd.DataFrame({
        "year": [2020, None, 2021],
        "src_id": [1, 2, None],
        "other": ["a", "b", "c"]
    })

    # Ensure columns exist in schema for _enforce_schema
    pipeline._validation_service.get_schema_columns.return_value = [
        "year", "src_id", "other"
    ]

    result = pipeline.transform(df)

    # NormalizationService handles type conversion if declared in config.fields
    # "year" is integer in fixture config.

    # Check if values are preserved/converted
    # (pandas nullable Int64 is used usually)
    assert result.iloc[0]["year"] == 2020
    assert pd.isna(result.iloc[1]["year"])

    assert result.iloc[0]["src_id"] == 1
    assert pd.isna(result.iloc[2]["src_id"])


def test_transform_pubmed_id(pipeline):
    """Test pubmed_id field transformation."""
    df = pd.DataFrame({
        "pubmed_id": [12345, None, 67890]
    })
    pipeline._validation_service.get_schema_columns.return_value = [
        "pubmed_id"
    ]

    result = pipeline.transform(df)

    assert result.iloc[0]["pubmed_id"] == 12345
    assert pd.isna(result.iloc[1]["pubmed_id"])
