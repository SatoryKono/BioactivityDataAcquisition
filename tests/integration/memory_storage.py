# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""In-memory storage for integration tests."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path


class MemoryStorage:
    def __init__(self):
        self.data = defaultdict(list)
        self.bronze_metadata = {}  # Store run metadata for verification

    def write_bronze(
        self, records, provider, entity, date, batch_id, run_id, run_type, ingestion_ts
    ) -> Path:
        key = f"bronze/{provider}/{entity}/{date}/{batch_id}.jsonl.zst"
        self.data[key].extend(records)
        # Store metadata for test verification
        self.bronze_metadata[key] = {
            "run_id": str(run_id),
            "run_type": run_type.value if hasattr(run_type, "value") else str(run_type),
            "ingestion_ts": ingestion_ts.isoformat() if ingestion_ts else None,
        }
        return Path(key)

    def write_silver(self, table_name, records, _primary_keys):
        self.data[table_name].extend(records)

    def write_gold(self, table_name, records, _schema, _mode):
        self.data[table_name].extend(records)
