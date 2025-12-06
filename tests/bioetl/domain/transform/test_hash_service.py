import re

import pandas as pd

from bioetl.domain.transform.hash_service import HashService


def test_add_index_column_and_immutability():
    svc = HashService()
    src = pd.DataFrame({"a": [1, 2, 3]})
    out = svc.add_index_column(src)
    assert "index" in out.columns
    assert list(out["index"]) == [0, 1, 2]
    # исходный df не должен иметь новую колонку
    assert "index" not in src.columns


def test_add_database_version_column_and_empty_df():
    svc = HashService()
    src = pd.DataFrame({"a": []})
    out = svc.add_database_version_column(src, "v1.2.3")
    assert "database_version" in out.columns
    # на пустом df столбец всё равно существует (пустой)
    assert out["database_version"].dtype == object or out["database_version"].empty

    src2 = pd.DataFrame({"a": [1]})
    out2 = svc.add_database_version_column(src2, "v1.2.3")
    assert all(out2["database_version"] == "v1.2.3")


def test_add_fulldate_column_format_and_consistency():
    svc = HashService()
    src = pd.DataFrame({"a": [1, 2, 3]})
    out = svc.add_fulldate_column(src)
    assert "extracted_at" in out.columns
    vals = out["extracted_at"].unique()
    assert len(vals) == 1  # одинаковая метка для всех строк
    ts = vals[0]
    assert isinstance(ts, str) and "T" in ts  # простая проверка ISO-формата
    # можно попробовать парсить, но это не критично — проверим наличие числа года
    assert re.search(r"\d{4}-\d{2}-\d{2}T", ts)
