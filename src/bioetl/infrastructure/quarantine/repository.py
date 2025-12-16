"""Quarantine repository for Delta Lake access.

Handles I/O operations for quarantine data.
"""
from datetime import datetime, timedelta, UTC
from typing import Any

from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError
import pyarrow.compute as pc

from bioetl.domain.types import DQStatus
from bioetl.infrastructure.quarantine.model import QuarantineRecord


class QuarantineRepository:
    """Access layer for Quarantine Delta Table."""

    def __init__(self, base_path: str, storage_options: dict[str, str] | None = None) -> None:
        self.base_path = base_path
        self.storage_options = storage_options or {}

    def save(self, record: QuarantineRecord) -> None:
        """Save a single record to the repository."""
        data = [record.to_dict()]
        try:
            write_deltalake(
                table_or_uri=self.base_path,
                data=data,
                mode="append",
                storage_options=self.storage_options,
            )
        except TableNotFoundError:
            write_deltalake(
                table_or_uri=self.base_path,
                data=data,
                mode="append",
                partition_by=["pipeline"],
                storage_options=self.storage_options,
            )

    def find_records(
        self,
        pipeline: str,
        limit: int = 100,
        error_code: str | None = None,
        dq_status: DQStatus | None = None,
        max_age_days: int | None = None,
        sort_descending: bool = True
    ) -> list[dict[str, Any]]:
        """Find records matching criteria."""
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            return []

        arrow_table = dt.to_pyarrow_table()
        mask = pc.equal(arrow_table["pipeline"], pipeline)

        if error_code:
            mask = pc.and_(mask, pc.equal(arrow_table["error_code"], error_code))

        if dq_status:
            mask = pc.and_(mask, pc.equal(arrow_table["dq_status"], dq_status.value))

        if max_age_days:
            cutoff_date = (datetime.now(UTC) - timedelta(days=max_age_days)).isoformat()
            age_mask = pc.greater_equal(arrow_table["ingestion_ts"], cutoff_date)
            mask = pc.and_(mask, age_mask)

        filtered_table = arrow_table.filter(mask)

        sort_order = "descending" if sort_descending else "ascending"
        filtered_table = filtered_table.sort_by([("ingestion_ts", sort_order)])

        if limit > 0:
            filtered_table = filtered_table.slice(length=limit)

        return filtered_table.to_pylist()

    def delete_older_than(self, pipeline: str, cutoff_date: str) -> int:
        """Delete records older than cutoff date."""
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            return 0

        predicate = f"pipeline = '{pipeline}' AND ingestion_ts < '{cutoff_date}'"

        # Count before delete
        arrow_table = dt.to_pyarrow_table()
        mask = pc.and_(
            pc.equal(arrow_table["pipeline"], pipeline),
            pc.less(arrow_table["ingestion_ts"], cutoff_date),
        )
        count_before = pc.sum(pc.cast(mask, "int64")).as_py()

        dt.delete(predicate)
        return count_before or 0

    def update_status(self, payload_hash: str, new_status: DQStatus) -> bool:
        """Update status for a specific payload hash."""
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            return False

        predicate = f"payload_hash = '{payload_hash}'"

        # Check existence
        arrow_table = dt.to_pyarrow_table()
        mask = pc.equal(arrow_table["payload_hash"], payload_hash)
        if pc.sum(pc.cast(mask, "int64")).as_py() == 0:
            return False

        dt.update(
            updates={"dq_status": f"'{new_status.value}'"},
            predicate=predicate,
        )
        return True

    def get_dataframe(self, pipeline: str): # Returns pandas DF
        """Get all records for a pipeline as pandas DataFrame."""
        try:
            dt = DeltaTable(self.base_path, storage_options=self.storage_options)
        except TableNotFoundError:
            return None

        arrow_table = dt.to_pyarrow_table()
        mask = pc.equal(arrow_table["pipeline"], pipeline)
        filtered = arrow_table.filter(mask)

        if len(filtered) == 0:
            return None

        return filtered.to_pandas()
