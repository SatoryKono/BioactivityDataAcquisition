from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config._base import get_pipeline_config
from bioetl.infrastructure.config.pipeline_config_api import (
    load_pipeline_config_from_root,
)
from bioetl.infrastructure.config.config_root import (
    ConfigRootResolver,
    get_default_repo_root,
    resolve_configs_root,
)


pytestmark = pytest.mark.unit


def test_resolve_configs_root_defaults_to_repo_configs_directory() -> None:
    repo_root = get_default_repo_root()

    assert resolve_configs_root() == (repo_root / "configs").resolve()
    assert (repo_root / "pyproject.toml").exists()
    assert (repo_root / "configs").is_dir()


def test_resolve_configs_root_honors_explicit_path() -> None:
    explicit_root = Path("/tmp/bioetl-configs")

    assert resolve_configs_root(explicit_root) == explicit_root


def test_resolve_configs_root_resolves_relative_path_from_repo_root() -> None:
    repo_root = get_default_repo_root()

    assert resolve_configs_root(Path("configs")) == (repo_root / "configs").resolve()


def test_resolve_configs_root_ignores_cwd_configs_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = get_default_repo_root()
    (tmp_path / "configs").mkdir()
    monkeypatch.chdir(tmp_path)

    assert resolve_configs_root() == (repo_root / "configs").resolve()


def test_resolve_configs_root_can_opt_into_cwd_configs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cwd_configs = tmp_path / "configs"
    cwd_configs.mkdir()
    monkeypatch.chdir(tmp_path)

    assert resolve_configs_root(prefer_cwd_configs=True) == cwd_configs.resolve()


def test_config_root_resolver_allows_explicit_repo_override(tmp_path: Path) -> None:
    resolver = ConfigRootResolver(repo_root=tmp_path)

    assert resolver.resolve() == (tmp_path / "configs").resolve()


def test_get_default_repo_root_points_to_repository_root() -> None:
    repo_root = get_default_repo_root()

    assert (repo_root / "src").is_dir()
    assert (repo_root / "configs").is_dir()
    assert (repo_root / "pyproject.toml").is_file()
    assert (repo_root / "src" / "bioetl").is_dir()


def test_get_pipeline_config_falls_back_to_repo_root_when_cwd_is_src(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = get_default_repo_root()
    monkeypatch.chdir(repo_root / "src")
    get_pipeline_config.cache_clear()

    try:
        config = get_pipeline_config("chembl_assay")
    finally:
        get_pipeline_config.cache_clear()

    assert config.provider == "chembl"
    assert config.entity_type == "assay"


def test_get_pipeline_config_ignores_cwd_local_configs_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "configs" / "entities" / "tmp"
    config_dir.mkdir(parents=True)
    (config_dir / "pipeline.yaml").write_text(
        "\n".join(
            [
                "version: '1.0.0'",
                "provider: tmp",
                "entity: pipeline",
                "pipeline:",
                "  pipeline_name: tmp_pipeline",
                "  provider: tmp",
                "  entity_type: pipeline",
                "  business_primary_keys: ['id']",
                "  silver_table: 'tmp.pipeline'",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    get_pipeline_config.cache_clear()

    try:
        with pytest.raises(ValueError, match="Configuration file not found"):
            get_pipeline_config("tmp_pipeline")
    finally:
        get_pipeline_config.cache_clear()


def test_get_pipeline_config_uses_explicit_configs_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "configs" / "entities" / "tmp"
    config_dir.mkdir(parents=True)
    (tmp_path / "configs" / "base").mkdir(parents=True)
    (tmp_path / "configs" / "base" / "quality.yaml").write_text(
        "\n".join(
            [
                "version: '1.0.0'",
                "thresholds:",
                "  soft_fail: 0.05",
                "  hard_fail: 0.20",
                "strict_validation: false",
                "invalid_record_policy: quarantine",
                "report:",
                "  enabled: true",
                "  format: json",
                "  include_sample_failures: true",
                "  sample_size: 10",
                "  output_path: null",
                "common_field_validations: []",
                "common_cross_field_validations: []",
            ]
        ),
        encoding="utf-8",
    )
    (config_dir / "pipeline.yaml").write_text(
        "\n".join(
            [
                "version: '1.0.0'",
                "provider: tmp",
                "entity: pipeline",
                "pipeline:",
                "  pipeline_name: tmp_pipeline",
                "  provider: tmp",
                "  entity_type: pipeline",
                "  business_primary_keys: ['id']",
                "  silver_table: 'tmp.pipeline'",
                "  sink: {}",
                "schema:",
                "  column_groups:",
                "    - name: system",
                "      fields: [entity_id]",
                "    - name: business",
                "      fields: [value]",
                "  silver:",
                "    include_groups: [system, business]",
                "  gold:",
                "    include_groups: [system, business]",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    config = load_pipeline_config_from_root(
        "tmp_pipeline",
        configs_root=tmp_path / "configs",
    )

    assert config.provider == "tmp"
    assert config.entity_type == "pipeline"
