"""Port for pipeline contract policy access.

Defines the minimal contract-policy shape used by application
transformers for field renaming and content-hash field selection.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable

from bioetl.domain.types import GoldRecord

__all__ = ["ContractPolicyProtocol"]


@runtime_checkable
class ContractPolicyProtocol(Protocol):
    """Protocol for pipeline contract policy objects.

    Implementations may come from infrastructure schemas or test doubles,
    but application code depends only on this port.
    """

    @property
    def primary_key(self) -> Sequence[str]:
        """Return primary key fields."""
        ...

    @property
    def merge_keys(self) -> Sequence[str]:
        """Return merge key fields."""
        ...

    @property
    def hash_include(self) -> Sequence[str]:
        """Return explicit include fields for content hash calculation."""
        ...

    @property
    def hash_exclude(self) -> Sequence[str]:
        """Return fields excluded from content hash calculation."""
        ...

    @property
    def rename_map(self) -> Mapping[str, str]:
        """Return source-to-target field rename mapping."""
        ...


# ETLRecordSchema declares these parent columns first and sets ordered=True.
_ETL_RECORD_PREFIX: tuple[str, ...] = (
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_ingestion_ts",
    "_index",
    "_dq_warn",
    "_dq_error",
)


def project_etl_order(record: GoldRecord) -> GoldRecord:
    """Keep ETL parent columns ahead of pipeline fields."""
    ordered = {key: record[key] for key in _ETL_RECORD_PREFIX if key in record}
    ordered.update((key, value) for key, value in record.items() if key not in ordered)
    return ordered
