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
"""Unit tests for NoOpMetadataWriter behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.models.metadata import (
    DeltaMetrics,
    EnvironmentMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SilverMetadata,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter


@pytest.mark.unit
class TestNoOpMetadataWriter:
    """Tests for NoOpMetadataWriter behavior."""

    @pytest.mark.asyncio
    async def test_noop_returns_empty_string(self) -> None:
        """NoOp metadata writer should return empty artifact paths."""
        noop = NoOpMetadataWriter()
        metadata = SilverMetadata(
            runtime=RuntimeMetadata(
                run_id="test",
                run_type=RunTypeEnum.INCREMENTAL,
                started_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            ),
            pipeline=PipelineMetadata(name="test", provider="test", entity="test"),
            delta=DeltaMetrics(table_path="/test", operation="merge"),
            environment=EnvironmentMetadata(
                hostname="test",
                python_version="3.11",
                bioetl_version="1.0",
            ),
        )

        result = await noop.write_silver_metadata("test-output/silver/test", metadata)
        assert result == ""
