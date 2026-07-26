"""Request building helpers for Gold writer."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.types import GoldRecord, RunID, ScdConfig
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.gold.pipeline_helpers import GoldWriteRequest

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

__all__ = ["_build_gold_write_request"]


def _build_gold_write_request(
    *,
    table_name: str,
    records: list[GoldRecord],
    schema: DataFrameSchema,
    primary_keys: list[str] | None,
    mode: str,
    partition_cols: list[str] | None,
    scd_config: ScdConfig | None,
    column_order: list[str] | None,
    ingestion_ts: datetime | None,
    run_id: RunID | None,
    silver_refs: list[SilverWriteResult] | None,
    contract_version: str | None = None,
) -> GoldWriteRequest:
    """Build the canonical Gold write request."""
    return GoldWriteRequest(
        table_name=table_name,
        records=records,
        schema=schema,
        primary_keys=primary_keys,
        mode=mode,
        partition_cols=partition_cols,
        scd_config=scd_config,
        column_order=column_order,
        ingestion_ts=ingestion_ts,
        run_id=run_id,
        silver_refs=silver_refs,
        contract_version=contract_version,
    )
