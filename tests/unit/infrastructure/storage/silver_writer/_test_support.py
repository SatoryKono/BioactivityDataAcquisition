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
"""Shared support helpers for split ``SilverWriter`` unit tests."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pyarrow as pa
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

if TYPE_CHECKING:
    from bioetl.infrastructure.storage.silver.runtime_helpers import (
        SilverWriterRuntimeServices,
        SilverWriterRuntimeServicesRequest,
    )

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-silver-writer-tests-"))
SILVER_BASE_PATH = TEST_ROOT / "silver"


def make_silver_writer(
    *,
    logger: object,
    base_path: str | Path | None = None,
    runtime_services: SilverWriterRuntimeServices | None = None,
    runtime_request: SilverWriterRuntimeServicesRequest | None = None,
    flat_structure: bool = False,
    pipeline_name: str | None = None,
) -> object:
    """Build a ``SilverWriter`` with the standard test base path."""
    from bioetl.infrastructure.storage.silver.runtime_helpers import (
        SilverWriterRuntimeServicesRequest,
    )
    from bioetl.infrastructure.storage.silver_writer import SilverWriter
    from bioetl.infrastructure.validation.pandera_validator import NoOpValidator

    if runtime_services is None and runtime_request is None:
        runtime_request = SilverWriterRuntimeServicesRequest(
            logger=logger,  # type: ignore[arg-type]
            silver_validator=NoOpValidator(),
        )
    elif runtime_request is not None and runtime_request.silver_validator is None:
        runtime_request = SilverWriterRuntimeServicesRequest(
            csv_exporter=runtime_request.csv_exporter,
            tracing=runtime_request.tracing,
            write_policy=runtime_request.write_policy,
            metrics=runtime_request.metrics,
            audit=runtime_request.audit,
            logger=runtime_request.logger or logger,  # type: ignore[arg-type]
            silver_validator=NoOpValidator(),
            metadata_writer=runtime_request.metadata_writer,
            metadata_coordinator=runtime_request.metadata_coordinator,
            lineage_store=runtime_request.lineage_store,
            dq_calculator=runtime_request.dq_calculator,
            merge_resilience_policy=runtime_request.merge_resilience_policy,
            contract_rollout_policy=runtime_request.contract_rollout_policy,
            base_path=runtime_request.base_path,
            pipeline_name=runtime_request.pipeline_name,
            delta_module_loader=runtime_request.delta_module_loader,
        )

    return SilverWriter(
        base_path=str(SILVER_BASE_PATH if base_path is None else base_path),
        logger=logger,
        runtime_services=runtime_services,
        runtime_request=runtime_request,
        flat_structure=flat_structure,
        pipeline_name=pipeline_name,
    )


def silver_table_path(table_name: str, *, base_path: str | Path | None = None) -> str:
    """Resolve a Silver table path under the standard test root."""
    resolved_base_path = SILVER_BASE_PATH if base_path is None else Path(base_path)
    return str(resolved_base_path / table_name.replace(".", "/"))


def silver_write_schema() -> pa.Schema:
    """Return the standard Arrow schema used by many Silver write tests."""
    return pa.schema(
        [
            pa.field("entity_id", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )


async def write_standard_silver(
    writer: object,
    *,
    table_name: str = "test.table",
    records: list[dict[str, object]],
    mode: str,
) -> object:
    """Execute the canonical Silver test write call shared across unit tests."""
    return await writer.write_silver(
        table_name=table_name,
        records=records,
        primary_keys=["entity_id"],
        schema=silver_write_schema(),
        mode=mode,
    )


async def assert_standard_silver_write_succeeds(
    writer: object,
    *,
    records: list[dict[str, object]],
    mode: str,
) -> None:
    """Assert the canonical Silver test write reaches the Delta write path."""
    with patch_new_silver_write() as mock_write:
        await write_standard_silver(
            writer,
            records=records,
            mode=mode,
        )
        mock_write.assert_called_once()


@contextmanager
def patch_new_silver_write(
    *,
    patch_base_delta_table: bool = False,
    patch_writer_delta_table: bool = True,
) -> Iterator[MagicMock]:
    """Patch the new-table Silver write path and yield ``write_deltalake`` mock."""
    with ExitStack() as stack:
        if patch_base_delta_table:
            stack.enter_context(
                patch(
                    "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                    side_effect=DeltaTableNotFoundError("Not found"),
                )
            )
        if patch_writer_delta_table:
            stack.enter_context(
                patch(
                    "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                    side_effect=DeltaTableNotFoundError("Not found"),
                )
            )
        mock_write = stack.enter_context(
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake")
        )
        yield mock_write
