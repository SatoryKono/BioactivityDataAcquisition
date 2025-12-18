import pytest
from pathlib import Path
import yaml
import os
from bioetl.infrastructure.config import load_pipeline_config
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

@pytest.fixture
def setup_configs(tmp_path, monkeypatch):
    """
    Sets up a temporary configs directory structure and changes the current working directory
    to tmp_path so the relative paths in load_pipeline_config work correctly.
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
        "checkpoint_interval": 1000
    }

    # Create dummy/test.yaml (for dummy_test)
    dummy_dir = pipelines_dir / "dummy"
    dummy_dir.mkdir()
    (dummy_dir / "test.yaml").write_text(yaml.dump(base_config))

    # Create chembl/activity.yaml (mocking a real one)
    chembl_dir = pipelines_dir / "chembl"
    chembl_dir.mkdir()
    chembl_config = base_config.copy()
    chembl_config.update({
        "pipeline_name": "chembl_activity",
        "provider": "chembl",
        "entity_type": "activity",
        "silver_table": "chembl.activity_silver"
    })
    (chembl_dir / "activity.yaml").write_text(yaml.dump(chembl_config))

    # Change CWD to tmp_path so "configs/pipelines/..." resolves to our temp files
    monkeypatch.chdir(tmp_path)

    return pipelines_dir

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
        "checkpoint_interval": 1000
    }

    (pipelines_dir / "simple.yaml").write_text(yaml.dump(simple_config))

    config = load_pipeline_config("simple")
    assert isinstance(config, PipelineYamlConfig)
    assert config.pipeline_name == "simple"
