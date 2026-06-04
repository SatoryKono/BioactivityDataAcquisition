"""Tests for activity_aggregator facade exports."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.activity_aggregator import (
    ActivityAggregator,
    AggregationMethod,
)

pytestmark = pytest.mark.unit


def test_activity_aggregator_exports() -> None:
    """Test that activity_aggregator module exports expected classes."""
    assert ActivityAggregator is not None
    assert AggregationMethod is not None