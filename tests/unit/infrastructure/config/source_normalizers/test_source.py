"""Same-path owner tests for source config normalizer module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.config.source_normalizers.source import (
    normalize_source_config,
)


pytestmark = pytest.mark.unit


def test_normalize_source_config_rejects_retired_transport_aliases() -> None:
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

    try:
        normalize_source_config(raw)
    except ValueError as error:
        assert "Retired source transport aliases" in str(error)
        assert "api, client" in str(error)
    else:
        raise AssertionError("Expected retired transport aliases to fail")


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
