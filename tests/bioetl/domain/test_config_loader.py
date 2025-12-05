from pathlib import Path

import pytest

from bioetl.domain import config_loader
from bioetl.domain.config_loader import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    UnknownProviderError,
    load_pipeline_config,
    load_pipeline_config_from_path,
)
from bioetl.infrastructure.config.models import ChemblSourceConfig


def test_load_pipeline_config_from_path_valid():
    path = Path("tests/fixtures/configs/chembl_activity_valid.yaml")
    config = load_pipeline_config_from_path(path)

    assert config.id == "chembl.activity"
    assert config.provider == "chembl"
    assert isinstance(config.provider_config, ChemblSourceConfig)
    assert config.provider_config.timeout_sec == 30


def test_extra_field_triggers_validation_error():
    path = Path("tests/fixtures/configs/chembl_activity_invalid_extra_key.yaml")
    with pytest.raises(ConfigValidationError):
        load_pipeline_config_from_path(path)


def test_missing_config_file_raises():
    with pytest.raises(ConfigFileNotFoundError):
        load_pipeline_config_from_path(Path("tests/fixtures/configs/missing.yaml"))


def test_unknown_provider_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pipelines_root = tmp_path / "pipelines"
    profiles_root = tmp_path / "profiles"
    (pipelines_root / "unknown").mkdir(parents=True)
    profiles_root.mkdir()

    config_path = pipelines_root / "unknown" / "entity.yaml"
    config_path.write_text(
        """id: unknown.entity
provider: unknown
entity: entity
input_mode: auto_detect
input_path: null
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

    monkeypatch.setattr(config_loader, "PIPELINES_ROOT", pipelines_root)
    monkeypatch.setattr(config_loader, "PROFILES_ROOT", profiles_root)

    with pytest.raises(UnknownProviderError):
        load_pipeline_config("unknown.entity")


def test_profile_merge_applied(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    pipelines_root = tmp_path / "pipelines"
    profiles_root = tmp_path / "profiles"
    chembl_dir = pipelines_root / "chembl"
    chembl_dir.mkdir(parents=True)
    profiles_root.mkdir()

    pipeline_file = chembl_dir / "activity.yaml"
    pipeline_file.write_text(
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
  timeout_sec: 10
  max_retries: 1
  rate_limit_per_sec: 5.0
""",
        encoding="utf-8",
    )

    profile_file = profiles_root / "base.yaml"
    profile_file.write_text(
        """output_path: /tmp/profile_out
batch_size: 25
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(config_loader, "PIPELINES_ROOT", pipelines_root)
    monkeypatch.setattr(config_loader, "PROFILES_ROOT", profiles_root)

    config = load_pipeline_config("chembl.activity")

    assert config.output_path == "/tmp/out"  # pipeline overrides profile
    assert config.batch_size == 10
    assert config.provider_config.timeout_sec == 10
