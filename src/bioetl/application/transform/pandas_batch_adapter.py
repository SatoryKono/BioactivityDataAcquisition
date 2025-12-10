"""Адаптер для конвертации pandas DataFrame и других батчей в SourceRecordModel."""

from __future__ import annotations

from typing import Any, cast

import pandas as pd
from pydantic import BaseModel

from bioetl.domain.ports.extraction import BatchAdapterABC
from bioetl.domain.record_source import SourceRecordModel


class PandasBatchAdapter(BatchAdapterABC):
    """Конвертирует сырые батчи в список записей SourceRecordModel."""

    def __init__(self, model_cls: type[BaseModel] | None = None) -> None:
        self._model_cls: type[BaseModel] = model_cls or SourceRecordModel

    def process_batch(self, raw_batch: Any) -> list[SourceRecordModel]:
        """Нормализует батч провайдера в список моделей."""
        if raw_batch is None:
            return []

        if isinstance(raw_batch, pd.DataFrame):
            return [
                cast(SourceRecordModel, self._model_cls.model_validate(record))
                for record in raw_batch.to_dict("records")
            ]

        if isinstance(raw_batch, list):
            normalized: list[SourceRecordModel] = []
            for item in raw_batch:
                normalized.append(self._convert_record(item))
            return normalized

        if isinstance(raw_batch, dict):
            return [self._convert_record(raw_batch)]

        raise TypeError(
            "Unsupported batch type "
            f"'{type(raw_batch).__name__}' for PandasBatchAdapter"
        )

    def adapt_batch(self, raw_batch: Any) -> list[SourceRecordModel]:
        """Alias для process_batch для обратной совместимости."""
        return self.process_batch(raw_batch)

    def _convert_record(self, item: Any) -> SourceRecordModel:
        if isinstance(item, BaseModel):
            return cast(SourceRecordModel, item)
        return cast(SourceRecordModel, self._model_cls.model_validate(item))


__all__ = ["PandasBatchAdapter"]
