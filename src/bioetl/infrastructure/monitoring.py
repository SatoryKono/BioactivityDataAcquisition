import logging
import json
import sys
from datetime import datetime, timezone

# Rule 3.2.1: Log Schema
# MUST: ts, level, run_id, pipeline, stage
# SHOULD: dataset, record_count

class JsonFormatter(logging.Formatter):
    def __init__(self, run_id: str, pipeline: str):
        super().__init__()
        self.run_id = run_id
        self.pipeline = pipeline

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "run_id": self.run_id,
            "pipeline": self.pipeline,
            "stage": getattr(record, "stage", "unknown"),
            "message": record.getMessage(),
            "logger": record.name
        }

        if hasattr(record, "dataset"):
            log_record["dataset"] = record.dataset
        if hasattr(record, "record_count"):
            log_record["record_count"] = record.record_count
        if hasattr(record, "error_type"):
            log_record["error_type"] = record.error_type

        return json.dumps(log_record)

def configure_logging(pipeline: str, run_id: str, level: int = logging.INFO) -> None:
    root = logging.getLogger()
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(run_id=run_id, pipeline=pipeline)
    handler.setFormatter(formatter)

    # Remove existing handlers to avoid duplication
    root.handlers = []
    root.addHandler(handler)
