from __future__ import annotations

import pytest
import yaml

from bioetl.infrastructure.config import load_pipeline_config
from bioetl.infrastructure.config_loader import (
    _normalize_source_config,
)
from bioetl.infrastructure.config_loader import (
    load_pipeline_config as load_pipeline_config_cached,
)
from bioetl.infrastructure.config_loader import (
    load_source_config,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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


def test_load_source_config_legacy_and_new_format_equivalent_chembl(
    tmp_path, monkeypatch
):
    """New source format should normalize to same result as legacy format (chembl)."""
    load_source_config.cache_clear()

    sources_dir = tmp_path / "configs" / "sources"
    sources_dir.mkdir(parents=True)

    legacy = {
        "source": {
            "type": "api",
            "load_strategy": "full",
            "provider_config": {
                "provider": "chembl",
                "base_url": "https://example.chembl/api",
                "auth_type": "public",
                "api_version": "v1",
                "client": {"timeout_sec": 60.0, "max_retries": 3},
                "batch_size": 25,
            },
            "rate_limit": {
                "requests_per_second": 3.0,
                "burst": 10,
                "with_api_key": {"requests_per_second": 6.0, "burst": 20},
            },
            "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
            "health_check": {"endpoint": "/health", "timeout": 5},
        }
    }
    new = {
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
    (sources_dir / "chembl_legacy.yaml").write_text(yaml.dump(legacy))
    (sources_dir / "chembl_new.yaml").write_text(yaml.dump(new))

    cfg_legacy = load_source_config("chembl_legacy")
    load_source_config.cache_clear()
    cfg_new = load_source_config("chembl_new")

    assert cfg_legacy.base_url == cfg_new.base_url
    assert cfg_legacy.timeout_sec == cfg_new.timeout_sec
    assert cfg_legacy.max_retries == cfg_new.max_retries
    assert cfg_legacy.batch_size == cfg_new.batch_size
    assert (
        cfg_legacy.rate_limit.requests_per_second
        == cfg_new.rate_limit.requests_per_second
    )


def test_load_source_config_legacy_and_new_format_equivalent_pubmed(
    tmp_path, monkeypatch
):
    """New source format should normalize to same result as legacy format (pubmed)."""
    load_source_config.cache_clear()

    sources_dir = tmp_path / "configs" / "sources"
    sources_dir.mkdir(parents=True)

    legacy = {
        "source": {
            "type": "api",
            "load_strategy": "full",
            "provider_config": {
                "provider": "pubmed",
                "base_url": "https://example.pubmed/api",
                "auth_type": "api_key",
                "api_key": "${BIOETL_PUBMED_API_KEY}",
                "client": {"timeout": 45.0, "max_retries": 4},
                "batch_size": 100,
            },
            "rate_limit": {
                "requests_per_second": 5.0,
                "burst": 15,
                "with_api_key": {"requests_per_second": 9.0, "burst": 25},
            },
            "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
            "health_check": {"endpoint": "/health", "timeout": 5},
        }
    }
    new = {
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
    (sources_dir / "pubmed_legacy.yaml").write_text(yaml.dump(legacy))
    (sources_dir / "pubmed_new.yaml").write_text(yaml.dump(new))

    cfg_legacy = load_source_config("pubmed_legacy")
    load_source_config.cache_clear()
    cfg_new = load_source_config("pubmed_new")

    assert cfg_legacy.base_url == cfg_new.base_url
    assert cfg_legacy.timeout_sec == cfg_new.timeout_sec
    assert cfg_legacy.max_retries == cfg_new.max_retries
    assert cfg_legacy.batch_size == cfg_new.batch_size
    assert (
        cfg_legacy.rate_limit.requests_per_second
        == cfg_new.rate_limit.requests_per_second
    )


def test_normalize_source_config_maps_rate_limit_and_timeout_aliases() -> None:
    """Normalizer should map old/new aliases for rate-limit and timeout keys."""
    raw = {
        "source": {
            "provider_config": {
                "provider": "pubmed",
                "client": {"timeout": 42.0, "max_retries": 3},
                "batch_size": 30,
            },
            "rate_limit": {
                "requests_per_second": 5.0,
                "with_api_key": {"requests_per_second": 8.0, "burst": 20},
            },
            "health_check": {"endpoint": "/health", "timeout": 9},
        }
    }

    normalized = _normalize_source_config(raw)
    source = normalized["source"]

    assert source["rate_limit"]["authenticated"] == source["rate_limit"]["with_api_key"]
    assert source["health_check"]["timeout_sec"] == 9
    assert source["provider_config"]["client"]["timeout_sec"] == 42.0
    assert source["provider_config"]["batch_size"] == 30


def test_normalize_source_config_supports_top_level_flat_format() -> None:
    """Normalizer should promote top-level api/client/batch into source section."""
    raw = {
        "api": {
            "base_url": "https://example.chembl/api",
            "auth_type": "public",
            "api_version": "v1",
        },
        "client": {"timeout_sec": 33.0, "max_retries": 4},
        "batch": {"api_batch_size": 77, "page_size": 500},
        "rate_limit": {"requests_per_second": 2.0, "burst": 5},
        "circuit_breaker": {"failure_threshold": 6, "recovery_timeout": 120},
        "health_check": {"endpoint": "/health", "timeout": 4},
    }

    normalized = _normalize_source_config(raw)
    source = normalized["source"]

    assert source["provider_config"]["base_url"] == "https://example.chembl/api"
    assert source["provider_config"]["auth_type"] == "public"
    assert source["provider_config"]["api_version"] == "v1"
    assert source["provider_config"]["client"]["timeout_sec"] == 33.0
    assert source["provider_config"]["batch_size"] == 77
    assert source["provider_config"]["page_size"] == 500
    assert source["rate_limit"]["requests_per_second"] == 2.0
    assert source["circuit_breaker"]["failure_threshold"] == 6
    assert source["health_check"]["timeout_sec"] == 4


def test_load_source_config_top_level_flat_format(tmp_path, monkeypatch) -> None:
    """Flat top-level source config should load through SourceYamlConfig."""
    load_source_config.cache_clear()

    sources_dir = tmp_path / "configs" / "sources"
    sources_dir.mkdir(parents=True)

    flat = {
        "api": {
            "base_url": "https://example.pubmed/api",
            "auth_type": "api_key",
            "api_key": "${BIOETL_PUBMED_API_KEY}",
        },
        "client": {"timeout": 45.0, "max_retries": 3},
        "batch": {"api_batch_size": 120},
        "rate_limit": {"requests_per_second": 5.0, "burst": 12},
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
    }

    monkeypatch.chdir(tmp_path)
    (sources_dir / "pubmed_flat.yaml").write_text(yaml.dump(flat))

    cfg = load_source_config("pubmed_flat")

    assert cfg.base_url == "https://example.pubmed/api"
    assert cfg.timeout_sec == 45.0
    assert cfg.max_retries == 3
    assert cfg.batch_size == 120
    assert cfg.rate_limit.requests_per_second == 5.0


def test_dq_thresholds_are_validated_once(setup_configs):
    """DQ thresholds must satisfy domain invariants even in YAML schema."""
    pipelines_dir = setup_configs

    invalid_config = {
        "pipeline_name": "dummy_invalid",
        "provider": "dummy",
        "entity_type": "invalid",
        "primary_keys": ["id"],
        "silver_table": "dummy.test_silver",
        "dq_overrides": {"soft_fail_threshold": 0.3, "hard_fail_threshold": 0.2},
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


# =============================================================================
# Convention-based Path Resolution Tests (ADR-029)
# =============================================================================


def test_convention_based_source_file(setup_configs, tmp_path):
    """Verify source_file is auto-computed from provider when not specified."""
    pipelines_dir = setup_configs

    # Create a config without source_file
    config_data = {
        "pipeline_name": "test_provider_entity",
        "provider": "testprovider",
        "entity_type": "entity",
        "primary_keys": ["id"],
        "silver_table": "test.entity",
    }

    test_dir = pipelines_dir / "testprovider"
    test_dir.mkdir()
    (test_dir / "entity.yaml").write_text(yaml.dump(config_data))

    config = load_pipeline_config("testprovider_entity")

    # source_file should be auto-computed
    assert config.dq_config_file == "../../quality/entities/testprovider/entity.yaml"
    assert (
        config.filter_config_file == "../../filters/entities/testprovider/entity.yaml"
    )
    assert config.data_schema_file == "../schemas/testprovider/entity.yaml"


def test_convention_based_sink_paths(setup_configs, tmp_path):
    """Verify sink paths are auto-computed from provider/entity when not specified."""
    pipelines_dir = setup_configs

    # Create a config without sink paths
    config_data = {
        "pipeline_name": "auto_paths",
        "provider": "autoprov",
        "entity_type": "autoent",
        "primary_keys": ["id"],
        "silver_table": "auto.entity",
    }

    auto_dir = pipelines_dir / "autoprov"
    auto_dir.mkdir()
    (auto_dir / "autoent.yaml").write_text(yaml.dump(config_data))

    config = load_pipeline_config("autoprov_autoent")

    # Sink paths should be auto-computed
    assert config.sink["bronze"].path == "data/output/bronze/autoprov/autoent"
    assert config.sink["silver"].path == "data/output/silver/autoprov/autoent"
    assert config.sink["gold"].path == "data/output/gold/autoprov/autoent"


def test_convention_based_primary_key_propagation(setup_configs, tmp_path):
    """Verify primary_keys are propagated to sink.silver.primary_key."""
    pipelines_dir = setup_configs

    config_data = {
        "pipeline_name": "pk_test_entity",
        "provider": "pktest",
        "entity_type": "entity",
        "primary_keys": ["pk_field1", "pk_field2"],
        "silver_table": "pk.entity",
    }

    pk_dir = pipelines_dir / "pktest"
    pk_dir.mkdir()
    (pk_dir / "entity.yaml").write_text(yaml.dump(config_data))

    config = load_pipeline_config("pktest_entity")

    # primary_keys should be propagated to sink.silver.primary_key
    assert config.sink["silver"].primary_key == ["pk_field1", "pk_field2"]
    # And to sort_by.columns
    assert config.sink["silver"].sort_by.columns == ["pk_field1", "pk_field2"]
    assert config.sink["gold"].sort_by.columns == ["pk_field1", "pk_field2"]


def test_sort_by_inheritance_from_base_validated(setup_configs, tmp_path):
    """sort_by MAY be inherited from _base.yaml with post-merge validation."""
    pipelines_dir = setup_configs

    base_config = {
        "sink": {
            "silver": {"sort_by": {"ascending": True}},
            "gold": {"sort_by": {"ascending": True}},
        }
    }
    (pipelines_dir / "_base.yaml").write_text(yaml.dump(base_config))

    config_data = {
        "pipeline_name": "inherit_sort",
        "provider": "inherit",
        "entity_type": "entity",
        "primary_keys": ["record_id"],
        "silver_table": "inherit.entity",
    }

    inherit_dir = pipelines_dir / "inherit"
    inherit_dir.mkdir()
    (inherit_dir / "entity.yaml").write_text(yaml.dump(config_data))

    config = load_pipeline_config("inherit_entity")

    assert config.sink["silver"].sort_by.columns == ["record_id"]
    assert config.sink["gold"].sort_by.columns == ["record_id"]
    assert config.sink["silver"].sort_by.ascending is True
    assert config.sink["gold"].sort_by.ascending is True


def test_sort_by_validation_fails_without_effective_columns(setup_configs, tmp_path):
    """Loading MUST fail when effective sink.silver/gold.sort_by.columns are empty."""
    pipelines_dir = setup_configs

    config_data = {
        "pipeline_name": "missing_sort",
        "provider": "nosort",
        "entity_type": "entity",
        "primary_keys": ["record_id"],
        "silver_table": "nosort.entity",
        "sink": {
            "silver": {"sort_by": {"columns": []}},
            "gold": {"sort_by": {"columns": []}},
        },
    }

    nosort_dir = pipelines_dir / "nosort"
    nosort_dir.mkdir()
    (nosort_dir / "entity.yaml").write_text(yaml.dump(config_data))

    with pytest.raises(
        ValueError,
        match=r"MUST have effective sink\.(silver|gold)\.sort_by\.columns",
    ):
        load_pipeline_config("nosort_entity")


def test_explicit_paths_override_convention(setup_configs, tmp_path):
    """Verify explicitly specified paths override convention defaults."""
    pipelines_dir = setup_configs

    config_data = {
        "pipeline_name": "explicit_paths",
        "provider": "explicit",
        "entity_type": "entity",
        "primary_keys": ["id"],
        "silver_table": "explicit.entity",
        "sink": {
            "bronze": {"path": "custom/bronze/path"},
            "silver": {"path": "custom/silver/path", "primary_key": ["custom_pk"]},
            "gold": {"path": "custom/gold/path"},
        },
    }

    explicit_dir = pipelines_dir / "explicit"
    explicit_dir.mkdir()
    (explicit_dir / "entity.yaml").write_text(yaml.dump(config_data))

    config = load_pipeline_config("explicit_entity")

    # Explicit paths should be used
    assert config.sink["bronze"].path == "custom/bronze/path"
    assert config.sink["silver"].path == "custom/silver/path"
    assert config.sink["silver"].primary_key == ["custom_pk"]
    assert config.sink["gold"].path == "custom/gold/path"


def test_filter_config_merging(setup_configs, tmp_path):
    """Verify filter config is loaded and merged from filter_config_file."""
    pipelines_dir = setup_configs

    # Create filter config directory structure
    filter_dir = tmp_path / "configs" / "filters" / "entities" / "filtertest"
    filter_dir.mkdir(parents=True)

    # Create filter entity config with complete input_filter
    filter_config = {
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
    (filter_dir / "entity.yaml").write_text(yaml.dump(filter_config))

    # Create pipeline config that references the filter config
    config_data = {
        "pipeline_name": "filtertest_entity",
        "provider": "filtertest",
        "entity_type": "entity",
        "primary_keys": ["id"],
        "silver_table": "filter.entity",
        # filter_config_file will be auto-computed to ../../filters/entities/filtertest/entity.yaml
    }

    filter_pipeline_dir = pipelines_dir / "filtertest"
    filter_pipeline_dir.mkdir()
    (filter_pipeline_dir / "entity.yaml").write_text(yaml.dump(config_data))

    config = load_pipeline_config("filtertest_entity")

    # Filter config should be merged
    assert config.input_filter.enabled is True
    assert config.input_filter.source_path == "data/input/filter.csv"
    assert config.input_filter.batch_size == 50
    assert config.gold_filters.columns == {"status": ["active"]}
    assert config.gold_filters.required_fields == ["id", "name"]


def test_filter_config_explicit_override(setup_configs, tmp_path):
    """Verify explicit pipeline config overrides filter config."""
    pipelines_dir = setup_configs

    # Create filter config directory structure
    filter_dir = tmp_path / "configs" / "filters" / "entities" / "override"
    filter_dir.mkdir(parents=True)

    # Create filter entity config
    filter_config = {
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
    (filter_dir / "entity.yaml").write_text(yaml.dump(filter_config))

    # Create pipeline config with explicit overrides
    config_data = {
        "pipeline_name": "override_entity",
        "provider": "override",
        "entity_type": "entity",
        "primary_keys": ["id"],
        "silver_table": "override.entity",
        # Explicit overrides
        "input_filter": {
            "batch_size": 100,  # Override batch_size
        },
        "gold_filters": {
            "required_fields": ["id", "name", "extra"],  # Override required_fields
        },
    }

    override_dir = pipelines_dir / "override"
    override_dir.mkdir()
    (override_dir / "entity.yaml").write_text(yaml.dump(config_data))

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
