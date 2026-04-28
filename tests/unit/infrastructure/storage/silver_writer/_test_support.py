"""Shared support helpers for split ``SilverWriter`` unit tests."""

from __future__ import annotations

import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pyarrow as pa
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-silver-writer-tests-"))
SILVER_BASE_PATH = TEST_ROOT / "silver"


def make_silver_writer(
    *,
    logger: object,
    base_path: str | Path | None = None,
    **kwargs: Any,
) -> object:
    """Build a ``SilverWriter`` with the standard test base path."""
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

    return SilverWriter(
        base_path=str(SILVER_BASE_PATH if base_path is None else base_path),
        logger=logger,
        **kwargs,
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
