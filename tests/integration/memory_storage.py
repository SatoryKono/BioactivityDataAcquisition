"""In-memory storage for integration tests."""
from collections import defaultdict

from bioetl.domain.ports import StoragePort


class MemoryStorage(StoragePort):
    def __init__(self):
        self.data = defaultdict(list)
        self.metadata = {}  # Store run_id/run_type for verification

    def write_bronze(self, records, provider, entity, date, batch_id, run_id=None, run_type=None):
        key = f"bronze/{provider}/{entity}/{date}/{batch_id}.jsonl.zst"
        self.data[key].extend(records)
        # Store metadata for test verification
        if run_id is not None:
            self.metadata[key] = {"run_id": str(run_id), "run_type": run_type.value if run_type else None}

    def write_silver(self, table_name, records, _primary_keys):
        self.data[table_name].extend(records)

    def write_gold(self, table_name, records, _mode):
        self.data[table_name].extend(records)
