"""Tests for the interfaces.orchestration package surface."""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.mark.unit
def test_orchestration_package_exports_are_intentionally_empty() -> None:
    """Reserved orchestration package should remain importable with no public exports."""
    sys.modules.pop("bioetl.interfaces.orchestration", None)

    module = importlib.import_module("bioetl.interfaces.orchestration")

    assert module.__all__ == []
    assert "orchestration utilities" in (module.__doc__ or "").lower()
