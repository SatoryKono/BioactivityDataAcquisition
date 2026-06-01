"""Tests for ProviderRegistry.

Verifies provider registration, configuration lookup, and adapter creation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.composition.providers import (
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
    create_provider_registry,
    register_provider,
)
from bioetl.composition.providers._loading import (
    get_provider_registry_loaded_status,
    load_provider_registry,
)
from bioetl.composition.providers.provider_registry import (
    register_default_provider_config,
)
from bioetl.composition.providers.loader import (
    ensure_providers_loaded,
    get_loaded_status,
    load_providers,
    reset_loader,
)
from bioetl.domain.types import HealthStatus

pytestmark = pytest.mark.unit


@dataclass
class MockAdapter:
    """Mock adapter for testing."""

    http_client: Any = None
    logger: Any = None
    provider_name: str = "mock"

    async def fetch(self, *args, **kwargs):
        """Mock fetch."""
        yield {}

    async def health_check(self) -> HealthStatus:
        """Mock health check."""
        await asyncio.sleep(0)
        return HealthStatus.HEALTHY


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_create_basic_config(self):
        """Verify basic ProviderConfig creation."""
        config = ProviderConfig(adapter_class=MockAdapter)

        assert config.adapter_class is MockAdapter
        assert config.http_config is None
        assert config.requires_http_client is True
        assert config.requires_logger is True
        assert config.custom_creator is None
        assert config.default_kwargs == {}

    def test_create_config_with_http(self):
        """Verify ProviderConfig with HTTP configuration."""
        http_config = HttpConfig(rate=10.0, capacity=20)
        config = ProviderConfig(
            adapter_class=MockAdapter,
            http_config=http_config,
        )

        assert config.http_config is not None
        assert config.http_config.rate == pytest.approx(10.0)
        assert config.http_config.capacity == 20

    def test_config_is_frozen(self):
        """Verify ProviderConfig is immutable."""
        config = ProviderConfig(adapter_class=MockAdapter)

        with pytest.raises(AttributeError):
            config.adapter_class = object  # type: ignore


class TestHttpConfig:
    """Tests for HttpConfig dataclass."""

    def test_http_config_default_values(self):
        """Verify HttpConfig default values."""
        config = HttpConfig()

        assert config.rate == pytest.approx(5.0)
        assert config.capacity == 10
        assert config.rate_overrides == {}

    def test_http_config_accepts_custom_values(self):
        """Verify HttpConfig with custom values."""
        config = HttpConfig(
            rate=100.0,
            capacity=200,
            rate_overrides={"api_key": 150.0},
        )

        assert config.rate == pytest.approx(100.0)
        assert config.capacity == 200
        assert config.rate_overrides == {"api_key": 150.0}

    def test_config_is_frozen(self):
        """Verify HttpConfig is immutable."""
        config = HttpConfig()

        with pytest.raises(AttributeError):
            config.rate = 999.0  # type: ignore


class TestProviderRegistry:
    """Tests for ProviderRegistry class."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Reset registry before and after each test."""
        # Store original state (save a copy, may be empty if not loaded)
        original_providers = dict(ProviderRegistry._providers)
        # Clear for isolated test
        ProviderRegistry._providers.clear()

        yield

        # Restore original state
        ProviderRegistry._providers.clear()
        ProviderRegistry._providers.update(original_providers)

    def test_register_provider(self):
        """Verify provider registration."""
        config = ProviderConfig(adapter_class=MockAdapter)

        ProviderRegistry.register("test_provider", config)

        assert ProviderRegistry.is_registered("test_provider")
        assert ProviderRegistry.get("test_provider") is config

    def test_register_duplicate_overwrites(self):
        """Verify registering duplicate provider overwrites config."""
        config1 = ProviderConfig(adapter_class=MockAdapter)
        config2 = ProviderConfig(
            adapter_class=MockAdapter,
            http_config=HttpConfig(rate=99.0),
        )

        ProviderRegistry.register("duplicate_test", config1)
        ProviderRegistry.register("duplicate_test", config2)

        # Should have the second config
        result = ProviderRegistry.get("duplicate_test")
        assert result is config2
        assert result.http_config is not None
        assert result.http_config.rate == pytest.approx(99.0)

    def test_get_unknown_provider_raises(self):
        """Verify getting unknown provider raises KeyError."""
        with pytest.raises(KeyError, match="Unknown provider"):
            ProviderRegistry.get("nonexistent")

    def test_is_registered(self):
        """Verify is_registered method."""
        config = ProviderConfig(adapter_class=MockAdapter)
        ProviderRegistry.register("check_test", config)

        assert ProviderRegistry.is_registered("check_test") is True
        assert ProviderRegistry.is_registered("not_registered") is False

    def test_list_providers(self):
        """Verify list_providers returns sorted list."""
        ProviderRegistry.register(
            "beta_provider", ProviderConfig(adapter_class=MockAdapter)
        )
        ProviderRegistry.register(
            "alpha_provider", ProviderConfig(adapter_class=MockAdapter)
        )

        providers = ProviderRegistry.list_providers()

        # Should be sorted
        assert "alpha_provider" in providers
        assert "beta_provider" in providers
        assert providers.index("alpha_provider") < providers.index("beta_provider")

    def test_get_http_config(self):
        """Verify get_http_config method."""
        http_config = HttpConfig(rate=15.0, capacity=30)
        config = ProviderConfig(adapter_class=MockAdapter, http_config=http_config)
        ProviderRegistry.register("http_test", config)

        result = ProviderRegistry.get_http_config("http_test")

        assert result is not None
        assert result.rate == pytest.approx(15.0)
        assert result.capacity == 30

    def test_get_http_config_returns_none(self):
        """Verify get_http_config returns None when not configured."""
        config = ProviderConfig(adapter_class=MockAdapter, http_config=None)
        ProviderRegistry.register("no_http_test", config)

        result = ProviderRegistry.get_http_config("no_http_test")

        assert result is None

    def test_clear(self):
        """Verify clear method removes all providers."""
        ProviderRegistry.register(
            "clear_test", ProviderConfig(adapter_class=MockAdapter)
        )

        ProviderRegistry.clear()

        assert ProviderRegistry.list_providers() == []

    def test_register_default_provider_config_targets_lazy_singleton(self):
        """Named compatibility helper should register on the default singleton only."""
        isolated = create_provider_registry()
        config = ProviderConfig(
            adapter_class=MockAdapter,
            requires_http_client=False,
            requires_logger=False,
        )

        register_default_provider_config("default_seam_provider", config)

        assert ProviderRegistry.is_registered("default_seam_provider") is True
        assert ProviderRegistry.get("default_seam_provider") is config
        assert isolated.is_registered("default_seam_provider") is False

    def test_isolated_registry_keeps_state_local(self):
        """Instance-scoped registries must not leak writes into the default singleton."""
        isolated = create_provider_registry()
        config = ProviderConfig(
            adapter_class=MockAdapter,
            requires_http_client=False,
            requires_logger=False,
        )

        isolated.register("isolated_provider", config)

        assert isolated.is_registered("isolated_provider") is True
        assert isolated.get("isolated_provider") is config
        assert "isolated_provider" in isolated._providers
        assert "isolated_provider" not in ProviderRegistry._providers

    def test_injected_store_and_creator_are_used_by_instance_api(self):
        """Injected collaborators must power instance-scoped adapter creation."""
        from bioetl.composition.providers._store import ProviderStore

        sentinel_adapter = object()

        class StubCreator:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str]] = []

            def create_adapter(self, **kwargs: object) -> object:
                self.calls.append(("create_adapter", str(kwargs["name"])))
                return sentinel_adapter

            def create_data_source(self, **kwargs: object) -> object:
                self.calls.append(("create_data_source", str(kwargs["name"])))
                return object()

            def has_data_source_creator(self, config: ProviderConfig) -> bool:
                return config.data_source_creator is not None

            def require_data_source_creator(
                self,
                *,
                name: str,
                config: ProviderConfig,
            ) -> None:
                if config.data_source_creator is None:
                    raise KeyError(name)

            def build_bound_creator(self, *, name: str, create_data_source_fn):
                self.calls.append(("build_bound_creator", name))
                return create_data_source_fn

        store = ProviderStore(
            {
                "injected_provider": ProviderConfig(
                    adapter_class=MockAdapter,
                    requires_http_client=False,
                    requires_logger=False,
                )
            }
        )
        creator = StubCreator()
        isolated = ProviderRegistry(store=store, creator=creator)

        result = isolated.create_adapter("injected_provider")

        assert result is sentinel_adapter
        assert creator.calls == [("create_adapter", "injected_provider")]
        assert ProviderRegistry._providers == {}


class TestProviderRegistryAdapterCreation:
    """Tests for adapter creation through ProviderRegistry."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Reset registry before and after each test."""
        original_providers = dict(ProviderRegistry._providers)
        ProviderRegistry._providers.clear()

        yield

        ProviderRegistry._providers.clear()
        ProviderRegistry._providers.update(original_providers)

    def test_create_adapter_standard(self):
        """Verify standard adapter creation."""
        config = ProviderConfig(adapter_class=MockAdapter)
        ProviderRegistry.register("standard_test", config)

        mock_client = MagicMock()
        mock_logger = MagicMock()

        adapter = ProviderRegistry.create_adapter(
            "standard_test",
            http_client=mock_client,
            logger=mock_logger,
        )

        assert isinstance(adapter, MockAdapter)
        assert adapter.http_client is mock_client
        assert adapter.logger is mock_logger

    def test_create_adapter_without_http_client(self):
        """Verify adapter creation when http_client not required."""
        config = ProviderConfig(
            adapter_class=MockAdapter,
            requires_http_client=False,
        )
        ProviderRegistry.register("no_http_required", config)

        mock_logger = MagicMock()

        adapter = ProviderRegistry.create_adapter(
            "no_http_required",
            http_client=None,
            logger=mock_logger,
        )

        assert isinstance(adapter, MockAdapter)
        assert adapter.http_client is None
        assert adapter.logger is mock_logger

    def test_create_adapter_with_custom_creator(self):
        """Verify adapter creation with custom creator function."""
        custom_adapter = MagicMock()

        def custom_creator(**kwargs):
            return custom_adapter

        config = ProviderConfig(
            adapter_class=MockAdapter,
            custom_creator=custom_creator,
        )
        ProviderRegistry.register("custom_test", config)

        result = ProviderRegistry.create_adapter("custom_test")

        assert result is custom_adapter

    def test_create_adapter_with_default_kwargs(self):
        """Verify adapter creation with default kwargs."""

        @dataclass
        class AdapterWithDefaults:
            http_client: Any = None
            logger: Any = None
            batch_size: int = 100
            timeout: int = 30

        config = ProviderConfig(
            adapter_class=AdapterWithDefaults,
            default_kwargs={"batch_size": 500, "timeout": 60},
            requires_http_client=False,
            requires_logger=False,
        )
        ProviderRegistry.register("defaults_test", config)

        adapter = ProviderRegistry.create_adapter("defaults_test")

        assert adapter.batch_size == 500
        assert adapter.timeout == 60

    def test_create_adapter_kwargs_override_defaults(self):
        """Verify kwargs override default_kwargs."""

        @dataclass
        class AdapterWithDefaults:
            http_client: Any = None
            logger: Any = None
            batch_size: int = 100

        config = ProviderConfig(
            adapter_class=AdapterWithDefaults,
            default_kwargs={"batch_size": 500},
            requires_http_client=False,
            requires_logger=False,
        )
        ProviderRegistry.register("override_test", config)

        adapter = ProviderRegistry.create_adapter(
            "override_test",
            batch_size=1000,
        )

        assert adapter.batch_size == 1000

    def test_create_adapter_raises_when_logger_missing(self):
        """Verify ValueError raised when required logger is not provided."""
        config = ProviderConfig(
            adapter_class=MockAdapter,
            requires_http_client=False,
            requires_logger=True,
        )
        ProviderRegistry.register("logger_required_test", config)

        with pytest.raises(ValueError, match="requires logger"):
            ProviderRegistry.create_adapter("logger_required_test", logger=None)

    def test_create_adapter_raises_when_http_client_missing(self):
        """Verify ValueError raised when required http_client is not provided."""
        config = ProviderConfig(
            adapter_class=MockAdapter,
            requires_http_client=True,
            requires_logger=False,
        )
        ProviderRegistry.register("http_required_test", config)

        with pytest.raises(ValueError, match="requires http_client"):
            ProviderRegistry.create_adapter("http_required_test", http_client=None)


class TestProviderRegistryDataSourceCreator:
    """Tests for provider-bound data-source creator closures."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Reset registry before and after each test."""
        original_providers = dict(ProviderRegistry._providers)
        ProviderRegistry._providers.clear()

        yield

        ProviderRegistry._providers.clear()
        ProviderRegistry._providers.update(original_providers)

    def test_build_data_source_creator_delegates_to_registered_creator(self):
        """ProviderRegistry should return a provider-bound creator callback."""
        data_source = MagicMock()
        data_source_creator = MagicMock(return_value=data_source)
        ProviderRegistry.register(
            "creator_test",
            ProviderConfig(
                adapter_class=MockAdapter,
                data_source_creator=data_source_creator,
            ),
        )

        creator = ProviderRegistry.build_data_source_creator("creator_test")
        result = creator(
            settings=MagicMock(),
            pipeline_config=MagicMock(),
            logger=MagicMock(),
            filter_config=MagicMock(),
            metrics=MagicMock(),
            pipeline_name="creator_pipeline",
        )

        assert result is data_source
        data_source_creator.assert_called_once()

    def test_build_data_source_creator_raises_without_registered_creator(self):
        """Providers without a registered creator should fail clearly."""
        ProviderRegistry.register(
            "missing_creator",
            ProviderConfig(adapter_class=MockAdapter),
        )

        with pytest.raises(KeyError, match="does not have a data_source_creator"):
            ProviderRegistry.build_data_source_creator("missing_creator")


class TestRegisterProviderDecorator:
    """Tests for @register_provider decorator."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Reset registry before and after each test."""
        original_providers = dict(ProviderRegistry._providers)
        ProviderRegistry._providers.clear()

        yield

        ProviderRegistry._providers.clear()
        ProviderRegistry._providers.update(original_providers)

    def test_decorator_registers_class__test_register_provider_decorator_composition_providers_test_provider_registry_513(
        self,
    ):
        """Verify decorator registers the class."""

        @register_provider("decorator_test", http_rate=5.0)
        @dataclass
        class DecoratorTestAdapter:
            http_client: Any = None
            logger: Any = None

        assert ProviderRegistry.is_registered("decorator_test")
        config = ProviderRegistry.get("decorator_test")
        assert config.adapter_class is DecoratorTestAdapter

    def test_decorator_sets_http_config(self):
        """Verify decorator sets HTTP configuration."""

        @register_provider(
            "http_decorator_test",
            http_rate=25.0,
            http_capacity=50,
        )
        @dataclass
        class HttpDecoratorTestAdapter:
            http_client: Any = None
            logger: Any = None

        config = ProviderRegistry.get("http_decorator_test")
        assert config.http_config is not None
        assert config.http_config.rate == pytest.approx(25.0)
        assert config.http_config.capacity == 50

    def test_decorator_without_http_client(self):
        """Verify decorator with requires_http_client=False."""

        @register_provider(
            "no_http_decorator_test",
            requires_http_client=False,
        )
        @dataclass
        class NoHttpDecoratorTestAdapter:
            logger: Any = None

        config = ProviderRegistry.get("no_http_decorator_test")
        assert config.requires_http_client is False
        assert config.http_config is None

    def test_decorator_with_rate_overrides__test_register_provider_decorator_composition_providers_test_provider_registry_559(
        self,
    ):
        """Verify decorator with rate overrides."""

        @register_provider(
            "rate_override_test",
            http_rate=10.0,
            rate_overrides={"api_key": 100.0},
        )
        @dataclass
        class RateOverrideTestAdapter:
            http_client: Any = None
            logger: Any = None

        config = ProviderRegistry.get("rate_override_test")
        assert config.http_config is not None
        assert config.http_config.rate_overrides == {"api_key": 100.0}

    def test_decorator_sets_provider_name_attribute(self):
        """Verify decorator sets __provider_name__ on class."""

        @register_provider("name_attr_test")
        @dataclass
        class NameAttrTestAdapter:
            http_client: Any = None
            logger: Any = None

        assert hasattr(NameAttrTestAdapter, "__provider_name__")
        assert NameAttrTestAdapter.__provider_name__ == "name_attr_test"

    def test_decorator_returns_original_class(self):
        """Verify decorator returns the original class."""

        @register_provider("return_test")
        @dataclass
        class ReturnTestAdapter:
            http_client: Any = None
            logger: Any = None

        # Class should be usable normally
        adapter = ReturnTestAdapter(http_client=None, logger=None)
        assert isinstance(adapter, ReturnTestAdapter)


class TestProviderLoader:
    """Tests for provider loader functions."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Reset loader state before and after each test."""
        # Save original state
        original_providers = dict(ProviderRegistry._providers)
        reset_loader()

        yield

        # Restore original state
        reset_loader()
        ProviderRegistry._providers.update(original_providers)

    def test_load_providers_sets_loaded_status(self):
        """Verify load_providers sets loaded status."""
        assert get_loaded_status() is False

        load_providers()

        assert get_loaded_status() is True

    def test_load_providers_idempotent(self):
        """Verify load_providers is idempotent."""
        load_providers()
        load_providers()  # Should not raise

        assert get_loaded_status() is True

    def test_reset_loader(self):
        """Verify reset_loader resets state."""
        load_providers()
        assert get_loaded_status() is True

        reset_loader()

        assert get_loaded_status() is False

    def test_ensure_providers_loaded_recovers_after_registry_clear(self):
        """Ensure loader repopulates the default registry after it was cleared."""
        load_providers()
        assert get_loaded_status() is True

        ProviderRegistry.clear()
        assert get_loaded_status() is False

        ensure_providers_loaded()

        assert get_loaded_status() is True
        assert ProviderRegistry.list_providers()

    def test_custom_registry_loaded_status_tracks_registry_contents_without_global_flag(
        self,
    ) -> None:
        """Loader status for isolated registries should depend on actual contents."""
        registry = create_provider_registry()

        def _register(registrar) -> None:
            registrar.register("mock", ProviderConfig(adapter_class=MockAdapter))

        assert get_provider_registry_loaded_status(registry) is False

        load_provider_registry(registry, register_providers=_register)

        assert get_provider_registry_loaded_status(registry) is True

        registry.clear()

        assert get_provider_registry_loaded_status(registry) is False

    def test_loader_entrypoints_route_default_registry_through_private_helper(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Loader module should resolve the default registry through one helper path."""
        from bioetl.composition.providers import loader as module

        registry = create_provider_registry()
        captured: dict[str, object] = {}

        monkeypatch.setattr(module, "_get_loader_registry", lambda: registry)
        monkeypatch.setattr(
            module,
            "load_provider_registry",
            lambda candidate, *, force=False: captured.setdefault(
                "load", (candidate, force)
            ),
        )
        monkeypatch.setattr(
            module,
            "ensure_provider_registry_loaded",
            lambda candidate: captured.setdefault("ensure", candidate),
        )
        monkeypatch.setattr(
            module,
            "get_provider_registry_loaded_status",
            lambda candidate: captured.setdefault("status", candidate) is candidate,
        )
        monkeypatch.setattr(
            module,
            "reset_provider_registry_loader",
            lambda candidate: captured.setdefault("reset", candidate),
        )

        module.load_providers(force=True)
        module.ensure_providers_loaded()
        assert module.get_loaded_status() is True
        module.reset_loader()

        assert captured["load"] == (registry, True)
        assert captured["ensure"] is registry
        assert captured["status"] is registry
        assert captured["reset"] is registry

    def test_loader_registry_helper_uses_canonical_registry_resolution(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Loader helper should reuse the shared registry-resolution seam."""
        from bioetl.composition.providers import loader as module

        registry = create_provider_registry()
        captured: dict[str, object] = {}

        monkeypatch.setattr(
            module,
            "resolve_provider_registry",
            lambda candidate=None: (
                captured.setdefault("candidate", candidate) or registry
            ),
        )

        assert module._get_loader_registry() is registry
        assert captured["candidate"] is None


class TestRealProviderRegistration:
    """Integration tests for real provider registration."""

    @pytest.fixture(autouse=True)
    def ensure_loaded(self):
        """Ensure providers are loaded fresh."""
        # Reset loader state to allow reloading
        reset_loader()
        # Load providers fresh with force to reload modules
        load_providers(force=True)

    def test_chembl_is_registered(self):
        """Verify ChEMBL provider is registered with values from source config."""
        from bioetl.infrastructure.config.source_config_loader import load_source_config

        assert ProviderRegistry.is_registered("chembl")

        config = ProviderRegistry.get("chembl")
        assert config.http_config is not None

        # Rate should match configs/sources/chembl.yaml
        source_config = load_source_config("chembl")
        assert config.http_config.rate == source_config.rate_limit.requests_per_second

    def test_pubchem_is_registered(self):
        """Verify PubChem provider is registered."""
        assert ProviderRegistry.is_registered("pubchem")

        config = ProviderRegistry.get("pubchem")
        assert config.requires_http_client is False

    def test_uniprot_is_registered(self):
        """Verify UniProt provider is registered."""
        assert ProviderRegistry.is_registered("uniprot")

        config = ProviderRegistry.get("uniprot")
        assert config.http_config is not None
        assert "uniprot_api_key" in config.http_config.rate_overrides

    def test_pubmed_is_registered(self):
        """Verify PubMed provider is registered with values from source config."""
        from bioetl.infrastructure.config.source_config_loader import load_source_config

        assert ProviderRegistry.is_registered("pubmed")

        config = ProviderRegistry.get("pubmed")
        assert config.custom_creator is not None
        assert config.http_config is not None

        # Rate should match configs/sources/pubmed.yaml
        source_config = load_source_config("pubmed")
        assert config.http_config.rate == source_config.rate_limit.requests_per_second

    def test_crossref_is_registered(self):
        """Verify CrossRef provider is registered with values from source config."""
        from bioetl.infrastructure.config.source_config_loader import load_source_config

        assert ProviderRegistry.is_registered("crossref")

        config = ProviderRegistry.get("crossref")
        assert config.custom_creator is not None
        assert config.http_config is not None
        assert config.data_source_creator is not None

        # Rate should match configs/sources/crossref.yaml (50 req/sec for polite pool)
        source_config = load_source_config("crossref")
        assert config.http_config.rate == source_config.rate_limit.requests_per_second
        assert config.http_config.rate == pytest.approx(50.0)

    def test_all_providers_listed(self):
        """Verify all expected providers are listed."""
        providers = ProviderRegistry.list_providers()

        expected = ["chembl", "crossref", "pubchem", "pubmed", "uniprot"]
        for provider in expected:
            assert provider in providers, f"Missing provider: {provider}"
