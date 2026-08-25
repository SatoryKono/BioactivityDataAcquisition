"""Source pagination config structural contracts."""

from __future__ import annotations

from typing import Protocol


class PaginationConfigLike(Protocol):
    id_batch_size: object


class SourceConfigLike(Protocol):
    pagination: PaginationConfigLike
