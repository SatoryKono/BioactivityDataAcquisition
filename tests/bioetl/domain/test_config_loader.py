from pathlib import Path

import pytest

from bioetl.application.services.schema_contract_provider import (
    SchemaContractProviderImpl,
)
from bioetl.domain.configs import ChemblSourceConfig
from bioetl.domain.schemas.registry import create_default_schema_registry
from bioetl.infrastructure.config import provider_registry
from bioetl.infrastructure.config.loader import (
    ConfigFileNotFoundError,
    ConfigValidationError,
    UnknownProviderError,
    get_pipeline_config,
    get_pipeline_config_from_path,
    reset_schema_contract_provider,
    set_schema_contract_provider,
)


@pytest.fixture(autouse=True)
def _reset_provider_registry() -> None:
    provider_registry.clear_provider_registry_cache()
    yield
    provider_registry.clear_provider_registry_cache()


@pytest.fixture(autouse=True)
def _setup_schema_contract_provider() -> None:
    """Set up schema contract provider for tests."""
    registry = create_default_schema_registry()
    contract_provider = SchemaContractProviderImpl(registry)
    set_schema_contract_provider(contract_provider)
    yield
    reset_schema_contract_provider()


def _write_pipeline_with_env_placeholder(config_path: Path) -> None:
    config_path.write_text(
        """id: chembl.molecule
provider: chembl
entity: molecule
primary_key: "${CHEMBL_MOLECULE_PRIMARY_KEY:-molecule_chembl_id}"
input_mode: auto_detect
input_path: null
output_path: /tmp/out
batch_size: 5
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30
    max_retries: 3
    rate_limit_per_sec: 10.0
""",
        encoding="utf-8",
    )


def test_get_pipeline_config_from_path_valid():
    path = Path("tests/fixtures/configs/chembl_activity_valid.yaml")
    config = get_pipeline_config_from_path(path)

    assert config.id == "chembl.activity"
    assert config.provider == "chembl"
    assert isinstance(config.provider_config, ChemblSourceConfig)
    assert config.provider_config.client.timeout_sec == 30


def test_env_placeholder_resolved_from_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    providers_file = Path("tests/fixtures/configs/providers.yaml")
    monkeypatch.setattr(
        provider_registry,
        "DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )
    provider_registry.clear_provider_registry_cache()

    config_path = tmp_path / "chembl_molecule.yaml"
    _write_pipeline_with_env_placeholder(config_path)
    monkeypatch.setenv("CHEMBL_MOLECULE_PRIMARY_KEY", "custom_pk")

    config = get_pipeline_config_from_path(config_path)

    assert config.identity.primary_key == ["custom_pk"]


def test_env_placeholder_falls_back_to_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    providers_file = Path("tests/fixtures/configs/providers.yaml")
    monkeypatch.setattr(
        provider_registry,
        "DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )
    provider_registry.clear_provider_registry_cache()

    config_path = tmp_path / "chembl_molecule.yaml"
    _write_pipeline_with_env_placeholder(config_path)
    monkeypatch.delenv("CHEMBL_MOLECULE_PRIMARY_KEY", raising=False)

    config = get_pipeline_config_from_path(config_path)

    assert config.identity.primary_key == ["molecule_chembl_id"]


def test_extra_field_triggers_validation_error(
    monkeypatch: pytest.MonkeyPatch,
):
    path = Path("tests/fixtures/configs/chembl_activity_invalid_extra_key.yaml")
    providers_file = Path("tests/fixtures/configs/providers.yaml")
    monkeypatch.setattr(
        provider_registry,
        "DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )
    provider_registry.clear_provider_registry_cache()
    with pytest.raises(ConfigValidationError):
        get_pipeline_config_from_path(path)


def test_missing_config_file_raises():
    with pytest.raises(ConfigFileNotFoundError):
        get_pipeline_config_from_path(Path("tests/fixtures/configs/missing.yaml"))


def test_get_pipeline_config_from_path_missing_input_path(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "chembl_activity.yaml"
    config_path.write_text(
        """id: chembl.activity
provider: chembl
entity: activity
input_mode: csv
input_path: ./does_not_exist.csv
output_path: /tmp/out
batch_size: 5
provider_config:
  provider: chembl
  base_url: https://www.ebi.ac.uk/chembl/api/data
  client:
    timeout_sec: 30
    max_retries: 3
    rate_limit_per_sec: 10.0
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError):
        get_pipeline_config_from_path(config_path)


def test_unknown_provider_raises_config_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    base_dir = tmp_path
    pipelines_root = base_dir / "pipelines"
    profiles_root = base_dir / "profiles"
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
  client:
    timeout_sec: 30
    max_retries: 3
    rate_limit_per_sec: 10.0
""",
        encoding="utf-8",
    )

    with pytest.raises(UnknownProviderError):
        get_pipeline_config("unknown.entity", base_dir=base_dir)


def test_provider_registry_allows_known_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base_dir = tmp_path
    providers_file = base_dir / "providers.yaml"
    providers_file.write_text(
        (
            "providers:\n"
            "  - id: chembl\n"
            "    module: tests.dummy\n"
            "    factory: create_chembl\n"
            "    active: true\n"
        ),
        encoding="utf-8",
    )

    pipelines_root = base_dir / "pipelines"
    profiles_root = base_dir / "profiles"
    chembl_dir = pipelines_root / "chembl"
    chembl_dir.mkdir(parents=True)
    profiles_root.mkdir()

    pipeline_file = chembl_dir / "activity.yaml"
    pipeline_file.write_text(
        """id: chembl.activity
provider: chembl
entity: activity
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

    monkeypatch.setattr(
        provider_registry,
        "DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )
    provider_registry.clear_provider_registry_cache()

    config = get_pipeline_config("chembl.activity", base_dir=base_dir)

    assert config.provider == "chembl"


def test_provider_registry_rejects_missing_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base_dir = tmp_path
    providers_file = base_dir / "providers.yaml"
    providers_file.write_text(
        (
            "providers:\n"
            "  - id: dummy\n"
            "    module: tests.dummy\n"
            "    factory: create_dummy\n"
            "    active: true\n"
        ),
        encoding="utf-8",
    )

    pipelines_root = base_dir / "pipelines"
    profiles_root = base_dir / "profiles"
    chembl_dir = pipelines_root / "chembl"
    chembl_dir.mkdir(parents=True)
    profiles_root.mkdir()

    pipeline_file = chembl_dir / "activity.yaml"
    pipeline_file.write_text(
        """id: chembl.activity
provider: chembl
entity: activity
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

    monkeypatch.setattr(
        provider_registry,
        "DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )
    provider_registry.clear_provider_registry_cache()

    with pytest.raises(UnknownProviderError):
        get_pipeline_config("chembl.activity", base_dir=base_dir)


def test_profile_merge_applied(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    base_dir = tmp_path
    providers_file = base_dir / "providers.yaml"
    providers_file.write_text(
        (
            "providers:\n"
            "  - id: chembl\n"
            "    module: tests.dummy\n"
            "    factory: create_chembl\n"
            "    active: true\n"
        ),
        encoding="utf-8",
    )

    pipelines_root = base_dir / "pipelines"
    profiles_root = base_dir / "profiles"
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

    monkeypatch.setattr(
        provider_registry,
        "DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )
    provider_registry.clear_provider_registry_cache()

    config = get_pipeline_config("chembl.activity", base_dir=base_dir)

    assert config.sink.output_path == "/tmp/out"  # pipeline overrides profile
    assert config.source.batch_size == 10
    assert config.provider_config.client.timeout_sec == 10


def test_fields_populated_from_schema_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    providers_file = Path("tests/fixtures/configs/providers.yaml")
    monkeypatch.setattr(
        provider_registry,
        "DEFAULT_PROVIDERS_REGISTRY_PATH",
        providers_file,
    )
    # config_loader.DEFAULT_PROVIDERS_REGISTRY_PATH doesn't exist, removed
    provider_registry.clear_provider_registry_cache()

    pipelines_root = tmp_path / "pipelines" / "chembl"
    pipelines_root.mkdir(parents=True)
    config_path = pipelines_root / "activity.yaml"
    config_path.write_text(
        """id: chembl.activity
provider: chembl
entity: activity
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

    config = get_pipeline_config_from_path(config_path)

    field_names = [field["name"] for field in config.fields]
    assert len(field_names) > 5
    assert "action_type" in field_names
    assert "extracted_at" in field_names
