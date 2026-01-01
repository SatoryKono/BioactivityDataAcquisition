from __future__ import annotations

import pytest
import yaml

from bioetl.infrastructure.config import load_pipeline_config
from bioetl.infrastructure.config_loader import (
    load_pipeline_config as load_pipeline_config_cached,
    load_source_config,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


@pytest.fixture
def setup_configs(tmp_path, monkeypatch):
    """
    Sets up a temporary configs directory structure and changes the current working directory
    to tmp_path so the relative paths in load_pipeline_config work correctly.

    IMPORTANT: Clears the LRU cache on teardown to prevent cross-test contamination.
    """
    # Create the configs/pipelines directory structure in the temp dir
    pipelines_dir = tmp_path / "configs" / "pipelines"
    pipelines_dir.mkdir(parents=True)

    # Base valid config data
    base_config = {
        "pipeline_name": "dummy_test",
        "provider": "dummy",
        "entity_type": "test",
        "primary_keys": ["id"],
        "silver_table": "dummy.test_silver",
        "batch_size": 100,
        "checkpoint_interval": 1000,
    }

    # Create dummy/test.yaml (for dummy_test)
    dummy_dir = pipelines_dir / "dummy"
    dummy_dir.mkdir()
    (dummy_dir / "test.yaml").write_text(yaml.dump(base_config))

    # Create chembl/activity.yaml (mocking a real one)
    chembl_dir = pipelines_dir / "chembl"
    chembl_dir.mkdir()
    chembl_config = base_config.copy()
    chembl_config.update(
        {
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity_type": "activity",
            "silver_table": "chembl.activity_silver",
        }
    )
    (chembl_dir / "activity.yaml").write_text(yaml.dump(chembl_config))

    # Change CWD to tmp_path so "configs/pipelines/..." resolves to our temp files
    monkeypatch.chdir(tmp_path)

    yield pipelines_dir

    # Teardown: Clear the LRU cache to prevent cross-test contamination
    # This is critical for test isolation when integration tests run after unit tests
    load_pipeline_config_cached.cache_clear()
    load_source_config.cache_clear()


def test_load_dynamic_pipeline(setup_configs):
    """Verify that a dynamically created pipeline loads correctly."""
    # dummy_test corresponds to configs/pipelines/dummy/test.yaml
    config = load_pipeline_config("dummy_test")
    assert isinstance(config, PipelineYamlConfig)
    assert config.pipeline_name == "dummy_test"
    assert config.provider == "dummy"


def test_load_registered_pipeline(setup_configs):
    """Verify that a standard pipeline loads correctly via dynamic resolution."""
    # chembl_activity should resolve to configs/pipelines/chembl/activity.yaml
    config = load_pipeline_config("chembl_activity")
    assert isinstance(config, PipelineYamlConfig)
    assert config.provider == "chembl"
    assert config.entity_type == "activity"


def test_load_nonexistent_pipeline(setup_configs):
    """Verify that a truly nonexistent pipeline raises ValueError."""
    with pytest.raises(ValueError, match="Configuration file not found"):
        load_pipeline_config("nonexistent_pipeline")


def test_load_invalid_name_format(setup_configs):
    """Verify behavior with name that doesn't split by underscore."""
    # This might fall back to configs/pipelines/invalidname.yaml which doesn't exist
    with pytest.raises(ValueError, match="Configuration file not found"):
        load_pipeline_config("invalidname")


def test_load_fallback_no_underscore(setup_configs):
    """Verify fallback for names without underscore if file exists."""
    # Create configs/pipelines/simple.yaml
    pipelines_dir = setup_configs

    simple_config = {
        "pipeline_name": "simple",
        "provider": "simple",
        "entity_type": "simple",
        "primary_keys": ["id"],
        "silver_table": "simple.table",
        "batch_size": 100,
        "checkpoint_interval": 1000,
    }

    (pipelines_dir / "simple.yaml").write_text(yaml.dump(simple_config))

    config = load_pipeline_config("simple")
    assert isinstance(config, PipelineYamlConfig)
    assert config.pipeline_name == "simple"


def test_dq_thresholds_are_validated_once(setup_configs):
    """DQ thresholds must satisfy domain invariants even in YAML schema."""
    pipelines_dir = setup_configs

    invalid_config = {
        "pipeline_name": "dummy_invalid",
        "provider": "dummy",
        "entity_type": "invalid",
        "primary_keys": ["id"],
        "silver_table": "dummy.test_silver",
        "dq_rules": {"soft_fail_threshold": 0.3, "hard_fail_threshold": 0.2},
    }

    (pipelines_dir / "dummy" / "invalid.yaml").write_text(yaml.dump(invalid_config))

    with pytest.raises(ValueError, match="soft_fail_threshold must be strictly less"):
        load_pipeline_config("dummy_invalid")


def test_gold_filters_loading(setup_configs):
    """Verify loading of gold_filters from YAML."""
    pipelines_dir = setup_configs

    config_data = {
        "pipeline_name": "chembl_filters",
        "provider": "chembl",
        "entity_type": "filters",
        "primary_keys": ["id"],
        "silver_table": "chembl.filters",
        "gold_filters": {
            "columns": {"standard_type": ["IC50", "Ki"]},
            "required_fields": ["value"],
            "exclude_if_present": ["invalid"],
        },
    }

    (pipelines_dir / "chembl" / "filters.yaml").write_text(yaml.dump(config_data))

    config = load_pipeline_config("chembl_filters")
    # Note: load_pipeline_config returns PipelineYamlConfig (infrastructure layer)
    # which uses lists. Use get_pipeline_config for domain PipelineConfig with tuples.
    assert config.gold_filters.columns == {"standard_type": ["IC50", "Ki"]}
    assert config.gold_filters.required_fields == ["value"]
    assert config.gold_filters.exclude_if_present == ["invalid"]
