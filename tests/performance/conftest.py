"""Pytest configuration for performance tests."""

from __future__ import annotations

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register performance-observation output option."""
    parser.addoption(
        "--perf-obs-out",
        dest="perf_obs_out",
        action="store",
        default=None,
        help="Path to JSONL file where hotspot performance observations are appended.",
    )
