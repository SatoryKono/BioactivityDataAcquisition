from dataclasses import dataclass, asdict
from datetime import datetime
from typing import NewType

RunID = NewType("RunID", str)
RunType = NewType("RunType", str)
EntityID = NewType("EntityID", str)
ContentHash = NewType("ContentHash", str)
BatchID = NewType("BatchID", str)

@dataclass(frozen=True, kw_only=True, slots=True)
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
        entity_id=EntityID("1"),
        content_hash=ContentHash("hash"),
        run_id=RunID("run1"),
        run_type=RunType("incremental"),
        ingestion_ts=datetime.now(),
        activity_id="act1",
        molecule_chembl_id="mol1"
    )

    d = asdict(entity)
    print("Keys in asdict:", d.keys())
    if "run_id" in d:
        print("run_id is present")
    else:
        print("run_id is MISSING")

if __name__ == "__main__":
    test()
