
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator, GoldMetadataInput
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.domain.types import RunType, RunID
from bioetl.domain.medallion import GoldWriteMode
from datetime import datetime, UTC
from uuid import uuid4

def main():
    ctx = RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        provider="p",
        entity="e"
    )
    coord = MetadataCoordinator(ctx)
    input_data = GoldMetadataInput(
        table_path="t",
        table_name="t",
        records=[{"id": 1}],
        mode=GoldWriteMode.OVERWRITE
    )
    meta = coord.create_gold_metadata(input_data)
    print(f"Gold Total Bytes: {meta.output.total_bytes}")
    print(f"Gold Output Ext Total Bytes: {meta.output.output_ext['gold']['total_bytes']}")

if __name__ == "__main__":
    main()
