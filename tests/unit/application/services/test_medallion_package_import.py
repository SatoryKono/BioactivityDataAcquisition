"""Smoke tests for rehomed medallion package (ARCH-REF-02)."""

from __future__ import annotations

import pytest

from bioetl.application.services.medallion.medallion_lifecycle import (
    MedallionLifecycleService,
)
from bioetl.application.services.medallion.medallion_types import (
    ClearResult,
    VacuumResult,
)

pytestmark = pytest.mark.unit


def test_medallion_public_types_importable() -> None:
    assert ClearResult is not None
    assert VacuumResult is not None
    assert MedallionLifecycleService is not None
