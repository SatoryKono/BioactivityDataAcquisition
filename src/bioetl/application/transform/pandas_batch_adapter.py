"""Адаптер для конвертации pandas DataFrame и других батчей в RawRecord."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd

from bioetl.domain.ports.extraction import BatchAdapterABC
from bioetl.domain.record_source import RawRecord


class PandasBatchAdapter(BatchAdapterABC):
    """Конвертирует сырые батчи в список записей RawRecord."""

    def process_batch(self, raw_batch: Any) -> list[RawRecord]:
        """Нормализует батч провайдера в список словарей."""
        if raw_batch is None:
            return []

        if isinstance(raw_batch, pd.DataFrame):
            return [
                cast(RawRecord, dict(record))
                for record in raw_batch.to_dict("records")
            ]

        if isinstance(raw_batch, list):
            normalized: list[RawRecord] = []
            for item in raw_batch:
                normalized.append(cast(RawRecord, dict(item)))
            return normalized

        if isinstance(raw_batch, dict):
            return [cast(RawRecord, dict(raw_batch))]

        raise TypeError(
            "Unsupported batch type "
            f"'{type(raw_batch).__name__}' for PandasBatchAdapter"
        )

    def adapt_batch(self, raw_batch: Any) -> list[RawRecord]:
        """Alias для process_batch для обратной совместимости."""
        return self.process_batch(raw_batch)


__all__ = ["PandasBatchAdapter"]
