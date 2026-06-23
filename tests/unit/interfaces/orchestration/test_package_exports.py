"""Tests for the retired interfaces.orchestration package seam."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_orchestration_package_is_retired() -> None:
    """Placeholder orchestration package must not remain importable."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("bioetl.interfaces.orchestration")
