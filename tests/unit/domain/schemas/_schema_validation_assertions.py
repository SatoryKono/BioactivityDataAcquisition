"""Shared assertions for generated domain schema validation tests."""

from __future__ import annotations

from typing import Any

import pandas as pd


def assert_schema_validates_frame(schema: Any, frame: pd.DataFrame) -> pd.DataFrame:
    """Assert that a Pandera schema accepts a frame without changing its boundary."""
    validated = schema.validate(frame)

    assert isinstance(validated, pd.DataFrame)
    assert validated.shape == frame.shape
    assert list(validated.columns) == list(frame.columns)
    assert validated.index.equals(frame.index)

    return validated
