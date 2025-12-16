"""In-memory storage for integration tests."""
from collections import defaultdict

from bioetl.domain.ports import StoragePort


class MemoryStorage(StoragePort):
    def __init__(self):
        self.data = defaultdict(list)

    def write_bronze(self, records, provider, entity, date, batch_id):
        key = f"bronze/{provider}/{entity}/{date}/{batch_id}.jsonl.zst"
        self.data[key].extend(records)

    def write_silver(self, table_name, records, _primary_keys):
        self.data[table_name].extend(records)

    def write_gold(self, table_name, records, _mode):
        self.data[table_name].extend(records)
