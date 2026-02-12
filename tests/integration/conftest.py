"""Fixtures for integration tests."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def integration_relaxed_dq() -> None:
    """Relax DQ thresholds for integration tests using VCR cassettes."""
    os.environ["BIOETL_TEST_RELAXED_DQ"] = "1"
