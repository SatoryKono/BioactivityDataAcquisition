from bioetl.domain.configs import PipelineConfig


def test_pipeline_config_migrates_legacy_flat_keys() -> None:
    """Test that legacy flat keys are migrated to decomposed sections."""
    config = PipelineConfig(
        id="test",
        provider="dummy",
        entity="entity",
        input_mode="csv",
        input_path="/tmp/input.csv",
        output_path="/tmp/output",
        batch_size=100,
        provider_config={
            "provider": "dummy",
            "base_url": "http://example.com",
            "client": {
                "timeout_sec": 1.0,
                "max_retries": 0,
            },
        },
        logging={"level": "DEBUG"},
        metrics={"enabled": False},
        pagination={"limit": 10},
        hashing={"algorithm": "sha256"},
        normalization={"id_fields": ["id"]},
        csv_options={"delimiter": ";"},
        features={"rest_interface_enabled": True},
    )

    # Test decomposed identity section
    assert config.identity.id == "test"
    assert config.identity.provider == "dummy"
    assert config.identity.entity == "entity"

    # Test decomposed source section (csv_options now in source.csv)
    assert config.source.input_mode == "csv"
    assert config.source.input_path == "/tmp/input.csv"
    assert config.source.batch_size == 100
    assert config.source.csv.delimiter == ";"

    # Test decomposed sink section
    assert config.sink.output_path == "/tmp/output"
    assert config.sink.dry_run is False

    # Test observability section
    assert config.observability.logging.level == "DEBUG"
    assert config.observability.metrics.enabled is False

    # Test runtime section
    assert config.runtime.pagination.limit == 10

    # Test quality section
    assert config.quality.hashing.algorithm == "sha256"
    assert config.quality.normalization.id_fields == ["id"]

    # Test features section
    assert config.features.interfaces.rest_interface_enabled is True

    # Test backward compatibility properties
    assert config.id == "test"
    assert config.provider == "dummy"
    assert config.entity == "entity"
    assert config.input_mode == "csv"
    assert config.output_path == "/tmp/output"
    assert config.csv_options.delimiter == ";"
