from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.infrastructure.config import load_pipeline_config, load_source_config
from bioetl.infrastructure.config.source_normalizers.source import (
    normalize_source_config,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

load_pipeline_config_cached = load_pipeline_config


def _minimal_unified_schema() -> dict[str, Any]:
    return {
        "column_groups": [
            {"name": "system", "fields": ["_etl_timestamp"]},
            {"name": "business", "fields": ["id"]},
        ],
        "silver": {"include_groups": ["system", "business"]},
        "gold": {"include_groups": ["business"]},
    }


def _dump_source_config(config: SourceYamlConfig) -> dict[str, Any]:
    """Produce stable dump for source-config golden equivalence checks."""
    return config.model_dump(mode="json", exclude_none=True)


def _write_unified_entity_config(
    entities_dir: Path,
    provider: str,
    entity: str,
    pipeline_cfg: dict[str, Any],
    *,
    schema: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
    quality: dict[str, Any] | None = None,
    contracts: dict[str, Any] | None = None,
) -> Path:
    entity_dir = entities_dir / provider
    entity_dir.mkdir(parents=True, exist_ok=True)
    entity_path = entity_dir / f"{entity}.yaml"

    payload = {
        "version": "1.0.0",
        "provider": provider,
        "entity": entity,
        "pipeline": pipeline_cfg,
        "schema": schema or _minimal_unified_schema(),
        "quality": quality or {},
        "filters": filters or {},
        "contracts": contracts
        or {
            "primary_key": ["id"],
            "merge_keys": ["id"],
        },
    }
    entity_path.write_text(yaml.dump(payload))
    return entity_path


@pytest.fixture
def setup_configs(tmp_path, monkeypatch):
    """
    Sets up a temporary configs directory structure and changes the current working directory
    to tmp_path so the relative paths in load_pipeline_config work correctly.

    IMPORTANT: Clears the LRU cache on setup AND teardown to prevent cross-test contamination.
    """
    # Clear cache at START of each test to ensure clean state
    load_pipeline_config_cached.cache_clear()
    load_source_config.cache_clear()

    # Create unified entities directory in temp dir
    entities_dir = tmp_path / "configs" / "entities"
    entities_dir.mkdir(parents=True)

    # Base valid config data
    base_config = {
        "pipeline_name": "dummy_test",
        "provider": "dummy",
        "entity_type": "test",
        "business_primary_keys": ["id"],
        "silver_table": "dummy.test_silver",
        "batch_size": 100,
        "checkpoint_interval": 1000,
    }

    # Create configs/entities/dummy/test.yaml (for dummy_test)
    _write_unified_entity_config(
        entities_dir,
        "dummy",
        "test",
        base_config,
    )

    # Create configs/entities/chembl/activity.yaml
    chembl_config = base_config.copy()
    chembl_config.update(
        {
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity_type": "activity",
            "silver_table": "chembl.activity_silver",
        }
    )
    _write_unified_entity_config(
        entities_dir,
        "chembl",
        "activity",
        chembl_config,
    )

    # Change CWD to tmp_path so "configs/entities/..." resolves to our temp files
    monkeypatch.chdir(tmp_path)

    yield entities_dir

    # Teardown: Clear the LRU cache to prevent cross-test contamination
    # This is critical for test isolation when integration tests run after unit tests
    load_pipeline_config_cached.cache_clear()
    load_source_config.cache_clear()


def test_load_dynamic_pipeline(setup_configs):
    """Verify that a dynamically created pipeline loads correctly."""
    # dummy_test corresponds to configs/entities/dummy/test.yaml
    config = load_pipeline_config("dummy_test")
    assert isinstance(config, PipelineYamlConfig)
    assert config.pipeline_name == "dummy_test"
    assert config.provider == "dummy"


def test_load_registered_pipeline(setup_configs):
    """Verify that a standard pipeline loads correctly via dynamic resolution."""
    # chembl_activity should resolve to configs/entities/chembl/activity.yaml
    config = load_pipeline_config("chembl_activity")
    assert isinstance(config, PipelineYamlConfig)
    assert config.provider == "chembl"
    assert config.entity_type == "activity"


def test_load_nonexistent_pipeline(setup_configs):
    """Verify that a truly nonexistent pipeline raises ValueError."""
    with pytest.raises(ValueError, match="Configuration file not found"):
        load_pipeline_config("nonexistent_pipeline")


def test_load_pipeline_from_unified_entity_when_legacy_missing(tmp_path, monkeypatch):
    """load_pipeline_config should support configs/entities/{provider}/{entity}.yaml."""
    load_pipeline_config_cached.cache_clear()
    load_source_config.cache_clear()

    entity_dir = tmp_path / "configs" / "entities" / "demo"
    entity_dir.mkdir(parents=True)
    (entity_dir / "item.yaml").write_text(
        yaml.dump(
            {
                "version": "1.0.0",
                "provider": "demo",
                "entity": "item",
                "pipeline": {
                    "pipeline_name": "demo_item",
                    "provider": "demo",
                    "entity_type": "item",
                    "business_primary_keys": ["id"],
                },
                "schema": {
                    "column_groups": [
                        {"name": "system", "fields": ["_ingestion_ts"]},
                        {"name": "business", "fields": ["id"]},
                    ],
                    "silver": {"include_groups": ["system", "business"]},
                    "gold": {"include_groups": ["business"]},
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)
    config = load_pipeline_config("demo_item")
    assert isinstance(config, PipelineYamlConfig)
    assert config.pipeline_name == "demo_item"
    assert config.provider == "demo"
    assert config.entity_type == "item"


def test_load_invalid_name_format(setup_configs):
    """Verify names without provider_entity format are rejected."""
    with pytest.raises(ValueError, match="must be in '<provider>_<entity>' format"):
        load_pipeline_config("invalidname")


def test_load_name_without_separator_raises(setup_configs):
    """Pipeline names without underscore must not resolve any config."""
    _ = setup_configs
    with pytest.raises(ValueError, match="must be in '<provider>_<entity>' format"):
        load_pipeline_config("simple")


def test_load_source_config_rejects_retired_transport_alias_sections_chembl(
    tmp_path, monkeypatch
):
    """Legacy source.api/source.client/source.batch aliases should fail fast."""
    load_source_config.cache_clear()

    providers_dir = tmp_path / "configs" / "providers"
    providers_dir.mkdir(parents=True)

    legacy = {
        "source": {
            "type": "api",
            "load_strategy": "full",
            "api": {
                "base_url": "https://example.chembl/api",
                "auth_type": "public",
                "api_version": "v1",
            },
            "client": {"timeout": 60.0, "max_retries": 3},
            "batch": {"batch_size": 25},
            "provider_config": {"provider": "chembl"},
            "rate_limit": {
                "requests_per_second": 3.0,
                "burst": 10,
                "authenticated": {"requests_per_second": 6.0, "burst": 20},
            },
            "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
            "health_check": {"endpoint": "/health", "timeout_sec": 5},
        }
    }

    monkeypatch.chdir(tmp_path)
    (providers_dir / "chembl_legacy.yaml").write_text(yaml.dump(legacy))

    with pytest.raises(ValueError, match="Retired source transport aliases"):
        normalize_source_config(legacy)

    with pytest.raises(ValueError, match="Retired source transport aliases"):
        load_source_config("chembl_legacy")


def test_load_source_config_from_unified_provider_file(tmp_path, monkeypatch):
    """Source config should load from configs/providers/{provider}.yaml source section."""
    load_source_config.cache_clear()

    providers_dir = tmp_path / "configs" / "providers"
    providers_dir.mkdir(parents=True)

    unified_provider = {
        "version": "1.0.0",
        "provider": "chembl",
        "source": {
            "type": "api",
            "load_strategy": "full",
            "provider_config": {
                "provider": "chembl",
                "base_url": "https://example.chembl/api",
                "auth_type": "public",
                "client": {"timeout_sec": 55.0, "max_retries": 4},
                "pagination": {"page_size": 111, "id_batch_size": 22},
            },
            "rate_limit": {"requests_per_second": 4.0, "burst": 8},
            "circuit_breaker": {"failure_threshold": 6, "recovery_timeout": 200},
        },
    }
    (providers_dir / "chembl.yaml").write_text(yaml.dump(unified_provider))

    monkeypatch.chdir(tmp_path)
    cfg = load_source_config("chembl")

    assert cfg.base_url == "https://example.chembl/api"
    assert cfg.timeout_sec == pytest.approx(55.0)
    assert cfg.max_retries == 4
    assert cfg.page_size == 111
    assert cfg.batch_size == 22


def test_load_source_config_rejects_retired_transport_alias_sections_pubmed(
    tmp_path, monkeypatch
):
    """Legacy PubMed source aliases should fail fast."""
    load_source_config.cache_clear()

    providers_dir = tmp_path / "configs" / "providers"
    providers_dir.mkdir(parents=True)

    legacy = {
        "source": {
            "type": "api",
            "load_strategy": "full",
            "api": {
                "base_url": "https://example.pubmed/api",
                "auth_type": "api_key",
                "api_key": "${BIOETL_PUBMED_API_KEY}",
            },
            "client": {"timeout_sec": 45.0, "max_retries": 4},
            "batch": {"size": 100},
            "provider_config": {"provider": "pubmed"},
            "rate_limit": {
                "requests_per_second": 5.0,
                "burst": 15,
                "authenticated": {"requests_per_second": 9.0, "burst": 25},
            },
            "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
            "health_check": {"endpoint": "/health", "timeout_sec": 5},
        }
    }

    monkeypatch.chdir(tmp_path)
    (providers_dir / "pubmed_legacy.yaml").write_text(yaml.dump(legacy))

    with pytest.raises(ValueError, match="Retired source transport aliases"):
        normalize_source_config(legacy)

    with pytest.raises(ValueError, match="Retired source transport aliases"):
        load_source_config("pubmed_legacy")


def test_normalize_source_config_maps_rate_limit_and_timeout_aliases() -> None:
    """Normalizer should map old/new aliases for rate-limit and timeout keys."""
    raw = {
        "source": {
            "provider_config": {
                "provider": "pubmed",
                "client": {"timeout": 42.0, "max_retries": 3},
                "pagination": {"id_batch_size": 30},
            },
            "rate_limit": {
                "requests_per_second": 5.0,
                "with_api_key": {"requests_per_second": 8.0, "burst": 20},
            },
            "health_check": {"endpoint": "/health", "timeout": 9},
        }
    }

    normalized = normalize_source_config(raw)
    source = normalized["source"]

    assert source["rate_limit"]["authenticated"] == source["rate_limit"]["with_api_key"]
    assert source["health_check"]["timeout_sec"] == 9
    assert source["provider_config"]["client"]["timeout_sec"] == pytest.approx(42.0)
    assert source["provider_config"]["pagination"]["id_batch_size"] == 30


def test_load_source_config_rejects_missing_source_section(
    tmp_path, monkeypatch
) -> None:
    """Loader should reject provider files without a source section."""
    load_source_config.cache_clear()

    providers_dir = tmp_path / "configs" / "providers"
    providers_dir.mkdir(parents=True)

    malformed_provider = {"version": "1.0.0", "provider": "pubmed"}
    (providers_dir / "pubmed.yaml").write_text(yaml.dump(malformed_provider))

    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="requires a top-level 'source' section"):
        load_source_config("pubmed")


def test_dq_thresholds_are_validated_once(setup_configs):
    """DQ thresholds must satisfy domain invariants even in YAML schema."""
    entities_dir = setup_configs

    invalid_config = {
        "pipeline_name": "dummy_invalid",
        "provider": "dummy",
        "entity_type": "invalid",
        "business_primary_keys": ["id"],
        "silver_table": "dummy.test_silver",
        "dq_overrides": {"soft_fail_threshold": 0.3, "hard_fail_threshold": 0.2},
    }

    _write_unified_entity_config(
        entities_dir,
        "dummy",
        "invalid",
        invalid_config,
    )

    with pytest.raises(ValueError, match="soft_fail_threshold must be strictly less"):
        load_pipeline_config("dummy_invalid")


def test_gold_filters_loading(setup_configs):
    """Verify loading of gold_filters from YAML."""
    entities_dir = setup_configs

    config_data = {
        "pipeline_name": "chembl_filters",
        "provider": "chembl",
        "entity_type": "filters",
        "business_primary_keys": ["id"],
        "silver_table": "chembl.filters",
        "gold_filters": {
            "columns": {"standard_type": ["IC50", "Ki"]},
            "required_fields": ["value"],
            "exclude_if_present": ["invalid"],
        },
    }

    _write_unified_entity_config(
        entities_dir,
        "chembl",
        "filters",
        config_data,
        filters={"gold_filters": config_data["gold_filters"]},
    )

    config = load_pipeline_config("chembl_filters")
    # Note: load_pipeline_config returns PipelineYamlConfig (infrastructure layer)
    # which uses lists. Use get_pipeline_config for domain PipelineConfig with tuples.
    assert config.gold_filters.columns == {"standard_type": ["IC50", "Ki"]}
    assert config.gold_filters.required_fields == ["value"]
    assert config.gold_filters.exclude_if_present == ["invalid"]


# =============================================================================
# Convention-based Path Resolution Tests (ADR-029)
# =============================================================================


def test_convention_based_source_file(setup_configs, tmp_path):
    """Verify provider source config is loaded without pipeline-level source_file."""
    entities_dir = setup_configs

    config_data = {
        "pipeline_name": "test_provider_entity",
        "provider": "testprovider",
        "entity_type": "entity",
        "business_primary_keys": ["id"],
        "silver_table": "test.entity",
    }

    _write_unified_entity_config(
        entities_dir,
        "testprovider",
        "entity",
        config_data,
    )
    providers_dir = Path("configs/providers")
    providers_dir.mkdir(parents=True, exist_ok=True)
    (providers_dir / "testprovider.yaml").write_text(
        yaml.dump(
            {
                "version": "1.0.0",
                "provider": "testprovider",
                "source": {
                    "provider_config": {"provider": "testprovider"},
                    "pagination": {"id_batch_size": 20},
                },
            }
        ),
        encoding="utf-8",
    )

    config = load_pipeline_config("testprovider_entity")

    assert config.dq_config_file == "../../entities/testprovider/entity.yaml"
    assert config.filter_config_file == "../../entities/testprovider/entity.yaml"
    assert config.source is not None


def test_convention_based_sink_paths(setup_configs, tmp_path):
    """Verify sink paths are auto-computed from provider/entity when not specified."""
    entities_dir = setup_configs

    # Create a config without sink paths
    config_data = {
        "pipeline_name": "auto_paths",
        "provider": "autoprov",
        "entity_type": "autoent",
        "business_primary_keys": ["id"],
        "silver_table": "auto.entity",
    }

    _write_unified_entity_config(
        entities_dir,
        "autoprov",
        "autoent",
        config_data,
    )

    config = load_pipeline_config("autoprov_autoent")

    # Sink paths should be auto-computed
    assert config.sink["bronze"].path == "data/output/bronze/autoprov/autoent"
    assert config.sink["silver"].path == "data/output/silver/autoprov/autoent"
    assert config.sink["gold"].path == "data/output/gold/autoprov/autoent"


def test_convention_based_table_names_use_provider_entity(setup_configs):
    """Verify table-name defaults use provider.entity canonical notation."""
    entities_dir = setup_configs

    config_data = {
        "pipeline_name": "autotable_entity",
        "provider": "autotable",
        "entity_type": "entity",
        "business_primary_keys": ["id"],
    }

    _write_unified_entity_config(
        entities_dir,
        "autotable",
        "entity",
        config_data,
    )

    config = load_pipeline_config("autotable_entity")

    assert config.silver_table == "autotable.entity"
    assert config.gold_table == "autotable.entity"


def test_explicit_paths_override_convention(setup_configs, tmp_path):
    """Verify explicitly specified paths override convention defaults."""
    entities_dir = setup_configs

    config_data = {
        "pipeline_name": "explicit_paths",
        "provider": "explicit",
        "entity_type": "entity",
        "business_primary_keys": ["id"],
        "silver_table": "explicit.entity",
        "sink": {
            "bronze": {"path": "custom/bronze/path"},
            "silver": {"path": "custom/silver/path"},
            "gold": {"path": "custom/gold/path"},
        },
    }

    _write_unified_entity_config(
        entities_dir,
        "explicit",
        "entity",
        config_data,
    )

    config = load_pipeline_config("explicit_entity")

    # Explicit paths should be used
    assert config.sink["bronze"].path == "custom/bronze/path"
    assert config.sink["silver"].path == "custom/silver/path"
    assert config.sink["gold"].path == "custom/gold/path"


def test_filter_config_merging(setup_configs, tmp_path):
    """Verify filter config is loaded and merged from filter_config_file."""
    entities_dir = setup_configs

    # Create unified entity config with complete filters section
    filters_section = {
        "input_filter": {
            "enabled": True,
            "source_path": "data/input/filter.csv",
            "column_name": "filter_col",
            "filter_field": "filter_field",
            "batch_size": 50,
        },
        "gold_filters": {
            "columns": {"status": ["active"]},
            "required_fields": ["id", "name"],
        },
    }

    # Create pipeline config that references the filter config
    config_data = {
        "pipeline_name": "filtertest_entity",
        "provider": "filtertest",
        "entity_type": "entity",
        "business_primary_keys": ["id"],
        "silver_table": "filter.entity",
        # filter_config_file will be auto-computed to ../../entities/filtertest/entity.yaml
    }

    _write_unified_entity_config(
        entities_dir,
        "filtertest",
        "entity",
        config_data,
        filters=filters_section,
    )

    config = load_pipeline_config("filtertest_entity")

    # Filter config should be merged
    assert config.input_filter.enabled is True
    assert config.input_filter.source_path == "data/input/filter.csv"
    assert config.input_filter.batch_size == 50
    assert config.gold_filters.columns == {"status": ["active"]}
    assert config.gold_filters.required_fields == ["id", "name"]


def test_filter_config_explicit_override(setup_configs, tmp_path):
    """Verify explicit pipeline config overrides filter config."""
    entities_dir = setup_configs

    # Create unified entity config filters section
    filters_section = {
        "input_filter": {
            "enabled": True,
            "source_path": "data/input/base.csv",
            "column_name": "id_col",
            "filter_field": "id",
            "batch_size": 50,
        },
        "gold_filters": {
            "columns": {"status": ["active"]},
            "required_fields": ["id"],
        },
    }

    # Create pipeline config with explicit overrides
    config_data = {
        "pipeline_name": "override_entity",
        "provider": "override",
        "entity_type": "entity",
        "business_primary_keys": ["id"],
        "silver_table": "override.entity",
        # Explicit overrides
        "input_filter": {
            "batch_size": 100,  # Override batch_size
        },
        "gold_filters": {
            "required_fields": ["id", "name", "extra"],  # Override required_fields
        },
    }

    _write_unified_entity_config(
        entities_dir,
        "override",
        "entity",
        config_data,
        filters=filters_section,
    )

    config = load_pipeline_config("override_entity")

    # Explicit overrides should take precedence
    assert config.input_filter.enabled is True  # From filter config
    assert (
        config.input_filter.source_path == "data/input/base.csv"
    )  # From filter config
    assert config.input_filter.batch_size == 100  # Explicit override
    assert config.gold_filters.columns == {"status": ["active"]}  # From filter config
    assert config.gold_filters.required_fields == [
        "id",
        "name",
        "extra",
    ]  # Explicit override


def test_load_source_section_reuses_canonical_source_loader(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    """Source merge should reuse the canonical source loader output."""
    from bioetl.infrastructure.config.pipeline_payload_normalization import (
        load_source_section as _load_source_section,
    )
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

    config = {
        "provider": "chembl",
        "source": {"rate_limit": {"requests_per_second": 999}},
    }
    config_path = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("pipeline: {}\n", encoding="utf-8")

    base_source = SourceYamlConfig.model_validate(
        {
            "source": {
                "provider_config": {"provider": "chembl"},
            }
        }
    )

    monkeypatch.setattr(
        "bioetl.infrastructure.config.source_config_loader.load_source_config",
        lambda provider: base_source,
    )

    _load_source_section(config, config_path)

    assert config["source"]["rate_limit"]["requests_per_second"] == 999
    assert config["source"]["provider_config"]["provider"] == "chembl"


@pytest.mark.parametrize(
    ("source_override", "expected_fragment"),
    [
        (
            {"provider_config": {"page_size": 999}},
            "source.provider_config.page_size",
        ),
        (
            {"provider_config": {"pagination": {"page_size": 999}}},
            "source.provider_config.pagination",
        ),
        (
            {"batch_size": 999},
            "source.batch_size",
        ),
        (
            {"batch": {"page_size": 999}},
            "source.batch",
        ),
    ],
)
def test_load_source_section_rejects_pipeline_source_pagination_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    source_override: dict[str, Any],
    expected_fragment: str,
) -> None:
    """Pipeline source merges must reject direct pagination override seams."""
    from bioetl.infrastructure.config.pipeline_payload_normalization import (
        load_source_section as _load_source_section,
    )
    from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

    config = {
        "provider": "chembl",
        "source": source_override,
    }
    config_path = tmp_path / "configs" / "entities" / "chembl" / "activity.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("pipeline: {}\n", encoding="utf-8")

    base_source = SourceYamlConfig.model_validate(
        {
            "source": {
                "provider_config": {"provider": "chembl"},
            }
        }
    )

    monkeypatch.setattr(
        "bioetl.infrastructure.config.source_config_loader.load_source_config",
        lambda provider: base_source,
    )

    with pytest.raises(ValueError, match="page_size_override") as exc_info:
        _load_source_section(config, config_path)

    assert expected_fragment in str(exc_info.value)


def test_pipeline_source_file_is_rejected_as_legacy_key(setup_configs):
    """Pipeline YAML must reject legacy source_file after normalization hardening."""
    entities_dir = setup_configs

    config_data = {
        "pipeline_name": "legacy_source_bridge",
        "provider": "chembl",
        "entity_type": "bridge",
        "business_primary_keys": ["id"],
        "silver_table": "chembl.bridge",
        "source_file": "../../providers/chembl.yaml",
    }

    _write_unified_entity_config(
        entities_dir,
        "chembl",
        "bridge",
        config_data,
    )

    with pytest.raises(ValueError, match="source_file"):
        load_pipeline_config("chembl_bridge")
