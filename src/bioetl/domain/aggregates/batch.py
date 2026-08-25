"""Batch Aggregate.

Compatibility re-export (ADR-059 / #9603): definitions live in
`_batch_status`, `_batch_record`, and `_batch_aggregate`. New code should
import from `bioetl.domain.aggregates`.
"""

from __future__ import annotations

from bioetl.domain.aggregates._batch_aggregate import Batch
from bioetl.domain.aggregates._batch_record import BatchRecord
from bioetl.domain.aggregates._batch_status import BatchStatus

__all__ = [
    "Batch",
    "BatchRecord",
    "BatchStatus",
]
