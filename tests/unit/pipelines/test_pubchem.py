import pytest
from unittest.mock import MagicMock
from bioetl.application.pipelines.pubchem.compound import PubChemCompoundPipeline
from bioetl.domain.context import PipelineContext
from bioetl.application.core.pipeline_config import PipelineRuntimeConfig
from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.application.core.pipeline_services import PipelineServices


@pytest.fixture
def pipeline():
    config = MagicMock()
    runtime = MagicMock()
    services = MagicMock()
    services.logger.bind.return_value = MagicMock()

    # Mocks for BasePipeline.__init__
    config.pipeline_name = "pubchem"
    config.dataset_name = "compound"
    config.provider = "pubchem"
    runtime.run_type = "batch" # Mock run_type

    return PubChemCompoundPipeline(config=config, runtime=runtime, services=services)


@pytest.fixture
def context():
    ctx = MagicMock(spec=PipelineContext)
    ctx.run_id = "run_123"
    return ctx


def test_create_pipeline():
    """Test pipeline factory method."""
    runtime = MagicMock()
    runtime.run_type = "batch" # Mock run_type
    services = MagicMock()
    services.logger.bind.return_value = MagicMock()
    config = MagicMock() # Relax spec to allow attributes
    config.pipeline_name = "pubchem"
    config.dataset_name = "compound"
    config.provider = "pubchem"

    pipeline = PubChemCompoundPipeline.create(runtime, services, config)
    assert isinstance(pipeline, PubChemCompoundPipeline)


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_valid(pipeline, context):
    """Test transformation with a complete record."""
    record = {
        "cid": 12345,
        "molecular_formula": "C6H12O6",
        "molecular_weight": 180.16,
        "canonical_smiles": "CCCCCC",
        "isomeric_smiles": "CCCCCC",
        "inchi": "InChI=1S/...",
        "inchikey": "KEY123",
        "iupac_name": "Hexane",
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result["cid"] == "12345"  # CID is now string
    assert result["molecular_formula"] == "C6H12O6"
    assert result["molecular_weight"] == 180.16
    assert result["canonical_smiles"] == "CCCCCC"
    assert result["isomeric_smiles"] == "CCCCCC"
    assert result["inchi"] == "InChI=1S/..."
    assert result["inchikey"] == "KEY123"
    assert result["iupac_name"] == "Hexane"
    assert "entity_id" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_missing_fields(pipeline, context):
    """Test transformation with missing optional fields."""
    record = {
        "cid": 67890
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result["cid"] == "67890"  # CID is now string
    assert result["molecular_formula"] is None
    assert result["molecular_weight"] is None
    assert result["canonical_smiles"] is None
    assert "entity_id" in result
    assert "content_hash" in result


@pytest.mark.asyncio
async def test_transform_bronze_to_silver_missing_cid(pipeline, context):
    """Test transformation returns None when CID is missing."""
    record = {
        "molecular_formula": "C6H12O6",
    }

    result = await pipeline.transform_bronze_to_silver(context, record)

    assert result is None


def test_extract_watermark(pipeline, context):
    """Test watermark extraction."""
    from bioetl.domain.types import Watermark

    record = {"cid": 999}
    watermark = pipeline.extract_watermark(context, record)

    assert isinstance(watermark, Watermark)
    assert watermark.value == 999


def test_extract_watermark_default(pipeline, context):
    """Test watermark extraction when cid is missing."""
    from bioetl.domain.types import Watermark

    record = {}
    watermark = pipeline.extract_watermark(context, record)

    assert isinstance(watermark, Watermark)
    assert watermark.value == 0
