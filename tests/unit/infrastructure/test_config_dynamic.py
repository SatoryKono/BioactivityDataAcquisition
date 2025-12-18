import pytest
from pathlib import Path
import yaml
import os
from bioetl.infrastructure.config import load_pipeline_config

@pytest.fixture
def setup_configs(tmp_path, monkeypatch):
    """
    Sets up a temporary configs directory structure and changes the current working directory
    to tmp_path so the relative paths in load_pipeline_config work correctly.
    """
    # Create the configs/pipelines directory structure in the temp dir
    pipelines_dir = tmp_path / "configs" / "pipelines"
    pipelines_dir.mkdir(parents=True)

    # Create dummy/test.yaml (for dummy_test)
    dummy_dir = pipelines_dir / "dummy"
    dummy_dir.mkdir()
    (dummy_dir / "test.yaml").write_text(yaml.dump({"pipeline_name": "dummy_test"}))

    # Create chembl/activity.yaml (mocking a real one)
    chembl_dir = pipelines_dir / "chembl"
    chembl_dir.mkdir()
    (chembl_dir / "activity.yaml").write_text(yaml.dump({"provider": "chembl", "entity": "activity"}))

    # Change CWD to tmp_path so "configs/pipelines/..." resolves to our temp files
    monkeypatch.chdir(tmp_path)

    return pipelines_dir

def test_load_dynamic_pipeline(setup_configs):
    """Verify that a dynamically created pipeline loads correctly."""
    # dummy_test corresponds to configs/pipelines/dummy/test.yaml
    config = load_pipeline_config("dummy_test")
    assert config is not None
    assert config.get("pipeline_name") == "dummy_test"

def test_load_registered_pipeline(setup_configs):
    """Verify that a standard pipeline loads correctly via dynamic resolution."""
    # chembl_activity should resolve to configs/pipelines/chembl/activity.yaml
    config = load_pipeline_config("chembl_activity")
    assert config is not None
    assert config.get("provider") == "chembl"

def test_load_nonexistent_pipeline(setup_configs):
    """Verify that a truly nonexistent pipeline returns empty dict."""
    config = load_pipeline_config("nonexistent_pipeline")
    assert config == {}

def test_load_invalid_name_format(setup_configs):
    """Verify behavior with name that doesn't split by underscore."""
    # This might fall back to configs/pipelines/invalidname.yaml which doesn't exist
    config = load_pipeline_config("invalidname")
    assert config == {}

def test_load_fallback_no_underscore(setup_configs):
    """Verify fallback for names without underscore if file exists."""
    # Create configs/pipelines/simple.yaml
    pipelines_dir = setup_configs
    (pipelines_dir / "simple.yaml").write_text(yaml.dump({"name": "simple"}))

    config = load_pipeline_config("simple")
    assert config is not None
    assert config.get("name") == "simple"
