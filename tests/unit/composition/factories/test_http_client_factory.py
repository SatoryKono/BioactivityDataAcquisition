"""Unit tests for HttpClientFactory."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.http_client_factory import (
    HttpClientFactory,
    ResolvedHttpConfig,
)
from bioetl.composition.providers.provider_registry import HttpConfig


@pytest.mark.unit
class TestHttpClientFactory:
    """Tests for provider HTTP client construction."""

    def test_create_for_unknown_provider_raises_value_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Factory should fail fast for unknown providers."""
        from bioetl.composition.factories import http_client_factory as module

        monkeypatch.setattr(module, "ensure_providers_loaded", lambda: None)
        monkeypatch.setattr(module.ProviderRegistry, "is_registered", lambda _: False)
        monkeypatch.setattr(
            module.ProviderRegistry, "list_providers", lambda: ["chembl", "pubmed"]
        )

        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            HttpClientFactory.create_for_provider("unknown")

    def test_create_uses_source_config_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Source YAML config should be primary source of HTTP settings."""
        from bioetl.composition.factories import http_client_factory as module

        source_config = SimpleNamespace(
            rate_limit=SimpleNamespace(requests_per_second=7.5, burst=15),
            circuit_breaker=SimpleNamespace(failure_threshold=9, recovery_timeout=120),
            timeout_sec=42.0,
            max_retries=5,
            retry_base_delay=0.5,
            retry_max_delay=9.0,
            max_connections=100,
            max_keepalive_connections=20,
        )
        client_ctor = MagicMock(return_value="client-from-source")

        monkeypatch.setattr(module, "ensure_providers_loaded", lambda: None)
        monkeypatch.setattr(module.ProviderRegistry, "is_registered", lambda _: True)
        monkeypatch.setattr(module, "load_source_config", lambda _: source_config)
        monkeypatch.setattr(module.ProviderRegistry, "get_http_config", lambda _: None)
        monkeypatch.setattr(module, "UnifiedHTTPClient", client_ctor)

        result = HttpClientFactory.create_for_provider("chembl")

        assert result == "client-from-source"
        kwargs = client_ctor.call_args.kwargs
        assert kwargs["timeout"] == 42.0
        assert kwargs["provider"] == "chembl"
        assert kwargs["rate_limiter"].rate == 7.5
        assert kwargs["rate_limiter"].capacity == 15
        assert kwargs["circuit_breaker"].failure_threshold == 9
        assert kwargs["circuit_breaker"].recovery_timeout == 120
        assert kwargs["retry_config"].max_attempts == 5
        assert kwargs["retry_config"].base_delay == 0.5
        assert kwargs["retry_config"].max_delay == 9.0
        assert kwargs["max_connections"] == 100
        assert kwargs["max_keepalive_connections"] == 20

    def test_create_applies_rate_override_from_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Settings with API key should apply provider rate override."""
        from bioetl.composition.factories import http_client_factory as module

        http_config = HttpConfig(
            rate=3.0,
            capacity=6,
            rate_overrides={"pubmed_api_key": 12.0},
        )
        client_ctor = MagicMock(return_value="client-with-override")

        monkeypatch.setattr(module, "ensure_providers_loaded", lambda: None)
        monkeypatch.setattr(module.ProviderRegistry, "is_registered", lambda _: True)

        def _raise_missing_source_config(_: str):
            raise ValueError("missing source config")

        monkeypatch.setattr(module, "load_source_config", _raise_missing_source_config)
        monkeypatch.setattr(
            module.ProviderRegistry, "get_http_config", lambda _: http_config
        )
        monkeypatch.setattr(module, "UnifiedHTTPClient", client_ctor)

        settings = SimpleNamespace(pubmed_api_key="non-empty")
        result = HttpClientFactory.create_for_provider("pubmed", settings=settings)

        assert result == "client-with-override"
        kwargs = client_ctor.call_args.kwargs
        assert kwargs["timeout"] == 30.0
        assert kwargs["rate_limiter"].rate == 12.0
        assert kwargs["rate_limiter"].capacity == 24
        assert kwargs["retry_config"].max_attempts == 3
        assert kwargs["retry_config"].base_delay == 1.0
        assert kwargs["retry_config"].max_delay == 60.0

    def test_check_setting_truthy_and_missing(self) -> None:
        """_check_setting should return True only for truthy existing values."""
        settings = SimpleNamespace(pubmed_api_key="key", empty_value="", zero_value=0)

        assert HttpClientFactory._check_setting(settings, "pubmed_api_key") is True
        assert HttpClientFactory._check_setting(settings, "empty_value") is False
        assert HttpClientFactory._check_setting(settings, "zero_value") is False
        assert HttpClientFactory._check_setting(settings, "missing_attr") is False


@pytest.mark.unit
class TestResolvedHttpConfig:
    """Tests for _resolve_config — pure config resolution without infra objects."""

    def test_resolve_from_source_yaml(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Source YAML config should populate all ResolvedHttpConfig fields."""
        from bioetl.composition.factories import http_client_factory as module

        source_config = SimpleNamespace(
            rate_limit=SimpleNamespace(requests_per_second=7.5, burst=15),
            circuit_breaker=SimpleNamespace(failure_threshold=9, recovery_timeout=120),
            timeout_sec=42.0,
            max_retries=5,
            retry_base_delay=0.5,
            retry_max_delay=9.0,
            max_connections=100,
            max_keepalive_connections=20,
        )
        monkeypatch.setattr(module, "load_source_config", lambda _: source_config)
        monkeypatch.setattr(module.ProviderRegistry, "get_http_config", lambda _: None)

        cfg = HttpClientFactory._resolve_config("chembl", None)

        assert isinstance(cfg, ResolvedHttpConfig)
        assert cfg.rate == 7.5
        assert cfg.capacity == 15
        assert cfg.failure_threshold == 9
        assert cfg.recovery_timeout == 120
        assert cfg.timeout == 42.0
        assert cfg.max_retries == 5
        assert cfg.base_delay == 0.5
        assert cfg.max_delay == 9.0
        assert cfg.max_connections == 100
        assert cfg.max_keepalive == 20

    def test_resolve_fallback_to_registry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When source config missing, fall back to ProviderRegistry."""
        from bioetl.composition.factories import http_client_factory as module

        http_config = HttpConfig(rate=3.0, capacity=6)

        def _raise(_: str) -> None:
            raise ValueError("missing")

        monkeypatch.setattr(module, "load_source_config", _raise)
        monkeypatch.setattr(
            module.ProviderRegistry, "get_http_config", lambda _: http_config
        )

        cfg = HttpClientFactory._resolve_config("test_provider", None)

        assert cfg.rate == 3.0
        assert cfg.capacity == 6
        assert cfg.timeout == 30.0
        assert cfg.max_retries == 3
        assert cfg.base_delay == 1.0
        assert cfg.max_delay == 60.0

    def test_resolve_applies_rate_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """API key in settings should boost rate via rate_overrides."""
        from bioetl.composition.factories import http_client_factory as module

        http_config = HttpConfig(
            rate=3.0, capacity=6, rate_overrides={"pubmed_api_key": 12.0}
        )

        def _raise(_: str) -> None:
            raise ValueError("missing")

        monkeypatch.setattr(module, "load_source_config", _raise)
        monkeypatch.setattr(
            module.ProviderRegistry, "get_http_config", lambda _: http_config
        )

        settings = SimpleNamespace(pubmed_api_key="non-empty")
        cfg = HttpClientFactory._resolve_config("pubmed", settings)

        assert cfg.rate == 12.0
        assert cfg.capacity == 24

    def test_resolved_http_config_is_frozen(self) -> None:
        """ResolvedHttpConfig should be immutable."""
        cfg = ResolvedHttpConfig(
            rate=1.0,
            capacity=2,
            failure_threshold=3,
            recovery_timeout=60,
            timeout=30.0,
            max_retries=3,
            base_delay=1.0,
            max_delay=60.0,
            max_connections=50,
            max_keepalive=10,
        )
        with pytest.raises(AttributeError):
            cfg.rate = 99.0  # type: ignore[misc]
