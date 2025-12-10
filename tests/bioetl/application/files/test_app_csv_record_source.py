from pathlib import Path
from typing import cast

import pandas as pd

from bioetl.application.files.csv_record_source import CsvRecordSourceImpl
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.record_source import RawRecord
from bioetl.domain.configs import CsvInputConfig


def test_csv_record_source_reads_full_dataset(tmp_path):
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
    assert [r.model_dump() for r in batches[0]] == [
        RawRecord(a=1, b="x").model_dump(),
        RawRecord(a=2, b="y").model_dump(),
    ]
