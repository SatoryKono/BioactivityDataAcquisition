"""Adapters for normalizing pandas batches into raw record lists."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, cast

import pandas as pd

from bioetl.domain.contracts import BatchAdapterABC
from bioetl.domain.record_source import RawRecord


class PandasBatchAdapter(BatchAdapterABC):
    """Adapter to convert pandas DataFrame batches to raw record lists."""

    def adapt_batch(self, raw_batch: Any) -> list[RawRecord]:
        """Normalize a batch into a list of raw record mappings."""
        if raw_batch is None:
            return []

        if isinstance(raw_batch, pd.DataFrame):
            return cast(list[RawRecord], raw_batch.to_dict(orient="records"))

        if isinstance(raw_batch, dict):
            return [cast(RawRecord, raw_batch)]

        if isinstance(raw_batch, list):
            return cast(list[RawRecord], raw_batch)

        if isinstance(raw_batch, Iterable) and not isinstance(raw_batch, (str, bytes)):
            return cast(list[RawRecord], list(raw_batch))

        raise TypeError(
            "iter_extract must yield DataFrame, mapping, or iterable of mappings."
        )

    def adapt_batches(self, batches: Iterable[Any]) -> Iterable[list[RawRecord]]:
        """Adapt an iterable of batches lazily."""
        for batch in batches:
            yield self.adapt_batch(batch)


__all__ = ["PandasBatchAdapter"]
