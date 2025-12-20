import pytest
from unittest.mock import MagicMock
from bioetl.application.pipelines.uniprot.protein import UniProtProteinPipeline
from bioetl.domain.context import PipelineContext
from bioetl.domain.config import PipelineRuntimeConfig
from bioetl.domain.config import PipelineConfig
from bioetl.application.core.pipeline_services import PipelineServices


@pytest.fixture
def pipeline():
    config = MagicMock()
    runtime = MagicMock()
    services = MagicMock()
    services.logger.bind.return_value = MagicMock()

    # Mocks for BasePipeline.__init__
    config.pipeline_name = "uniprot"
    config.dataset_name = "protein"
    config.provider = "uniprot"
    runtime.run_type = "batch"

    return UniProtProteinPipeline(config=config, runtime=runtime, services=services)


@pytest.fixture
def context():
    ctx = MagicMock(spec=PipelineContext)
    ctx.run_id = "run_456"
    return ctx


def test_create_pipeline():
    """Test pipeline factory method."""
    runtime = MagicMock()
    runtime.run_type = "batch"
    services = MagicMock()
    services.logger.bind.return_value = MagicMock()
    config = MagicMock() # Relax spec to allow attributes
    config.pipeline_name = "uniprot"
    config.dataset_name = "protein"
    config.provider = "uniprot"

    pipeline = UniProtProteinPipeline.create(runtime, services, config)
    assert isinstance(pipeline, UniProtProteinPipeline)


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_valid(pipeline, context):
    """Test transformation with a complete record."""
    record = {
        "primaryAccession": "P12345",
        "uniProtkbId": "PROT_HUMAN",
        "proteinDescription": {
            "recommendedName": {
                "fullName": {
                    "value": "Protein A"
                }
            }
        },
        "genes": [
            {
                "geneName": {
                    "value": "GENE1"
                }
            },
            {
                "geneName": {
                    "value": "GENE2"
                }
            }
        ],
        "organism": {
            "taxonId": 9606
        },
        "sequence": {
            "length": 300
        }
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result["accession"] == "P12345"
    assert result["entry_name"] == "PROT_HUMAN"
    assert result["protein_name"] == "Protein A"
    assert result["gene_names"] == ["GENE1", "GENE2"]
    assert result["organism_id"] == 9606
    assert result["sequence_length"] == 300
    assert "entity_id" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_minimal(pipeline, context):
    """Test transformation with minimal data (missing nested fields)."""
    record = {
        "primaryAccession": "P67890"
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result["accession"] == "P67890"
    assert result["entry_name"] is None
    assert result["protein_name"] is None
    assert result["gene_names"] == []
    assert result["organism_id"] is None
    assert result["sequence_length"] is None
    assert "entity_id" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_malformed_nested(pipeline, context):
    """Test transformation with malformed nested structures."""
    record = {
        "primaryAccession": "P99999",
        # Malformed proteinDescription (missing recommendedName)
        "proteinDescription": {
            "somethingElse": {}
        },
        # Malformed genes (missing geneName)
        "genes": [
            {
                "wrongKey": "value"
            }
        ]
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result["accession"] == "P99999"
    assert result["protein_name"] is None
    assert result["gene_names"] == []
    assert "entity_id" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_exceptions(pipeline, context):
    """Test transformation exception handling in helper methods."""
    record = {
        "primaryAccession": "P_ERR",
        "proteinDescription": None,
        "genes": None
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result["accession"] == "P_ERR"
    assert result["protein_name"] is None
    assert result["gene_names"] == []
    assert "entity_id" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_organism_none(pipeline, context):
    """Test transformation when organism is explicitly None."""
    record = {
        "primaryAccession": "P_ORG_NONE",
        "organism": None,
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result["accession"] == "P_ORG_NONE"
    assert result["organism_id"] is None
    assert "entity_id" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_missing_accession(pipeline, context):
    """Test transformation returns None when accession is missing."""
    record = {
        "uniProtkbId": "PROT_HUMAN",
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result is None


def test_extract_watermark(pipeline, context):
    """Test watermark extraction."""
    from bioetl.domain.types import Watermark

    record = {"primaryAccession": "P12345"}
    watermark = pipeline.extract_watermark(context, record)

    assert isinstance(watermark, Watermark)
    assert watermark.value == "P12345"


def test_extract_watermark_default(pipeline, context):
    """Test watermark extraction when accession is missing."""
    from bioetl.domain.types import Watermark

    record = {}
    watermark = pipeline.extract_watermark(context, record)

    assert isinstance(watermark, Watermark)
    assert watermark.value == ""
