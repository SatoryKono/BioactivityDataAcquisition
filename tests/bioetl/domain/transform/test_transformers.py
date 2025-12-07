from datetime import datetime, timedelta, timezone

import pandas as pd

from bioetl.domain.models import RunContext
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.transform.transformers import FulldateTransformerImpl


def test_fulldate_transformer_uses_run_context_timestamp() -> None:
    df = pd.DataFrame({"value": [1, 2]})
    started_at = datetime(2024, 5, 6, 7, 8, 9, tzinfo=timezone.utc)
    context = RunContext(started_at=started_at)

    transformer = FulldateTransformerImpl(HashService())

    result = transformer.apply(df, context)

    assert result["extracted_at"].unique().tolist() == [started_at.isoformat()]


def test_fulldate_transformer_localizes_naive_timestamp_once() -> None:
    df = pd.DataFrame({"value": [1]})
    base_ts = datetime(2024, 1, 2, 3, 4, 5)

    call_count = 0

    def _now_provider() -> datetime:
        nonlocal call_count
        call_count += 1
        return base_ts + timedelta(seconds=call_count)

    transformer = FulldateTransformerImpl(HashService(now_provider=_now_provider))

    first = transformer.apply(df)
    second = transformer.apply(df)

    expected_ts = (base_ts + timedelta(seconds=1)).replace(tzinfo=timezone.utc).isoformat()

    assert first["extracted_at"].tolist() == [expected_ts]
    assert second["extracted_at"].tolist() == [expected_ts]
    assert call_count == 1
