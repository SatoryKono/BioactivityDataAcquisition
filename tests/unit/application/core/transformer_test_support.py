# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Shared fixtures for batch and streaming transformer tests."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_transformer import BatchTransformer
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.types import RunType


@pytest.fixture
def mock_context():
    """Create mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite("transformer_test_support"),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_error_classifier():
    """Create error classifier."""
    return ErrorClassifier()


@pytest.fixture
def mock_quarantine_manager():
    """Create mock quarantine manager."""
    manager = MagicMock(spec=QuarantineRuntimeService)
    manager.quarantine_record = AsyncMock()
    manager.quarantine_records = AsyncMock()
    manager.quarantine_filtered_record = AsyncMock()
    manager.quarantine_filtered_records = AsyncMock()
    return manager


@pytest.fixture
def mock_batch_metrics():
    """Create mock batch metrics recorder."""
    return MagicMock(spec=BatchMetricsRecorder)


@pytest.fixture
def transform_callback():
    """Create shared transform callback."""

    async def transform(ctx, record, index):
        await asyncio.sleep(0)
        return {"entity_id": record.get("id", "unknown"), "value": record.get("value")}

    return transform


@pytest.fixture
def gold_filter_callback():
    """Create shared gold filter callback."""

    def filter_gold(ctx, record):
        return record.get("value", 0) > 5

    return filter_gold


@pytest.fixture
def gold_transform_callback():
    """Create shared gold transform callback."""

    def transform_gold(ctx, record):
        return record

    return transform_gold


@pytest.fixture
def batch_transformer(
    mock_context,
    mock_error_classifier,
    mock_quarantine_manager,
    mock_batch_metrics,
    transform_callback,
    gold_filter_callback,
    gold_transform_callback,
):
    """Create shared BatchTransformer instance."""
    config = RecordProcessorConfig(
        pipeline_name="test_provider_test_entity",
        provider="test_provider",
        entity_type="test_entity",
        silver_schema=MagicMock(),
        gold_schema=MagicMock(),
    )
    return BatchTransformer(
        context=mock_context,
        config=config,
        error_classifier=mock_error_classifier,
        quarantine_manager=mock_quarantine_manager,
        batch_metrics=mock_batch_metrics,
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        gold_transform_callback=gold_transform_callback,
    )
