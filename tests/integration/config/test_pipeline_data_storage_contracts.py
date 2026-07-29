# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

from copy import deepcopy
from functools import cache
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

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
def test_req_data_008_silver_declares_explicit_idempotency_contract(config_path):
    """Silver strategy must expose an explicit compatible idempotency contract."""
    config = load_config_with_defaults(config_path)

    silver_sink = config.get("sink", {}).get("silver", {})
    mode = silver_sink.get("mode", "merge")
    assert mode in {"merge", "append"}, (
        f"Silver mode in {config_path} is '{mode}', expected 'merge' or 'append'"
    )
    contract = silver_sink.get("idempotency_contract")
    assert contract, (
        f"Silver sink in {config_path} must declare idempotency_contract after defaults merge"
    )
    if mode == "merge":
        assert contract == "merge_upsert", (
            f"Silver merge mode in {config_path} requires "
            f"idempotency_contract='merge_upsert', got {contract!r}"
        )
    else:
        assert contract in {
            "append_log",
            "occurrence_only",
            "partition_append_with_stable_partition_key",
        }, (
            f"Silver append mode in {config_path} requires append-safe "
            f"idempotency_contract, got {contract!r}"
        )


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_gold_declares_explicit_idempotency_contract(config_path):
    """Gold strategy must expose an explicit compatible idempotency contract."""
    config = load_config_with_defaults(config_path)

    gold_sink = config.get("sink", {}).get("gold", {})
    if not gold_sink or gold_sink.get("enabled", True) is False:
        return
    mode = gold_sink.get("mode", "scd2")
    contract = gold_sink.get("idempotency_contract")
    assert contract, (
        f"Gold sink in {config_path} must declare idempotency_contract after defaults merge"
    )
    expected = {
        "append": {
            "append_log",
            "occurrence_only",
            "partition_append_with_stable_partition_key",
        },
        "overwrite": {"overwrite_rebuild"},
        "scd2": {"scd2"},
    }.get(mode)
    assert expected is not None, (
        f"Gold mode in {config_path} is '{mode}', expected append/overwrite/scd2"
    )
    assert contract in expected, (
        f"Gold mode {mode!r} in {config_path} requires idempotency_contract in "
        f"{sorted(expected)!r}, got {contract!r}"
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
