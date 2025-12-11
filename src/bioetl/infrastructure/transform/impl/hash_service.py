"""Infrastructure implementation of HashService using BLAKE2b.

Terminology:
    compute_fingerprint: Computes a hash fingerprint of the entire record.
    compute_entity_key: Computes a hash of the business key fields.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pandas as pd

from bioetl.domain.data import MutableTabularData, RecordBatch, TabularData
from bioetl.domain.transform.contracts import HasherABC, HashServiceABC
from bioetl.domain.value_objects import HashDigest


class Blake2bHashService(HashServiceABC):
    """
    Stateless хеш-сервис на основе BLAKE2b-256.

    Использует HasherABC для вычисления хешей.
    Не содержит никакого состояния - чистые функции хеширования.

    Methods:
        compute_fingerprint: Compute record_hash of entire record.
        compute_entity_key: Compute business_key_hash from key fields.
        add_hashes_to_batch: Add hash columns to records.
    """

    def __init__(self, hasher: HasherABC) -> None:
        """
        Args:
            hasher: Реализация алгоритма хеширования.
        """
        self._hasher = hasher

    @property
    def algorithm(self) -> str:
        """Return algorithm identifier."""
        return self._hasher.algorithm

    def compute_fingerprint(self, record: Mapping[str, Any]) -> HashDigest:
        """Compute record_hash (fingerprint) of entire record.

        Args:
            record: Record data as mapping (dict-like).

        Returns:
            HashDigest value object containing the record_hash.
        """
        if hasattr(self._hasher, "compute_hash"):
            res = self._hasher.compute_hash(record)
        else:
            res = self._hasher.compute_hash_row(record)
        return res if isinstance(res, HashDigest) else HashDigest(str(res))

    def compute_entity_key(
        self,
        record: Mapping[str, Any],
        key_fields: Sequence[str],
    ) -> HashDigest:
        """Compute business_key_hash (entity_key) from key fields.

        Args:
            record: Record data as mapping.
            key_fields: Sequence of field names forming the business key.

        Returns:
            HashDigest value object containing the business_key_hash.
        """
        if hasattr(self._hasher, "compute_hash_for_fields"):
            res = self._hasher.compute_hash_for_fields(record, key_fields)
        else:
            res = self._hasher.compute_hash_columns(record, key_fields)
        return res if isinstance(res, HashDigest) else HashDigest(str(res))

    def add_hashes_to_batch(
        self,
        records: RecordBatch,
        key_fields: Sequence[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Add hash columns (record_hash, business_key_hash) to each record.

        Args:
            records: Sequence of records (Mapping[str, Any]).
            key_fields: Optional sequence of business key field names.

        Returns:
            List of dictionaries with added hash columns.
        """
        result = []
        for record in records:
            record_dict = dict(record)
            record_dict["hash_row"] = self.compute_fingerprint(record).value
            if key_fields:
                record_dict["hash_business_key"] = self.compute_entity_key(
                    record, key_fields
                ).value
            else:
                record_dict["hash_business_key"] = None
            result.append(record_dict)
        return result

    def add_hash_columns(
        self, data: TabularData, business_key_cols: Sequence[str] | None = None
    ) -> MutableTabularData:
        """Add hash columns (record_hash, business_key_hash) to tabular data.

        Args:
            data: Input tabular data.
            business_key_cols: Optional sequence of business key column names.

        Returns:
            MutableTabularData with added hash columns.
        """
        # Work with pandas DataFrame
        df = data if isinstance(data, pd.DataFrame) else pd.DataFrame(data.to_records())
        df = df.copy()

        if business_key_cols:
            cols_to_hash = [c for c in business_key_cols if c in df.columns]
            if cols_to_hash:
                df["hash_business_key"] = df.apply(
                    lambda row, _hasher=self._hasher, _cols=cols_to_hash: (
                        (lambda _res: _res.value if hasattr(_res, "value") else str(_res))(
                            _hasher.compute_hash_for_fields(row.to_dict(), _cols)
                        )
                        if hasattr(_hasher, "compute_hash_for_fields")
                        else (lambda _res: _res.value if hasattr(_res, "value") else str(_res))(
                            _hasher.compute_hash_columns(row.to_dict(), _cols)
                        )
                    ),
                    axis=1,
                )
            else:
                df["hash_business_key"] = None
        else:
            df["hash_business_key"] = None

        def _to_value(x: object) -> str:
            return x.value if isinstance(x, HashDigest) else str(x)

        def _row_hash(rec: dict) -> str:
            if hasattr(self._hasher, "compute_hash"):
                return _to_value(self._hasher.compute_hash(rec))
            return _to_value(self._hasher.compute_hash_row(rec))

        def _compute_bkh(rec: dict, cols: list[str]) -> str:
            if hasattr(self._hasher, "compute_hash_for_fields"):
                return _to_value(self._hasher.compute_hash_for_fields(rec, cols))
            return _to_value(self._hasher.compute_hash_columns(rec, cols))

        df["hash_row"] = df.apply(lambda row: _row_hash(row.to_dict()), axis=1)
        return df

    # Legacy methods for backward compatibility

    def compute_row_fingerprint(self, row: dict) -> str:
        """Вычисляет хеш-отпечаток строки как полного объекта (legacy).

        Args:
            row: Словарь с данными строки.

        Returns:
            Hex-строка с хешем строки.
        """
        return self.compute_fingerprint(row).value


__all__ = ["Blake2bHashService"]
