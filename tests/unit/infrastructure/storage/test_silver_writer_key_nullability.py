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
"""Tests for SilverWriter key nullability policy validation."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pyarrow as pa
import pytest

from bioetl.domain.config import KeyNullabilityRule
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.silver_writer import SilverWriter

TEST_SILVER_ROOT = "test-output/silver"


@pytest.mark.unit
class TestSilverWriterKeyNullability:
    """Validate merge/partition key nullability policies."""

    @pytest.mark.asyncio
    async def test_non_nullable_merge_key_rejects_null(self) -> None:
        """Non-null merge key policy must reject records with null merge key."""
        writer = SilverWriter(base_path=TEST_SILVER_ROOT, logger=NoOpLogger())
        writer._dispatch_write_with_domain_errors = AsyncMock()  # type: ignore[method-assign]

        records = [
            {
                "entity_id": None,
                "region": "eu",
                "_run_id": "run-1",
                "_run_type": "incremental",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2025-01-01T00:00:00Z",
            }
        ]
        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("region", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        with pytest.raises(ValueError, match="Key nullability policy violation"):
            await writer.write_silver(
                table_name="test_table",
                records=records,
                primary_keys=["entity_id"],
                schema=schema,
                partition_cols=["region"],
                key_nullability_rules=[
                    KeyNullabilityRule(
                        field="entity_id", key_type="merge", nullable=False
                    )
                ],
            )

    @pytest.mark.asyncio
    async def test_nullable_partition_key_allows_null(self) -> None:
        """Nullable partition key policy should allow null partition values."""
        writer = SilverWriter(base_path=TEST_SILVER_ROOT, logger=NoOpLogger())

        writer._dispatch_write_with_domain_errors = AsyncMock(return_value=None)  # type: ignore[method-assign]
        writer._get_delta_version = AsyncMock(return_value=1)  # type: ignore[assignment]
        writer._get_table_schema = AsyncMock(return_value=None)  # type: ignore[assignment]

        records = [
            {
                "entity_id": "e1",
                "region": None,
                "_run_id": "run-1",
                "_run_type": "incremental",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2025-01-01T00:00:00Z",
            }
        ]
        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("region", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        result = await writer.write_silver(
            table_name="test_table",
            records=records,
            primary_keys=["entity_id"],
            schema=schema,
            partition_cols=["region"],
            key_nullability_rules=[
                KeyNullabilityRule(field="entity_id", key_type="merge", nullable=False),
                KeyNullabilityRule(field="region", key_type="partition", nullable=True),
            ],
        )

        assert result is not None
