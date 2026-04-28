# mypy: disable-error-code=attr-defined
"""Merged-write helpers for ``SilverWriter``."""

from __future__ import annotations

from bioetl.infrastructure.storage.silver.merged_operations import (
    _MergedSilverWriteRequest,
)
from bioetl.infrastructure.storage.silver.operations.merged_operations import (
    _MergedWriteFacade,
)


class SilverWriterMergedMixin(_MergedWriteFacade):
    """Merged write path extracted from ``SilverWriter`` class body."""
