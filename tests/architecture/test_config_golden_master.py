# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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

from __future__ import annotations

import json
import os
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from bioetl.domain.config import PipelineConfig
from bioetl.infrastructure.config._base import yaml_config_to_domain
from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config

pytestmark = pytest.mark.architecture

# Path to store snapshots
SNAPSHOT_DIR = Path("tests/snapshots")
SNAPSHOT_FILE = SNAPSHOT_DIR / "pipeline_configs.json"
MATRIX_PATH = Path("configs/quality/test_matrix.yaml")
EXCLUDED_PROVIDER_SURFACES = frozenset({"chembl", "composite"})


def _convert_for_json(obj: Any) -> Any:
    """Convert non-JSON-serializable types for snapshotting."""
    if isinstance(obj, Enum):
        return obj.value  # Convert Enum to its value
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
    return cast(dict[str, Any], _convert_for_json(raw_dict))


def load_snapshots() -> dict[str, Any]:
    """Load existing snapshots from JSON file."""
    if not SNAPSHOT_FILE.exists():
        return {}
    with open(SNAPSHOT_FILE) as f:
        return cast(dict[str, Any], json.load(f))


def save_snapshots(snapshots: dict[str, Any]) -> None:
    """Save snapshots to JSON file."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOT_FILE, "w") as f:
        json.dump(snapshots, f, indent=2, sort_keys=True)


@pytest.fixture(scope="session")
def golden_snapshots() -> dict[str, Any]:
    """Fixture to provide loaded snapshots."""
    return load_snapshots()


def _active_entity_pipelines() -> dict[str, str]:
    """Collect one active representative pipeline name per provider."""
    providers: dict[str, str] = {}
    for config_path in sorted(Path("configs/entities").glob("*/*.yaml")):
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        pipeline_name = payload.get("pipeline_name")
        if not isinstance(pipeline_name, str) or not pipeline_name.strip():
            # Some compatibility/config surfaces (e.g. composite) are not standalone pipelines.
            continue
        providers.setdefault(config_path.parent.name, pipeline_name)
    return providers


def _golden_master_registry() -> dict[str, tuple[str, ...]]:
    matrix = yaml.safe_load(MATRIX_PATH.read_text(encoding="utf-8")) or {}
    registry = matrix.get("fixture_governance", {}).get("golden_master_registry", {})
    providers = registry.get("providers", {})
    return {
        str(provider): tuple(str(pipeline) for pipeline in config.get("pipelines", []))
        for provider, config in providers.items()
    }


# Matrix-declared inventory is the source of truth for golden-master coverage.
PIPELINES = [
    pipeline
    for pipelines in _golden_master_registry().values()
    for pipeline in pipelines
]


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
        return

    # 3. Assert against snapshot
    if pipeline_name not in golden_snapshots:
        pytest.fail(
            f"No snapshot found for {pipeline_name}. "
            f"Run with UPDATE_SNAPSHOTS=1 to generate initial snapshots."
        )

    assert serialized_config == golden_snapshots[pipeline_name]


def test_golden_master_pipeline_set_references_existing_configs() -> None:
    """Representative golden-master pipelines must remain loadable."""
    for pipeline_name in PIPELINES:
        yaml_config = load_pipeline_config(pipeline_name)
        assert yaml_config is not None


def test_golden_master_pipeline_set_covers_each_non_chembl_provider() -> None:
    """Golden-master set must cover every standalone entity-config provider."""
    represented = {
        yaml_config_to_domain(load_pipeline_config(pipeline_name)).provider
        for pipeline_name in PIPELINES
    }
    expected = {
        provider
        for provider in _active_entity_pipelines()
        if provider not in EXCLUDED_PROVIDER_SURFACES
    }

    assert expected <= represented


def test_golden_master_pipeline_set_includes_special_case_pipeline() -> None:
    """Representative set should keep a non-trivial pipeline shape in scope."""
    assert "chembl_publication_term" in PIPELINES


def test_golden_master_pipeline_set_matches_declared_registry() -> None:
    """Representative pipeline set must match the matrix-declared registry."""
    registry = _golden_master_registry()
    expected = {pipeline for pipelines in registry.values() for pipeline in pipelines}
    assert set(PIPELINES) == expected
