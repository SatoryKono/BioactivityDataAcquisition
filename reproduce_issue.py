from dataclasses import asdict, dataclass
from datetime import datetime

# Mock types
RunID = str
RunType = str
EntityID = str
ContentHash = str
BatchID = str

@dataclass(frozen=True, kw_only=True)
class BaseEntity:
    entity_id: EntityID
    content_hash: ContentHash
    run_id: RunID
    run_type: RunType
    ingestion_ts: datetime
    source_batch_id: BatchID | None = None

@dataclass(frozen=True, kw_only=True)
class Activity(BaseEntity):
    activity_id: str
    molecule_chembl_id: str

def test():
    entity = Activity(
        entity_id="ent1",
        content_hash="hash1",
        run_id="run1",
        run_type="incremental",
        ingestion_ts=datetime.now(),
        activity_id="act1",
        molecule_chembl_id="mol1"
    )

    d = asdict(entity)
    print("Dict keys:", d.keys())

    try:
        run_id = d.pop("run_id")
        print("Popped run_id:", run_id)
    except KeyError as e:
        print("KeyError:", e)

if __name__ == "__main__":
    test()
