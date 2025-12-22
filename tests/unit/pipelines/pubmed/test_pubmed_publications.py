"""Unit tests for PubMed Publications Pipeline."""

from typing import cast
from unittest.mock import MagicMock

import pytest

from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord, RunID, RunType


@pytest.fixture
def mock_services():
    services = MagicMock()
    # Mock logger behavior
    services.logger.bind.return_value = services.logger
    return services


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.provider = "pubmed"
    return config


@pytest.fixture
def mock_runtime():
    return MagicMock()


@pytest.fixture
def pipeline(mock_config, mock_runtime, mock_services):
    return PubMedPublicationsPipeline(mock_config, mock_runtime, mock_services)


@pytest.fixture
def pipeline_context(mock_services):
    return PipelineContext(
        run_id=RunID("00000000-0000-0000-0000-000000000000"),
        run_type=RunType.INCREMENTAL,
        logger=mock_services.logger,
    )


@pytest.mark.asyncio
async def test_transform_bronze_to_silver(pipeline, pipeline_context):
    """Test transformation of valid Bronze record to Silver record."""
    xml_content = """
    <PubmedArticle>
        <MedlineCitation>
            <PMID>12345</PMID>
            <Article>
                <ArticleTitle>Test Title</ArticleTitle>
                <Journal>
                    <Title>Test Journal</Title>
                </Journal>
                <Abstract>
                    <AbstractText>Test Abstract</AbstractText>
                </Abstract>
                <AuthorList>
                    <Author>
                        <LastName>Doe</LastName>
                        <Initials>J</Initials>
                    </Author>
                </AuthorList>
                <PubDate>
                    <Year>2023</Year>
                </PubDate>
            </Article>
        </MedlineCitation>
    </PubmedArticle>
    """

    bronze_record: BronzeRecord = cast(
        "BronzeRecord",
        {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test_batch"},
    )

    # Since we are testing logic that uses datetime.now(UTC), we don't need context.run_start_time
    # which we confirmed was removed from PipelineContext

    silver_record = await pipeline.transform_bronze_to_silver(
        pipeline_context, bronze_record
    )

    assert silver_record is not None
    assert silver_record["pmid"] == "12345"
    assert silver_record["title"] == "Test Title"
    assert silver_record["journal"] == "Test Journal"
    assert silver_record["abstract"] == "Test Abstract"
    assert silver_record["publication_year"] == 2023
    assert silver_record["authors"] == ["Doe, J"]
    assert "_ingestion_ts" in silver_record
    assert isinstance(silver_record["_ingestion_ts"], str)


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_invalid_xml(pipeline, pipeline_context):
    """Test transformation with invalid XML handles error gracefully."""
    bronze_record: BronzeRecord = cast(
        "BronzeRecord",
        {"pmid": "12345", "_raw_xml": "<Invalid>XML", "source_batch_id": "test_batch"},
    )

    silver_record = await pipeline.transform_bronze_to_silver(
        pipeline_context, bronze_record
    )

    assert silver_record is None
    # Check if warning was logged. pipeline.logger is actually accessed via self.services.logger or context.logger in BasePipeline
    # In this test setup, BasePipeline might be using self.logger which comes from somewhere.
    # BasePipeline init: self.logger = services.logger
    # Verify warning call arguments
    args, kwargs = pipeline.logger.warning.call_args
    assert args[0] == "XML_parse_error"
    assert kwargs["pmid"] == "12345"
    assert "error" in kwargs
