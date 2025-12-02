import pandas as pd
from unittest.mock import patch
from pathlib import Path

from bioetl.output.impl.parquet_writer import ParquetWriterImpl


def test_parquet_writer_properties():
    writer = ParquetWriterImpl()
    assert writer.atomic is True
    assert writer.supports_format("parquet")
    assert writer.supports_format("PARQUET")
    assert not writer.supports_format("csv")


def test_parquet_write():
    writer = ParquetWriterImpl()
    df = pd.DataFrame({"a": [1, 2]})
    path = Path("test.parquet")

    # Mock to_parquet
    with patch("pandas.DataFrame.to_parquet") as mock_to_parquet, \
         patch("time.monotonic", side_effect=[0.0, 0.1]):

        result = writer.write(df, path)

        # Check result
        assert result.path == path
        assert result.row_count == 2
        assert result.duration_sec == 0.1

        # Check call
        mock_to_parquet.assert_called_once_with(path, index=False)
