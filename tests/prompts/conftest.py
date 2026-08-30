"""Prompts tests — avoid heavy SilverWriter/polars autouse fixture."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _bioetl_test_silver_validator() -> None:
    """Shadow root autouse fixture to keep prompts tests lightweight (no polars import)."""
    yield
