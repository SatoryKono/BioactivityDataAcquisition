"""Unit tests for PubMed Publication Pipeline."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.application.pipelines.pubmed import PubMedPublicationPipeline
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import BronzeRecord, RunType
from tests.helpers.transformer_dependencies import instantiate_test_transformer

pytestmark = pytest.mark.usefixtures("publication_type_classification_data")


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
    runtime = MagicMock()
    runtime.exact_replay = False
    runtime.replay_anchor_date = None
    return runtime


@pytest.fixture
def pipeline(mock_config, mock_runtime, mock_services):
    run_id = uuid4()
    transformer = instantiate_test_transformer(
        PubMedPublicationTransformer,
        provider="pubmed",
    )
    return PubMedPublicationPipeline(
        mock_config,
        mock_runtime,
        mock_services,
        run_id,
        shutdown_signal=ShutdownSignal(),
        transformer=transformer,
    )


@pytest.fixture
def pipeline_context(mock_services):
    return PipelineContext(
        run_id=UUID("00000000-0000-0000-0000-000000000000"),
        run_type=RunType.INCREMENTAL,
        logger=mock_services.logger,
    )


@pytest.mark.asyncio
async def test_pubmed_publication__bronze_to_silver__ea1a4f16(pipeline, pipeline_context):
    """Test transformation of valid Bronze record to Silver record."""
    # XML structure matches real PubMed XML format
    xml_content = """
    <PubmedArticle>
        <MedlineCitation>
            <PMID>12345</PMID>
            <Article>
                <ArticleTitle>Test Title</ArticleTitle>
                <Journal>
                    <Title>Test Journal</Title>
                    <ISOAbbreviation>Test J</ISOAbbreviation>
                    <ISSN>1234-5678</ISSN>
                    <JournalIssue>
                        <Volume>10</Volume>
                        <Issue>5</Issue>
                        <PubDate>
                            <Year>2023</Year>
                            <Month>Mar</Month>
                            <Day>15</Day>
                        </PubDate>
                    </JournalIssue>
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
                <Language>eng</Language>
                <PublicationTypeList>
                    <PublicationType>Journal Article</PublicationType>
                </PublicationTypeList>
                <ELocationID EIdType="doi">10.1234/test.2023</ELocationID>
                <ArticleDate DateType="Electronic">
                    <Year>2023</Year>
                    <Month>03</Month>
                    <Day>10</Day>
                </ArticleDate>
            </Article>
            <MedlineJournalInfo>
                <Country>United States</Country>
            </MedlineJournalInfo>
            <KeywordList>
                <Keyword>bioinformatics</Keyword>
                <Keyword>drug discovery</Keyword>
            </KeywordList>
        </MedlineCitation>
        <PubmedData>
            <ArticleIdList>
                <ArticleId IdType="pubmed">12345</ArticleId>
                <ArticleId IdType="pmc">PMC123456</ArticleId>
            </ArticleIdList>
            <History>
                <PubMedPubDate PubStatus="received">
                    <Year>2022</Year>
                    <Month>12</Month>
                    <Day>01</Day>
                </PubMedPubDate>
                <PubMedPubDate PubStatus="accepted">
                    <Year>2023</Year>
                    <Month>02</Month>
                    <Day>15</Day>
                </PubMedPubDate>
            </History>
        </PubmedData>
    </PubmedArticle>
    """

    bronze_record: BronzeRecord = cast(
        "BronzeRecord",
        {"pmid": "12345", "_raw_xml": xml_content, "source_batch_id": "test_batch"},
    )

    silver_record = await pipeline.transform_bronze_to_silver(
        pipeline_context, bronze_record
    )

    import json

    assert silver_record is not None
    # Basic fields
    assert silver_record["pmid"] == "12345"
    assert silver_record["title"] == "Test Title"
    assert silver_record["journal"] == "Test Journal"
    assert silver_record["abstract"] == "Test Abstract"
    # Authors are stored as names (not hashed)
    assert json.loads(silver_record["authors"]) == ["Doe, J"]
    # Date fields
    assert silver_record["publication_year"] == 2023
    assert silver_record["pub_date"] == "2023-03-15"
    # Note: accepted_date, received_date, epub_date are excluded from output per design
    # Journal fields
    assert silver_record["journal_name_short"] == "Test J"
    assert silver_record["issn"] == "1234-5678"
    assert silver_record["volume"] == "10"
    assert silver_record["issue"] == "5"
    # Classification
    assert silver_record["doi"] == "10.1234/test.2023"
    assert silver_record["pmc_id"] == "PMC123456"
    assert silver_record["publication_types"] == '["Journal Article"]'
    assert silver_record["subject_keywords"] == '["bioinformatics","drug discovery"]'
    assert silver_record["language"] == "eng"
    assert silver_record["country"] == "United States"
    # Metadata
    assert "_ingestion_ts" in silver_record
    assert silver_record["_run_id"] == str(pipeline_context.run_id)
    assert silver_record["_run_type"] == pipeline_context.run_type.value


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_invalid_xml(pipeline, pipeline_context):
    """Invalid XML must surface validation failure through the pipeline wrapper.

    After refactoring to BasePublicationTransformer pattern:
    - XML parsing happens in _pre_extract_validation
    - ET.ParseError is caught and logged as XML_parse_error
    - Then ValueError is raised, which BaseTransformer logs as
      entity_validation_failed before propagating to the caller
    """
    bronze_record: BronzeRecord = cast(
        "BronzeRecord",
        {"pmid": "12345", "_raw_xml": "<Invalid>XML", "source_batch_id": "test_batch"},
    )

    with pytest.raises(ValueError, match="XML parse error"):
        await pipeline.transform_bronze_to_silver(pipeline_context, bronze_record)
    # Verify warning was logged - unified BasePublicationTransformer pattern
    # logs entity_validation_failed when ValueError is raised from _pre_extract_validation
    args, kwargs = pipeline.logger.warning.call_args
    assert args[0] == "entity_validation_failed"
    assert "error" in kwargs
    # The XML_parse_error is also logged earlier (can check call_args_list if needed)
