"""Fixtures for ops/data script tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def temp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory for testing."""
    data_dir = tmp_path / "data" / "output" / "silver" / "chembl"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def sample_delta_data() -> dict:
    """Sample Delta table data for testing."""
    return {
        "molecule_id": ["CHEMBL1", "CHEMBL2", "CHEMBL3"],
        "standard_type": ["IC50", "Ki", "EC50"],
        "standard_value": [100.0, 50.0, 25.0],
    }
