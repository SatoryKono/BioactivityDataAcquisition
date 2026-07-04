"""Shared helpers for constructing storage-taxonomy errors in infrastructure."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from bioetl.domain.exceptions import StorageError

__all__ = ["build_storage_error"]


def build_storage_error(
    *,
    message_prefix: str,
    operation: str,
    path: Path,
    error: Exception,
    **context: object,
) -> StorageError:
    """Build one contextualized ``StorageError`` for infrastructure call sites."""
    wrapped = StorageError(f"{message_prefix} {operation} failed for '{path}': {error}")
    contextualized = wrapped.with_context(
        operation=operation,
        path=str(path),
        original_error=str(error),
        **context,
    )
    return cast(StorageError, contextualized)
