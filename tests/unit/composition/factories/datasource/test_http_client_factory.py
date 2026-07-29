# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for HttpClientFactory."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.datasource.http_client import (
    HttpClientFactory,
    ResolvedHttpConfig,
)
from bioetl.composition.providers.provider_registry import (
    HttpConfig,
    ProviderConfig,
    create_provider_registry,
)


@pytest.mark.unit
class TestHttpClientFactory:
    """Tests for provider HTTP client construction."""

    def test_create_for_unknown_provider_raises_value_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Factory should fail fast for unknown providers."""
        from bioetl.composition.factories.datasource import http_client as module

        registry = MagicMock()
        registry.is_registered.return_value = False
        registry.list_providers.return_value = ["chembl", "pubmed"]
        monkeypatch.setattr(
            module,
            "_resolve_provider_registry",
            lambda provider_registry=None: registry,
        )

        with pytest.raises(ValueError, match="Unknown provider: unknown"):
            HttpClientFactory.create_for_provider("unknown")

    def test_create_uses_source_config_when_available(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Source YAML config should be primary source of HTTP settings."""
        from bioetl.composition.factories.datasource import http_client as module

        source_config = SimpleNamespace(
            rate_limit=SimpleNamespace(requests_per_second=7.5, burst=15),
            circuit_breaker=SimpleNamespace(failure_threshold=9, recovery_timeout=120),
            timeout_sec=42.0,
            max_retries=5,
            retry_base_delay=0.5,
            retry_max_delay=9.0,
            max_connections=100,
            max_keepalive_connections=20,
            trust_env=False,
        )
        client_ctor = MagicMock(return_value="client-from-source")
        registry = MagicMock()
        registry.is_registered.return_value = True
        registry.get_http_config.return_value = None

        monkeypatch.setattr(
            module,
            "_resolve_provider_registry",
            lambda provider_registry=None: registry,
        )
        monkeypatch.setattr(module, "load_source_config", lambda _: source_config)
        monkeypatch.setattr(module, "UnifiedHTTPClient", client_ctor)

        result = HttpClientFactory.create_for_provider("chembl")

        assert result == "client-from-source"
        kwargs = client_ctor.call_args.kwargs
        assert kwargs["timeout"] == pytest.approx(42.0)
        assert kwargs["provider"] == "chembl"
        assert kwargs["rate_limiter"].rate == pytest.approx(7.5)
        assert kwargs["rate_limiter"].capacity == 15
        assert kwargs["circuit_breaker"].failure_threshold == 9
        assert kwargs["circuit_breaker"].recovery_timeout == 120
        assert kwargs["retry_config"].max_attempts == 5
        assert kwargs["retry_config"].base_delay == pytest.approx(0.5)
        assert kwargs["retry_config"].max_delay == pytest.approx(9.0)
        assert kwargs["max_connections"] == 100
        assert kwargs["max_keepalive_connections"] == 20
        assert kwargs["trust_env"] is False

    def test_create_applies_rate_override_from_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Settings with API key should apply provider rate override."""
        from bioetl.composition.factories.datasource import http_client as module

        http_config = HttpConfig(
            rate=3.0,
            capacity=6,
            rate_overrides={"pubmed_api_key": 12.0},
        )
        client_ctor = MagicMock(return_value="client-with-override")
        registry = MagicMock()
        registry.is_registered.return_value = True
        registry.get_http_config.return_value = http_config

        monkeypatch.setattr(
            module,
            "_resolve_provider_registry",
            lambda provider_registry=None: registry,
        )

        def _raise_missing_source_config(_: str):
            raise ValueError("missing source config")

        monkeypatch.setattr(module, "load_source_config", _raise_missing_source_config)
        monkeypatch.setattr(module, "UnifiedHTTPClient", client_ctor)

        settings = SimpleNamespace(pubmed_api_key="non-empty")
        result = HttpClientFactory.create_for_provider("pubmed", settings=settings)

        assert result == "client-with-override"
        kwargs = client_ctor.call_args.kwargs
        assert kwargs["timeout"] == pytest.approx(30.0)
        assert kwargs["rate_limiter"].rate == pytest.approx(12.0)
        assert kwargs["rate_limiter"].capacity == 24
        assert kwargs["retry_config"].max_attempts == 3
        assert kwargs["retry_config"].base_delay == pytest.approx(1.0)
        assert kwargs["retry_config"].max_delay == pytest.approx(60.0)

    def test_create_clamps_retry_waits_in_test_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test mode should keep retries bounded and clamp request timeout."""
        from bioetl.composition.factories.datasource import http_client as module

        source_config = SimpleNamespace(
            rate_limit=SimpleNamespace(requests_per_second=7.5, burst=15),
            circuit_breaker=SimpleNamespace(failure_threshold=9, recovery_timeout=120),
            timeout_sec=42.0,
            max_retries=5,
            retry_base_delay=30.0,
            retry_max_delay=300.0,
            max_connections=100,
            max_keepalive_connections=20,
            trust_env=False,
        )
        client_ctor = MagicMock(return_value="client-test-mode")
        registry = MagicMock()
        registry.is_registered.return_value = True
        registry.get_http_config.return_value = None

        monkeypatch.setattr(
            module,
            "_resolve_provider_registry",
            lambda provider_registry=None: registry,
        )
        monkeypatch.setattr(module, "load_source_config", lambda _: source_config)
        monkeypatch.setattr(module, "UnifiedHTTPClient", client_ctor)

        settings = SimpleNamespace(test_mode=True)
        result = HttpClientFactory.create_for_provider(
            "semanticscholar",
            settings=settings,
        )

        assert result == "client-test-mode"
        assert client_ctor.call_args.kwargs["timeout"] == pytest.approx(5.0)
        retry_config = client_ctor.call_args.kwargs["retry_config"]
        assert retry_config.max_attempts == 5
        assert retry_config.base_delay == pytest.approx(0.0)
        assert retry_config.max_delay == pytest.approx(0.0)
        assert retry_config.max_retry_after_seconds == pytest.approx(0.0)

    def test_create_uses_explicit_provider_registry_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit registry should drive config lookup without default singleton use."""
        from bioetl.composition.factories.datasource import http_client as module

        isolated = create_provider_registry()
        isolated.register(
            "isolated_provider",
            ProviderConfig(
                adapter_class=MagicMock(),
                http_config=HttpConfig(rate=9.0, capacity=18),
                requires_http_client=False,
                requires_logger=False,
            ),
        )
        client_ctor = MagicMock(return_value="client-from-explicit-registry")

        def _raise_missing_source_config(_: str):
            raise ValueError("missing source config")

        monkeypatch.setattr(module, "load_source_config", _raise_missing_source_config)
        monkeypatch.setattr(module, "UnifiedHTTPClient", client_ctor)

        result = HttpClientFactory.create_for_provider(
            "isolated_provider",
            provider_registry=isolated,
        )

        assert result == "client-from-explicit-registry"
        kwargs = client_ctor.call_args.kwargs
        assert kwargs["provider"] == "isolated_provider"
        assert kwargs["rate_limiter"].rate == pytest.approx(9.0)
        assert kwargs["rate_limiter"].capacity == 18

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
        from bioetl.composition.factories.datasource import http_client as module

        source_config = SimpleNamespace(
            rate_limit=SimpleNamespace(requests_per_second=7.5, burst=15),
            circuit_breaker=SimpleNamespace(failure_threshold=9, recovery_timeout=120),
            timeout_sec=42.0,
            max_retries=5,
            retry_base_delay=0.5,
            retry_max_delay=9.0,
            max_connections=100,
            max_keepalive_connections=20,
            trust_env=False,
        )
        registry = MagicMock()
        registry.get_http_config.return_value = None
        monkeypatch.setattr(module, "load_source_config", lambda _: source_config)
        monkeypatch.setattr(
            module,
            "_resolve_provider_registry",
            lambda provider_registry=None: registry,
        )

        cfg = HttpClientFactory._resolve_config("chembl", None)

        assert isinstance(cfg, ResolvedHttpConfig)
        assert cfg.rate == pytest.approx(7.5)
        assert cfg.capacity == 15
        assert cfg.failure_threshold == 9
        assert cfg.recovery_timeout == 120
        assert cfg.timeout == pytest.approx(42.0)
        assert cfg.max_retries == 5
        assert cfg.base_delay == pytest.approx(0.5)
        assert cfg.max_delay == pytest.approx(9.0)
        assert cfg.max_connections == 100
        assert cfg.max_keepalive == 20
        assert cfg.trust_env is False

    def test_resolve_fallback_to_registry(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When source config missing, fall back to ProviderRegistry."""
        from bioetl.composition.factories.datasource import http_client as module

        http_config = HttpConfig(rate=3.0, capacity=6)
        registry = MagicMock()
        registry.get_http_config.return_value = http_config

        def _raise(_: str) -> None:
            raise ValueError("missing")

        monkeypatch.setattr(module, "load_source_config", _raise)
        monkeypatch.setattr(
            module,
            "_resolve_provider_registry",
            lambda provider_registry=None: registry,
        )

        cfg = HttpClientFactory._resolve_config("test_provider", None)

        assert cfg.rate == pytest.approx(3.0)
        assert cfg.capacity == 6
        assert cfg.timeout == pytest.approx(30.0)
        assert cfg.max_retries == 3
        assert cfg.base_delay == pytest.approx(1.0)
        assert cfg.max_delay == pytest.approx(60.0)
        assert cfg.trust_env is True

    def test_resolve_applies_rate_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """API key in settings should boost rate via rate_overrides."""
        from bioetl.composition.factories.datasource import http_client as module

        http_config = HttpConfig(
            rate=3.0, capacity=6, rate_overrides={"pubmed_api_key": 12.0}
        )
        registry = MagicMock()
        registry.get_http_config.return_value = http_config

        def _raise(_: str) -> None:
            raise ValueError("missing")

        monkeypatch.setattr(module, "load_source_config", _raise)
        monkeypatch.setattr(
            module,
            "_resolve_provider_registry",
            lambda provider_registry=None: registry,
        )

        settings = SimpleNamespace(pubmed_api_key="non-empty")
        cfg = HttpClientFactory._resolve_config("pubmed", settings)

        assert cfg.rate == pytest.approx(12.0)
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
            trust_env=True,
        )
        with pytest.raises(AttributeError):
            cfg.rate = 99.0  # type: ignore[misc]
