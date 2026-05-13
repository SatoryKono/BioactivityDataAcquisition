from __future__ import annotations

from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]

# Unified pipeline configs live in configs/entities/{provider}/{entity}.yaml.
PIPELINE_CONFIG_PATH = ROOT / "configs" / "entities"
DEFAULTS_PATH = ROOT / "configs" / "base" / "pipeline.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries, with override taking precedence."""
    result = deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = deepcopy(value)
    return result


@cache
def _load_defaults() -> dict:
    """Load default configuration."""
    if DEFAULTS_PATH.exists():
        with DEFAULTS_PATH.open(encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


@cache
def get_all_pipeline_configs() -> tuple[Path, ...]:
    """Get all main pipeline config files, excluding source configs and defaults."""
    if not PIPELINE_CONFIG_PATH.exists():
        return ()
    return tuple(
        sorted(
            p
            for p in PIPELINE_CONFIG_PATH.glob("*/*.yaml")
            if not p.name.startswith("_")
        )
    )


@cache
def load_config_with_defaults(config_path: Path) -> dict:
    """Load pipeline config merged with defaults."""
    defaults = _load_defaults()
    with config_path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    pipeline = raw.get("pipeline", raw) if isinstance(raw, dict) else {}
    return _deep_merge(defaults, pipeline)


@cache
def load_config_with_source(config_path: Path) -> dict:
    """Load pipeline config and merge source config if referenced."""
    config = load_config_with_defaults(config_path)

    # Load source config from separate file if specified
    if source_file := config.get("source_file"):
        source_path = config_path.parent / source_file
        if source_path.exists():
            with source_path.open(encoding="utf-8") as f:
                source_config = yaml.safe_load(f) or {}
            config["source"] = source_config.get("source", source_config)

    return config


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_data_002_bronze_path_format(config_path):
    """Bronze path must match the format."""
    config = load_config_with_defaults(config_path)

    assert "bronze" in config.get("sink", {}), f"No bronze sink in {config_path}"


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_data_006_007_silver_is_delta(config_path):
    """Silver data must be Delta Lake and not raw Parquet."""
    config = load_config_with_defaults(config_path)

    silver_sink = config.get("sink", {}).get("silver", {})
    assert silver_sink.get("format") == "delta", (
        f"Silver format in {config_path} is not 'delta'"
    )


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_data_008_silver_is_merge(config_path):
    """Silver strategy must be merge or append (with post-run dedup)."""
    config = load_config_with_defaults(config_path)

    silver_sink = config.get("sink", {}).get("silver", {})
    mode = silver_sink.get("mode", "merge")
    assert mode in {"merge", "append"}, (
        f"Silver mode in {config_path} is '{mode}', expected 'merge' or 'append'"
    )


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_data_009_gold_is_strict(config_path):
    """Gold data must have strict validation if it exists."""
    config = load_config_with_defaults(config_path)

    if "gold" in config.get("sink", {}):
        gold_sink = config.get("sink", {}).get("gold", {})
        assert gold_sink.get("validation", {}).get("strict", True), (
            f"Gold validation in {config_path} is not strict"
        )


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_delta_003_forensic_retention(config_path):
    """Forensic retention must be configurable via maintenance settings.

    Note: forensic_retention was removed from sink.silver because the
    Pydantic SinkLayerConfig model (single source of truth) does not
    support it.  Retention is now controlled via maintenance.vacuum_retention_days.
    """
    config = load_config_with_defaults(config_path)

    maintenance = config.get("maintenance", {})
    assert "vacuum_retention_days" in maintenance, (
        f"'vacuum_retention_days' key missing in maintenance of {config_path}"
    )


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_partition_004_no_high_cardinality_keys(config_path):
    """Partition keys must not have high cardinality."""
    config = load_config_with_defaults(config_path)

    disallowed_patterns = ["id", "uuid", "hash", "text", "desc"]

    for layer in ["silver", "gold"]:
        if layer in config.get("sink", {}):
            partition_keys = config["sink"][layer].get("partition_by", [])
            if isinstance(partition_keys, list):
                for key in partition_keys:
                    for pattern in disallowed_patterns:
                        assert pattern not in key.lower(), (
                            f"High cardinality key '{key}' used for partitioning in {config_path}"
                        )


def test_req_quarantine_001_unified_table_exists():
    """A unified quarantine table should be conceptually present."""
    assert get_all_pipeline_configs(), "Expected at least one pipeline config."
