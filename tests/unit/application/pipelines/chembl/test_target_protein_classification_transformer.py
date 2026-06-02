"""Unit tests for ChEMBL target protein-classification relation transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.pipelines.chembl.target_protein_classification_transformer import (
    TargetProteinClassificationTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies

pytestmark = pytest.mark.repo_backed


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a minimal pipeline context for transformer tests."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite(
            "test_target_protein_classification_transformer"
        ),
        run_type=RunType.INCREMENTAL,
        logger=logger,
    )


@pytest.fixture
def transformer() -> TargetProteinClassificationTransformer:
    """Create the target protein-classification transformer."""
    return TargetProteinClassificationTransformer(
        provider="chembl",
        dependencies=build_test_transformer_dependencies(),
    )


@pytest.mark.asyncio
async def test_transform_preserves_shaped_relation_row_identity(
    transformer: TargetProteinClassificationTransformer,
    mock_context: PipelineContext,
) -> None:
    record = {
        "target_id": "CHEMBL123",
        "component_id": "10",
        "leaf_id": "148",
        "l1_id": "1",
        "l1_name": "Membrane receptor",
        "classification_status": "resolved",
    }

    result = await transformer.transform(mock_context, record, index=0)

    assert result is not None
    assert result["entity_id"] == "CHEMBL123:10:148"
    assert result["target_id"] == "CHEMBL123"
    assert result["component_id"] == 10
    assert result["leaf_id"] == "148"
    assert result["classification_status"] == "resolved"


@pytest.mark.asyncio
async def test_transform_defaults_missing_status_to_missing_classification(
    transformer: TargetProteinClassificationTransformer,
    mock_context: PipelineContext,
) -> None:
    result = await transformer.transform(
        mock_context,
        {"target_id": "CHEMBL123"},
        index=0,
    )

    assert result is not None
    assert result["entity_id"] == "CHEMBL123:missing_classification"
    assert result["classification_status"] == "missing_classification"
