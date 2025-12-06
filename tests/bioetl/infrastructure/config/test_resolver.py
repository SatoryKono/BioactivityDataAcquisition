"""
Tests for configuration loading and profile handling.
"""

from pathlib import Path

import pytest

from bioetl.domain.transform.merge import deep_merge
from bioetl.infrastructure.config.loader import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    load_pipeline_config_from_path,
)
from bioetl.infrastructure.config.provider_registry_loader import (
    clear_provider_registry_cache,
)
from bioetl.infrastructure.config.sources import read_yaml_from_path


@pytest.fixture(autouse=True)
def _reset_registry() -> None:
    clear_provider_registry_cache()
    yield
    clear_provider_registry_cache()


def _write_providers(
    path: Path,
    content: str = (
        "providers:\n"
        "  - id: chembl\n"
        "    module: tests.dummy\n"
        "    factory: create_chembl\n"
        "    active: true\n"
    ),
) -> None:
    path.write_text(content, encoding="utf-8")


def test_load_with_profile_and_extends(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    providers_file = tmp_path / "providers.yaml"
    _write_providers(providers_file)
    monkeypatch.setattr(
        "bioetl.infrastructure.config.provider_registry_loader.DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )

    profiles_root = tmp_path / "profiles"
    profiles_root.mkdir()
    (profiles_root / "base.yaml").write_text("batch_size: 5", encoding="utf-8")
    (profiles_root / "prod.yaml").write_text("batch_size: 20", encoding="utf-8")

    pipelines_root = tmp_path / "pipelines" / "chembl"
    pipelines_root.mkdir(parents=True)
    config_path = pipelines_root / "activity.yaml"
    config_path.write_text(
        """extends: base
id: chembl.activity
provider: chembl
entity: activity
input_mode: auto_detect
input_path: null
output_path: /tmp/out
batch_size: 10
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  timeout_sec: 30
  max_retries: 3
  rate_limit_per_sec: 10.0
""",
        encoding="utf-8",
    )

    config = load_pipeline_config_from_path(
        config_path,
        profile="prod",
        profiles_root=profiles_root,
    )

    assert config.batch_size == 20  # profile override wins
    assert config.output_path == "/tmp/out"  # pipeline override


def test_deep_merge():
    """Test deep dictionary merge."""
    base = {"a": {"x": 1}}
    update = {"a": {"y": 2}, "b": 3}

    result = deep_merge(base, update)
    assert result["a"]["x"] == 1
    assert result["a"]["y"] == 2
    assert result["b"] == 3


def test_profile_not_found_raises(tmp_path: Path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "extends: missing\nprovider: chembl\nentity: e\ninput_mode: auto_detect\ninput_path: null\noutput_path: /tmp/out\nbatch_size: 1\nprovider_config:\n  provider: chembl\n  base_url: https://www.ebi.ac.uk/chembl/api/data\n  timeout_sec: 30\n  max_retries: 3\n  rate_limit_per_sec: 10.0\n",
        encoding="utf-8",
    )
    providers_file = tmp_path / "providers.yaml"
    _write_providers(providers_file)

    with pytest.raises(ConfigFileNotFoundError):
        load_pipeline_config_from_path(
            config_path,
            profile="missing",
            profiles_root=tmp_path / "profiles",
        )


def test_validate_input_path_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    providers_file = tmp_path / "providers.yaml"
    _write_providers(providers_file)
    monkeypatch.setattr(
        "bioetl.infrastructure.config.provider_registry_loader.DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )

    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """id: chembl.activity
provider: chembl
entity: activity
input_mode: csv
input_path: /does/not/exist.csv
output_path: /tmp/out
batch_size: 5
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  timeout_sec: 30
  max_retries: 3
  rate_limit_per_sec: 10.0
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError):
        load_pipeline_config_from_path(config_path)


def test_empty_yaml(tmp_path: Path):
    """Test handling of empty YAML file."""
    empty_file = tmp_path / "empty.yaml"
    empty_file.touch()

    path, data = read_yaml_from_path(empty_file, profile=None, profiles_root=tmp_path)
    assert data == {}
    assert path == empty_file
