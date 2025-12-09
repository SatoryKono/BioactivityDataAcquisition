from pathlib import Path

import pandas as pd

from bioetl.application.transform.pandas_batch_adapter import PandasBatchAdapter


def test_pandas_batch_adapter_converts_dataframe_to_records() -> None:
    adapter = PandasBatchAdapter()
    df = pd.DataFrame([{"id": 1, "name": "a"}, {"id": 2, "name": "b"}])

    records = adapter.adapt_batch(df)

    assert [r.model_dump() for r in records] == [
        {"id": 1, "name": "a"},
        {"id": 2, "name": "b"},
    ]


def test_record_source_module_has_no_pandas_import() -> None:
    record_source_path = Path("src/bioetl/domain/record_source.py")

    content = record_source_path.read_text(encoding="utf-8")

    assert "import pandas" not in content
