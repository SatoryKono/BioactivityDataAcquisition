"""
Golden Master tests for Pipeline Configuration.

These tests ensure that the mapping from YAML configuration to Domain configuration
remains stable across refactorings. It works by:
1. Loading all existing YAML pipeline configurations.
2. Converting them to their Domain representation (PipelineConfig).
3. Comparing the result against a stored JSON snapshot.
4. If snapshots don't exist (first run), they are created.

Usage:
    pytest tests/architecture/test_config_golden_master.py

    To update snapshots (ONLY do this if you intentionally changed config structure):
    UPDATE_SNAPSHOTS=1 pytest tests/architecture/test_config_golden_master.py
"""

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pytest

from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config import load_pipeline_config, yaml_config_to_domain

# Path to store snapshots
SNAPSHOT_DIR = Path("tests/snapshots")
SNAPSHOT_FILE = SNAPSHOT_DIR / "pipeline_configs.json"

# List of all pipeline config names to test
PIPELINES = [
    "chembl_activity",
    "pubchem_compound",
    "pubmed_publications",
    "uniprot_protein",
]


def _convert_for_json(obj: Any) -> Any:
    """Convert non-JSON-serializable types for snapshotting."""
    if isinstance(obj, frozenset):
        return sorted(obj)  # Convert to sorted list for stable comparisons
    if isinstance(obj, dict):
        return {k: _convert_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_for_json(item) for item in obj]
    return obj


def serialize_config(config: PipelineConfig) -> dict[str, Any]:
    """Serialize PipelineConfig to a dictionary for snapshotting."""
    raw_dict = asdict(config)
    return _convert_for_json(raw_dict)


def load_snapshots() -> dict[str, Any]:
    """Load existing snapshots from JSON file."""
    if not SNAPSHOT_FILE.exists():
        return {}
    with open(SNAPSHOT_FILE) as f:
        return json.load(f)


def save_snapshots(snapshots: dict[str, Any]) -> None:
    """Save snapshots to JSON file."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(snapshots, f, indent=2, sort_keys=True)


@pytest.fixture(scope="session")
def golden_snapshots() -> dict[str, Any]:
    """Fixture to provide loaded snapshots."""
    return load_snapshots()


@pytest.mark.parametrize("pipeline_name", PIPELINES)
def test_pipeline_config_golden_master(
    pipeline_name: str, golden_snapshots: dict[str, Any]
) -> None:
    """
    Test that the loaded configuration matches the Golden Master snapshot.
    """
    # 1. Load and map configuration
    yaml_config = load_pipeline_config(pipeline_name)
    domain_config = yaml_config_to_domain(yaml_config)
    serialized_config = serialize_config(domain_config)

    # 2. Check if we should update snapshots
    update_snapshots = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"

    if update_snapshots:
        # We are in update mode, so we update the in-memory snapshots
        current_snapshots = load_snapshots()
        current_snapshots[pipeline_name] = serialized_config
        save_snapshots(current_snapshots)
        pytest.skip(f"Updated snapshot for {pipeline_name}")

    # 3. Assert against snapshot
    if pipeline_name not in golden_snapshots:
        pytest.fail(
            f"No snapshot found for {pipeline_name}. "
            f"Run with UPDATE_SNAPSHOTS=1 to generate initial snapshots."
        )

    assert serialized_config == golden_snapshots[pipeline_name]
