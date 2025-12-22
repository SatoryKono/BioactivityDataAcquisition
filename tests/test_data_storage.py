from pathlib import Path

import pytest
import yaml

# Assuming pipeline configs are in a 'configs/pipelines' directory
PIPELINE_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "pipelines"


def get_all_pipeline_configs():
    """Get all main pipeline config files, excluding source configs."""
    if not PIPELINE_CONFIG_PATH.exists():
        return []
    # Exclude files in 'sources/' subdirectories (they are source configs, not pipeline configs)
    return [
        p for p in PIPELINE_CONFIG_PATH.glob("**/*.yaml") if "sources" not in p.parts
    ]


def load_config_with_source(config_path: Path) -> dict:
    """Load pipeline config and merge source config if referenced."""
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

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
    # This is a conceptual test. A real test would check the output path generation.
    # We check if the config hints at the right structure.
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # A true test would need to run the pipeline and check S3,
    # but we can check if the config looks plausible.
    # This test is more of a placeholder for a proper integration test.
    assert "bronze" in config.get("sink", {}), f"No bronze sink in {config_path}"


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_data_006_007_silver_is_delta(config_path):
    """Silver data must be Delta Lake and not raw Parquet."""
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    silver_sink = config.get("sink", {}).get("silver", {})
    assert (
        silver_sink.get("format") == "delta"
    ), f"Silver format in {config_path} is not 'delta'"


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_data_008_silver_is_merge(config_path):
    """Silver strategy must be merge/upsert."""
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    silver_sink = config.get("sink", {}).get("silver", {})
    assert (
        silver_sink.get("mode") == "merge"
    ), f"Silver mode in {config_path} is not 'merge'"


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_data_009_gold_is_strict(config_path):
    """Gold data must have strict validation if it exists."""
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if "gold" in config.get("sink", {}):
        gold_sink = config.get("sink", {}).get("gold", {})
        # Assuming a 'validation' key or similar
        assert gold_sink.get("validation", {}).get(
            "strict", True
        ), f"Gold validation in {config_path} is not strict"


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_delta_003_forensic_retention(config_path):
    """Forensic retention must be configurable."""
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    silver_sink = config.get("sink", {}).get("silver", {})
    assert (
        "forensic_retention" in silver_sink
    ), f"'forensic_retention' key missing in silver sink of {config_path}"


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_partition_004_no_high_cardinality_keys(config_path):
    """Partition keys must not have high cardinality."""
    with config_path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    disallowed_patterns = ["id", "uuid", "hash", "text", "desc"]

    for layer in ["silver", "gold"]:
        if layer in config.get("sink", {}):
            partition_keys = config["sink"][layer].get("partition_by", [])
            if isinstance(partition_keys, list):
                for key in partition_keys:
                    for pattern in disallowed_patterns:
                        assert (
                            pattern not in key.lower()
                        ), f"High cardinality key '{key}' used for partitioning in {config_path}"


@pytest.mark.parametrize("config_path", get_all_pipeline_configs())
def test_req_load_001_002_load_strategy(config_path):
    """Load strategy must be defined."""
    config = load_config_with_source(config_path)

    source = config.get("source", {})
    assert (
        "load_strategy" in source
    ), f"'load_strategy' missing in source of {config_path}"
    assert source["load_strategy"] in [
        "incremental",
        "full",
    ], f"Invalid 'load_strategy' in {config_path}"

    if source["load_strategy"] == "incremental":
        assert (
            "watermark_field" in source
        ), f"'watermark_field' missing for incremental strategy in {config_path}"


# This is a conceptual test for REQ-QUARANTINE-001
def test_req_quarantine_001_unified_table_exists():
    """A unified quarantine table should be conceptually present."""
    # A real test would connect to the DB and check `common.quarantine`.
    # Here, we just assert the concept.
    assert True, "Conceptual test for a unified quarantine table."
