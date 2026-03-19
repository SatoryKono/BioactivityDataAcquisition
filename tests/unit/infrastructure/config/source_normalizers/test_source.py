"""Same-path owner tests for source config normalizer module."""

from __future__ import annotations

from bioetl.infrastructure.config.source_normalizers.source import (
    normalize_source_config,
)


def test_normalize_source_config_merges_api_and_client_aliases() -> None:
    raw = {
        "source": {
            "api": {
                "base_url": "https://example.org",
                "auth_type": "api_key",
                "api_key": "secret",
            },
            "client": {"timeout": 5},
            "rate_limit": {"with_api_key": {"requests_per_second": 2}},
        }
    }

    normalized = normalize_source_config(raw)
    provider_config = normalized["source"]["provider_config"]

    assert provider_config["base_url"] == "https://example.org"
    assert provider_config["auth_type"] == "api_key"
    assert provider_config["api_key"] == "secret"
    assert provider_config["client"]["timeout"] == 5
    assert provider_config["client"]["timeout_sec"] == 5
    assert normalized["source"]["rate_limit"]["authenticated"] == {
        "requests_per_second": 2
    }


def test_normalize_source_config_rejects_retired_source_root_pagination_aliases() -> (
    None
):
    raw = {"source": {"batch_size": 100}}

    try:
        normalize_source_config(raw)
    except ValueError as error:
        assert "Retired source root pagination aliases" in str(error)
    else:
        raise AssertionError("Expected retired root pagination aliases to fail")
