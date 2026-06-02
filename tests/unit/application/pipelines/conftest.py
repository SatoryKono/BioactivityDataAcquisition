"""Shared pytest fixtures for pipeline unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

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
        run_id=deterministic_uuid_from_callsite("pipelines.conftest"),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )
