"""Tests for the HTTP package root surface."""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.unit
def test_http_package_root_exposes_no_convenience_exports() -> None:
    """Package root should stay free of convenience re-exports."""
    module = importlib.import_module("bioetl.interfaces.http")

    assert module.__all__ == []
    assert "HealthResponse" not in dir(module)
    assert "HealthServer" not in dir(module)
    with pytest.raises(AttributeError):
        getattr(module, "HealthResponse")
    with pytest.raises(AttributeError):
        getattr(module, "HealthServer")
