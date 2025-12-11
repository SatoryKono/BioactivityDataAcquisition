"""Tests for ChemblPipelineBase (Document context)."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.schemas.chembl.publication import PublicationTableSchema
from bioetl.infrastructure.transform.impl.normalize import (
    DefaultNormalizationTransformerImpl,
)


@pytest.fixture
def pipeline():
    """Create a configured ChemblPipelineBase for testing."""
    config = MagicMock()
    config.id = "chembl_publication"
    config.provider = "chembl"
    config.entity_name = "publication"
    config.primary_key = "document_chembl_id"
    config.serialization_mode = "pipe"
    config.model_dump.return_value = {}
    config.pipeline = {}

    config.fields = [
        {"name": "chembl_release", "data_type": "string"},
        {"name": "year", "data_type": "integer"},
        {"name": "src_id", "data_type": "integer"},
        {"name": "pubmed_id", "data_type": "integer"},
        {"name": "other", "data_type": "string"},
    ]
    config.normalization = MagicMock()
    config.normalization.case_sensitive_fields = []
    config.normalization.id_fields = []
    config.normalization.custom_normalizers = {}
    config.hashing = MagicMock()
    config.hashing.business_key_fields = []
    config.get_fields.side_effect = lambda: config.fields
    config.get_normalization.side_effect = lambda: config.normalization

    validation_service = MagicMock()
    validation_service.get_schema.return_value = PublicationTableSchema
    validation_service.get_schema_columns.return_value = list(
        PublicationTableSchema.to_schema().columns.keys()
    )

    normalization_service = DefaultNormalizationTransformerImpl(config)

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
    )


def test_transform_chembl_release(pipeline):
    df = pd.DataFrame(
        {"chembl_release": [{"chembl_release": "chembl_33"}, "chembl_34"]}
    )

    pipeline._validation_service.get_schema_columns.return_value = ["chembl_release"]

    def extract_release(val):
        if isinstance(val, dict):
            return val.get("chembl_release")
        return val

    with patch(
        "bioetl.infrastructure.transform.impl.normalize.get_normalizer"
    ) as mock_get:
        mock_get.side_effect = lambda name: (
            extract_release if name == "chembl_release" else None
        )

        result = pipeline.transform(df)

    assert result.iloc[0]["chembl_release"] == "chembl_33"
    assert result.iloc[1]["chembl_release"] == "chembl_34"


def test_transform_int_columns(pipeline):
    df = pd.DataFrame(
        {"year": [2020, None, 2021], "src_id": [1, 2, None], "other": ["a", "b", "c"]}
    )

    pipeline._validation_service.get_schema_columns.return_value = [
        "year",
        "src_id",
        "other",
    ]

    result = pipeline.transform(df)

    assert result.iloc[0]["year"] == 2020
    assert pd.isna(result.iloc[1]["year"])
    assert result.iloc[2]["year"] == 2021

    assert result.iloc[0]["src_id"] == 1
    assert result.iloc[1]["src_id"] == 2
    assert pd.isna(result.iloc[2]["src_id"])


def test_transform_pubmed_id(pipeline):
    df = pd.DataFrame({"pubmed_id": [12345, None, 67890]})
    pipeline._validation_service.get_schema_columns.return_value = ["pubmed_id"]

    result = pipeline.transform(df)

    assert result.iloc[0]["pubmed_id"] == 12345
    assert pd.isna(result.iloc[1]["pubmed_id"])
    assert result.iloc[2]["pubmed_id"] == 67890
