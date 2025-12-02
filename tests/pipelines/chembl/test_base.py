"""
Tests for ChemblPipelineBase.
"""
# pylint: disable=redefined-outer-name, unused-argument
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from bioetl.domain.models import RunContext
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ConcreteChemblPipeline(ChemblPipelineBase):
    """Concrete implementation for testing."""

    def extract(self, **_):
        """Mock extract implementation."""
        return pd.DataFrame()

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df["transformed"] = True
        return df


@pytest.fixture
def mock_dependencies_fixture():
    """Fixture for pipeline dependencies."""
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
def pipeline_fixture(mock_dependencies_fixture):
    """Fixture for pipeline instance."""
    # Mock config.model_dump()
    mock_dependencies_fixture["config"].model_dump.return_value = {}

    return ConcreteChemblPipeline(
        config=mock_dependencies_fixture["config"],
        logger=mock_dependencies_fixture["logger"],
        validation_service=mock_dependencies_fixture["validation_service"],
        output_writer=mock_dependencies_fixture["output_writer"],
        extraction_service=mock_dependencies_fixture["extraction_service"],
    )


def test_get_chembl_release(pipeline_fixture, mock_dependencies_fixture):
    """Test ChEMBL release version retrieval."""
    # Arrange
    mock_dependencies_fixture[
        "extraction_service"
    ].get_release_version.return_value = "chembl_34"

    # Act
    release1 = pipeline_fixture.get_chembl_release()
    release2 = pipeline_fixture.get_chembl_release()

    # Assert
    assert release1 == "chembl_34"
    assert release2 == "chembl_34"
    # Should be called only once due to caching
    (
        mock_dependencies_fixture["extraction_service"]
        .get_release_version.assert_called_once()
    )


def test_transform_flow(pipeline_fixture):
    """Test transform flow."""
    # Arrange
    df = pd.DataFrame({"a": [1]})

    # Act
    result = pipeline_fixture.transform(df)

    # Assert
    assert "transformed" in result.columns
    assert result.iloc[0]["transformed"]


def test_pre_transform_hook(pipeline_fixture):
    """Test pre-transform hook."""
    # Test default implementation (returns df as is)
    df = pd.DataFrame({"a": [1]})
    result = pipeline_fixture.pre_transform(df)
    pd.testing.assert_frame_equal(df, result)


def test_build_meta(pipeline_fixture, mock_dependencies_fixture):
    """Test metadata building."""
    # Arrange
    mock_dependencies_fixture[
        "extraction_service"
    ].get_release_version.return_value = "chembl_99"
    context = RunContext(
        entity_name="test",
        provider="chembl",
        started_at=datetime.now(timezone.utc)
    )
    df = pd.DataFrame()

    # Act
    # pylint: disable=protected-access
    meta = pipeline_fixture._build_meta(context, df)

    # Assert
    assert meta["chembl_release"] == "chembl_99"
    assert meta["entity"] == "test"
