"""Адаптер для конвертации pandas DataFrame и других батчей в raw dicts.

Returns raw dicts (Mapping[str, Any]) per BatchAdapterABC contract.
Domain model conversion should happen via RecordMapperABC in ExtractStage.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import pandas as pd
from pydantic import BaseModel

from bioetl.domain.ports.extraction import BatchAdapterABC


class PandasBatchAdapter(BatchAdapterABC):
    """Конвертирует сырые батчи в список записей (raw dicts).

    Returns raw dicts per BatchAdapterABC contract. Domain model conversion
    should happen via RecordMapperABC in ExtractStage if needed.
    """

    def __init__(self, model_cls: Any = None) -> None:
        # model_cls is no longer used - validation happens via RecordMapperABC
        if model_cls is not None:
            import warnings

            warnings.warn(
                "model_cls parameter is deprecated. Use RecordMapperABC in "
                "ExtractStage for domain model conversion.",
                DeprecationWarning,
                stacklevel=2,
            )

    def process_batch(self, raw_batch: Any) -> list[Mapping[str, Any]]:
        """Нормализует батч провайдера в список raw dicts.

        Returns raw dicts. Domain model validation should be performed by
        RecordMapperABC in the extraction stage.
        """
        if raw_batch is None:
            return []

        if isinstance(raw_batch, pd.DataFrame):
            return cast(list[Mapping[str, Any]], raw_batch.to_dict("records"))

        if isinstance(raw_batch, list):
            normalized: list[Mapping[str, Any]] = []
            for item in raw_batch:
                normalized.append(self._convert_record(item))
            return normalized

        if isinstance(raw_batch, dict):
            return [self._convert_record(raw_batch)]

        raise TypeError(
            "Unsupported batch type "
            f"'{type(raw_batch).__name__}' for PandasBatchAdapter"
        )

    def adapt_batch(self, raw_batch: Any) -> list[Mapping[str, Any]]:
        """Alias для process_batch для обратной совместимости."""
        return self.process_batch(raw_batch)

    def _convert_record(self, item: Any) -> Mapping[str, Any]:
        """Convert a single record to raw dict."""
        if isinstance(item, BaseModel):
            return item.model_dump()
        if isinstance(item, Mapping):
            return dict(item)
        raise TypeError(
            f"Cannot convert {type(item).__name__} to Mapping[str, Any]"
        )


__all__ = ["PandasBatchAdapter"]
