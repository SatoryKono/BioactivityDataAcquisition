"""Source pagination config structural contracts."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PaginationConfigLike(Protocol):
    """Structural pagination settings used by source extractors."""

    id_batch_size: object


@runtime_checkable
class SourceConfigLike(Protocol):
    """Structural source config surface exposing pagination settings."""

    pagination: PaginationConfigLike
