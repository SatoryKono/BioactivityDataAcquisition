
from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.domain.medallion import SilverWriteMode

def verify_operation_map():
    # Just check if we can import and if the method has the map (by inspection or running it)
    # We will try to run create_silver_metadata
    from bioetl.domain.value_objects.run_context import RunContext
    from bioetl.domain.types import RunType, RunID
    from bioetl.composition.services.metadata_coordinator import SilverMetadataInput
    from datetime import datetime, UTC
    from uuid import uuid4

    ctx = RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        provider="p",
        entity="e"
    )
    coord = MetadataCoordinator(ctx)
    input_data = SilverMetadataInput(
        table_path="t",
        records=[{"id": 1}],
        primary_keys=["id"],
        mode=SilverWriteMode.MERGE
    )
    try:
        coord.create_silver_metadata(input_data)
        print("Success: operation_map is working")
    except NameError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Other Error: {e}")

if __name__ == "__main__":
    verify_operation_map()
