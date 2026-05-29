"""Unit tests for application-owned record normalization stage."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)

if TYPE_CHECKING:
    pass


@pytest.mark.unit
def build_normalization_processor(**kwargs):
    return RecordNormalizationProcessor(**kwargs)


__all__ = [
    name
    for name in globals()
    if name
    not in {
        "__builtins__",
        "__cached__",
        "__doc__",
        "__file__",
        "__loader__",
        "__name__",
        "__package__",
        "__spec__",
    }
]
