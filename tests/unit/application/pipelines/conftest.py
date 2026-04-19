"""Shared pytest fixtures for pipeline unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def transformer() -> ActivityTransformer:
    """Create the default ActivityTransformer used by shared pipeline tests."""
    return ActivityTransformer(
        provider="chembl",
        dependencies=build_test_transformer_dependencies(),
    )


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context with a bound logger."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )
