"""Tests for CSV record source implementation.

CsvRecordSourceImpl returns raw dicts per RecordSourceABC contract.
Domain model conversion should happen via RecordMapperABC in ExtractStage.
"""
from pathlib import Path
from typing import cast

import pandas as pd

from bioetl.application.files.csv_record_source import CsvRecordSourceImpl
from bioetl.domain.configs import CsvInputConfig
from bioetl.domain.observability import LoggingPortABC


def test_csv_record_source_reads_full_dataset(tmp_path):
    """CsvRecordSourceImpl returns raw dicts, not domain models."""
    csv = tmp_path / "data.csv"
    pd.DataFrame({"a": [1, 2], "b": ["x", "y"]}).to_csv(csv, index=False)

    src = CsvRecordSourceImpl(
        input_path=Path(csv),
        csv_options=CsvInputConfig(),
        limit=None,
        logger=cast(LoggingPortABC, type("L", (), {"info": lambda *_: None}))(),
    )

    batches = list(src.iter_records())
    assert len(batches) == 1
    # Records are raw dicts (Mapping[str, Any]) - no model conversion
    assert list(batches[0]) == [
        {"a": 1, "b": "x"},
        {"a": 2, "b": "y"},
    ]
