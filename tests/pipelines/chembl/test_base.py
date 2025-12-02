import pytest
import pandas as pd
from unittest.mock import MagicMock

from bioetl.pipelines.chembl.base import ChemblPipelineBase
from bioetl.core.models import RunContext
from datetime import datetime, timezone


class TestChemblPipeline(ChemblPipelineBase):
    """Concrete implementation for testing."""

    def extract(self, **kwargs):
        return pd.DataFrame()

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df["transformed"] = True
        return df


@pytest.fixture
def mock_dependencies():
    return {
        "config": MagicMock(
            entity_name="test",
            provider="chembl",
            business_key=[]
        ),
        "logger": MagicMock(),
        "validation_service": MagicMock(),
        "output_writer": MagicMock(),
        "extraction_service": MagicMock(),
    }


@pytest.fixture
def pipeline(mock_dependencies):
    # Mock config.model_dump()
    mock_dependencies["config"].model_dump.return_value = {}

    return TestChemblPipeline(
        config=mock_dependencies["config"],
        logger=mock_dependencies["logger"],
        validation_service=mock_dependencies["validation_service"],
        output_writer=mock_dependencies["output_writer"],
        extraction_service=mock_dependencies["extraction_service"],
    )


def test_get_chembl_release(pipeline, mock_dependencies):
    # Arrange
    mock_dependencies["extraction_service"].get_release_version.return_value = (
        "chembl_34"
    )

    # Act
    release1 = pipeline.get_chembl_release()
    release2 = pipeline.get_chembl_release()

    # Assert
    assert release1 == "chembl_34"
    assert release2 == "chembl_34"
    # Should be called only once due to caching
    (
        mock_dependencies["extraction_service"]
        .get_release_version.assert_called_once()
    )


def test_transform_flow(pipeline):
    # Arrange
    df = pd.DataFrame({"a": [1]})

    # Act
    result = pipeline.transform(df)

    # Assert
    assert "transformed" in result.columns
    assert result.iloc[0]["transformed"] == True


def test_pre_transform_hook(pipeline):
    # Test default implementation (returns df as is)
    df = pd.DataFrame({"a": [1]})
    result = pipeline.pre_transform(df)
    pd.testing.assert_frame_equal(df, result)


def test_build_meta(pipeline, mock_dependencies):
    # Arrange
    mock_dependencies["extraction_service"].get_release_version.return_value = (
        "chembl_99"
    )
    context = RunContext(
        entity_name="test",
        provider="chembl",
        started_at=datetime.now(timezone.utc)
    )
    df = pd.DataFrame()

    # Act
    meta = pipeline._build_meta(context, df)

    # Assert
    assert meta["chembl_release"] == "chembl_99"
    assert meta["entity"] == "test"
