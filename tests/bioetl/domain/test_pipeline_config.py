from bioetl.domain.configs import PipelineConfig


def test_pipeline_config_migrates_legacy_flat_keys() -> None:
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
            "timeout_sec": 1.0,
            "max_retries": 0,
        },
        logging={"level": "DEBUG"},
        metrics={"enabled": False},
        pagination={"limit": 10},
        hashing={"algorithm": "sha256"},
        normalization={"id_fields": ["id"]},
        csv_options={"delimiter": ";"},
        features={"rest_interface_enabled": True},
    )

    assert config.observability.logging.level == "DEBUG"
    assert config.runtime.pagination.limit == 10
    assert config.runtime.csv.delimiter == ";"
    assert config.quality.hashing.algorithm == "sha256"
    assert config.quality.normalization.id_fields == ["id"]
    assert config.interface_features.rest_interface_enabled is True
