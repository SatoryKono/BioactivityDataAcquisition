"""Read the Silver snapshot explicitly published by an upstream workflow run."""

from __future__ import annotations

import asyncio
from pathlib import Path

import yaml
from deltalake import DeltaTable


class WorkflowCohortSnapshotReader:
    """Fail closed when retained snapshot provenance or row coverage differs."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = Path(base_path)

    async def read_run_identities(
        self, table: str, pipeline: str, run_id: str, expected_count: int
    ) -> dict[str, str]:
        def read() -> dict[str, str]:
            path = (self.base_path / table.replace(".", "/", 1)).resolve()
            if not path.is_relative_to(self.base_path.resolve()):
                raise ValueError("reference cohort table is outside storage root")
            metadata = yaml.safe_load((path / f"{pipeline}_metadata.yaml").read_text())
            if (
                metadata["runtime"]["run_id"] != run_id
                or metadata["pipeline"]["name"] != pipeline
            ):
                raise ValueError("reference cohort snapshot producer mismatch")
            version = metadata["output_ext"]["delta_version_after"]
            if not isinstance(version, int) or version < 0:
                raise ValueError("reference cohort snapshot version missing")
            snapshot = DeltaTable(str(path), version=version).to_pyarrow_table(
                columns=["entity_id", "content_hash"]
            )
            if (
                snapshot.num_rows != expected_count
                or metadata["output"]["record_count"] != expected_count
            ):
                raise ValueError(
                    "reference cohort snapshot contains a different row universe"
                )
            rows = snapshot.to_pylist()
            identities = {
                str(row["entity_id"]): str(row["content_hash"]) for row in rows
            }
            if len(identities) != len(rows):
                raise ValueError("reference cohort snapshot has duplicate identities")
            return identities

        return await asyncio.to_thread(read)
