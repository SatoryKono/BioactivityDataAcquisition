import asyncio
import os
import shutil
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
from deltalake import DeltaTable

from bioetl.infrastructure.storage.delta_writer import DeltaWriter, SilverWriteMode
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.domain.medallion import WriteModePolicy
import structlog

# Setup logger
logger = structlog.get_logger()

async def reproduce():
    base_path = Path("temp_storage/silver")
    if base_path.exists():
        shutil.rmtree(base_path)
    base_path.mkdir(parents=True)

    writer = DeltaWriter(
        base_path=base_path,
        logger=logger,
        tracing=NoOpTracing(),
        metrics=NoOpMetrics(),
        write_policy=WriteModePolicy()
    )

    # Define schema matching the error
    schema = pa.schema([
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("activity_id", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ])

    # Create a record with list values (simulating the error condition)
    # The error message shows:
    # entity_id: [["chembl:31872"]]
    # This suggests the data passed to PyArrow table creation is a list of lists,
    # or the column is being interpreted as a list of strings instead of string.

    # Let's try to pass data that might cause this.
    # If we pass a list of dicts where values are lists, PyArrow might infer list type.

    records = [
        {
            "entity_id": ["chembl:31872"],  # List instead of string
            "content_hash": ["hash123"],
            "activity_id": ["31872"],
            "_run_id": ["run1"],
            "_run_type": ["incremental"],
            "_source_batch_id": ["batch1"],
            "_ingestion_ts": ["2024-01-01"],
        }
    ]

    # But wait, the error says:
    # pyarrow.lib.ArrowInvalid: Invalid sort key column: No match for FieldRef.Name(id) in entity_id: string
    # Actually, looking closer at the error log in the prompt:
    # E   pyarrow.lib.ArrowInvalid: Invalid sort key column: No match for FieldRef.Name(id) in entity_id: string
    # ...
    # E   entity_id:
    # E     [
    # E       [
    # E         "chembl:31872"
    # E       ]
    # E     ]

    # The error "No match for FieldRef.Name(id)" is weird because the primary key is "activity_id" in config.
    # Wait, the error says "No match for FieldRef.Name(id)".
    # Is it possible that `primary_keys` passed to `write_silver` contains "id"?

    # Let's check `configs/pipelines/chembl/activity.yaml`:
    # primary_keys: ["activity_id"]
    # silver_table: "chembl_activity"
    # sink:
    #   silver:
    #     primary_key: ["activity_id"]

    # In `BatchWriter.write_silver`:
    # await self._storage.write_silver(
    #     ...
    #     primary_keys=list(self._table_config.primary_keys),
    #     ...
    # )

    # `self._table_config` comes from `RecordProcessorConfig`.
    # `RecordProcessorConfig` comes from `pipeline.config`.
    # `pipeline.config` comes from `yaml_config_to_domain`.

    # In `yaml_config_to_domain`:
    # return PipelineConfig(
    #     ...
    #     primary_keys=tuple(yaml_config.primary_keys),
    #     ...
    # )

    # In `PipelineYamlConfig`:
    # primary_keys: list[str] = Field(min_length=1)

    # So primary_keys should be ["activity_id"].

    # However, the error message:
    # E   pyarrow.lib.ArrowInvalid: Invalid sort key column: No match for FieldRef.Name(id) in entity_id: string

    # This implies that something is trying to sort by "id".

    # Let's look at `DeltaWriter._prepare_arrow_data`:
    # if primary_keys:
    #     arrow_data = arrow_data.sort_by([(pk, "ascending") for pk in primary_keys])

    # If `primary_keys` contained "id", and the schema doesn't have "id", this error would happen.
    # But the schema has "activity_id", "entity_id", etc.

    # Wait, look at the error again.
    # "No match for FieldRef.Name(id) in entity_id: string"
    # It lists all columns. "id" is NOT in the list of columns.
    # So it confirms that "id" is being requested as a sort key.

    # Where does "id" come from?
    # Maybe `input_filter` config?
    # input_filter:
    #   column_name: "activity_id"

    # Maybe `_table_config.primary_keys` has "id"?

    print("Reproducing...")
    try:
        # Simulate the call with "id" as primary key to see if it produces the same error
        await writer.write_silver(
            table_name="test_table",
            records=[{
                "entity_id": "chembl:31872",
                "content_hash": "hash",
                "activity_id": "31872",
                "_run_id": "run1",
                "_run_type": "incremental",
                "_source_batch_id": "batch1",
                "_ingestion_ts": "2024-01-01T00:00:00",
            }],
            primary_keys=["id"],  # INTENTIONALLY WRONG KEY
            schema=schema,
            mode="merge"
        )
    except Exception as e:
        print(f"Caught expected exception: {e}")

if __name__ == "__main__":
    asyncio.run(reproduce())
