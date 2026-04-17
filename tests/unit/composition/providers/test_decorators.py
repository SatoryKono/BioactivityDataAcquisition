"""Unit tests for provider decorator internals.

Tests _register_provider_class and register_provider decorator,
verifying HttpConfig construction, registry integration, and edge cases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import pytest

from bioetl.composition.providers.decorators import (
    _register_provider_class,
    register_provider,
)
from bioetl.composition.providers.provider_registry import (
    ProviderRegistry,
)


@pytest.fixture(autouse=True)
def _isolated_registry():
    """Reset ProviderRegistry before and after each test."""
    original = dict(ProviderRegistry._providers)
    ProviderRegistry._providers.clear()
    yield
    ProviderRegistry._providers.clear()
    ProviderRegistry._providers.update(original)


# ---------------------------------------------------------------------------
# Minimal fake adapters for DI in tests
# ---------------------------------------------------------------------------


@dataclass
class _FakeAdapter:
    http_client: Any = None
    logger: Any = None


def _create_fake_adapter() -> _FakeAdapter:
    """Return a fresh fake adapter instance for test stubs."""
    return _FakeAdapter()


# ---------------------------------------------------------------------------
# Tests for _register_provider_class
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisterProviderClass:
    """Tests for the internal _register_provider_class helper."""

    def test_registers_class_in_registry(self) -> None:
        """Should register the adapter class in ProviderRegistry."""
        _register_provider_class(
            cls=_FakeAdapter,
            name="fake_provider",
            http_rate=5.0,
            http_capacity=10,
            requires_http_client=True,
            requires_logger=True,
            rate_overrides=None,
            custom_creator=None,
            default_kwargs={},
        )

        assert ProviderRegistry.is_registered("fake_provider")

    def test_registers_via_named_default_registry_seam(self) -> None:
        """Registration should go through the named default-registry seam."""
        with patch(
            "bioetl.composition.providers.decorators.register_default_provider_config"
        ) as mock_register:
            _register_provider_class(
                cls=_FakeAdapter,
                name="seam_provider",
                http_rate=5.0,
                http_capacity=10,
                requires_http_client=False,
                requires_logger=False,
                rate_overrides=None,
                custom_creator=None,
                default_kwargs={"batch_size": 100},
            )

        mock_register.assert_called_once()
        name, config = mock_register.call_args.args
        assert name == "seam_provider"
        assert config.adapter_class is _FakeAdapter
        assert config.default_kwargs == {"batch_size": 100}
        assert config.http_config is None

    def test_creates_http_config_when_http_required(self) -> None:
        """Should create HttpConfig when requires_http_client is True."""
        _register_provider_class(
            cls=_FakeAdapter,
            name="http_provider",
            http_rate=20.0,
            http_capacity=40,
            requires_http_client=True,
            requires_logger=True,
            rate_overrides={"api_key": 50.0},
            custom_creator=None,
            default_kwargs={},
        )

        config = ProviderRegistry.get("http_provider")
        assert config.http_config is not None
        assert config.http_config.rate == pytest.approx(20.0)
        assert config.http_config.capacity == 40
        assert config.http_config.rate_overrides == {"api_key": 50.0}

    def test_no_http_config_when_http_not_required(self) -> None:
        """http_config should be None when requires_http_client is False."""
        _register_provider_class(
            cls=_FakeAdapter,
            name="no_http_provider",
            http_rate=5.0,
            http_capacity=10,
            requires_http_client=False,
            requires_logger=True,
            rate_overrides=None,
            custom_creator=None,
            default_kwargs={},
        )

        config = ProviderRegistry.get("no_http_provider")
        assert config.http_config is None

    def test_sets_provider_name_attribute_on_class(self) -> None:
        """Should set __provider_name__ on the adapter class."""

        @dataclass
        class _NamedAdapter:
            http_client: Any = None

        _register_provider_class(
            cls=_NamedAdapter,
            name="named_provider",
            http_rate=5.0,
            http_capacity=10,
            requires_http_client=False,
            requires_logger=False,
            rate_overrides=None,
            custom_creator=None,
            default_kwargs={},
        )

        assert hasattr(_NamedAdapter, "__provider_name__")
        assert _NamedAdapter.__provider_name__ == "named_provider"

    def test_stores_default_kwargs_in_config(self) -> None:
        """default_kwargs should be stored in ProviderConfig."""
        _register_provider_class(
            cls=_FakeAdapter,
            name="kwargs_provider",
            http_rate=5.0,
            http_capacity=10,
            requires_http_client=False,
            requires_logger=False,
            rate_overrides=None,
            custom_creator=None,
            default_kwargs={"batch_size": 100, "timeout": 30},
        )

        config = ProviderRegistry.get("kwargs_provider")
        assert config.default_kwargs == {"batch_size": 100, "timeout": 30}

    def test_stores_custom_creator_in_config(self) -> None:
        """custom_creator should be stored in ProviderConfig."""

        def custom(**_: Any) -> _FakeAdapter:
            return _create_fake_adapter()

        _register_provider_class(
            cls=_FakeAdapter,
            name="custom_creator_provider",
            http_rate=5.0,
            http_capacity=10,
            requires_http_client=True,
            requires_logger=True,
            rate_overrides=None,
            custom_creator=custom,
            default_kwargs={},
        )

        config = ProviderRegistry.get("custom_creator_provider")
        assert config.custom_creator is custom

    def test_empty_rate_overrides_stored_as_empty_dict(self) -> None:
        """rate_overrides=None should result in {} in HttpConfig."""
        _register_provider_class(
            cls=_FakeAdapter,
            name="no_overrides_provider",
            http_rate=5.0,
            http_capacity=10,
            requires_http_client=True,
            requires_logger=True,
            rate_overrides=None,
            custom_creator=None,
            default_kwargs={},
        )

        config = ProviderRegistry.get("no_overrides_provider")
        assert config.http_config is not None
        assert config.http_config.rate_overrides == {}


# ---------------------------------------------------------------------------
# Tests for register_provider decorator
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisterProviderDecorator:
    """Tests for the register_provider public decorator."""

    def test_decorator_registers_class(self) -> None:
        """@register_provider should register the decorated class."""

        @register_provider("decorated_provider", http_rate=5.0)
        @dataclass
        class _DecoratedAdapter:
            http_client: Any = None
            logger: Any = None

        assert ProviderRegistry.is_registered("decorated_provider")

    def test_decorator_returns_original_class_unchanged(self) -> None:
        """Decorator should return the exact same class object."""

        @dataclass
        class _OriginalAdapter:
            http_client: Any = None
            logger: Any = None

        decorated = register_provider("original_provider")(_OriginalAdapter)

        assert decorated is _OriginalAdapter

    def test_decorator_sets_default_http_rate(self) -> None:
        """Default http_rate should be 5.0."""

        @register_provider("default_rate_provider")
        @dataclass
        class _DefaultRateAdapter:
            http_client: Any = None
            logger: Any = None

        config = ProviderRegistry.get("default_rate_provider")
        assert config.http_config is not None
        assert config.http_config.rate == pytest.approx(5.0)

    def test_decorator_sets_custom_http_rate(self) -> None:
        """Custom http_rate should override the default."""

        @register_provider("custom_rate_provider", http_rate=25.0, http_capacity=50)
        @dataclass
        class _CustomRateAdapter:
            http_client: Any = None
            logger: Any = None

        config = ProviderRegistry.get("custom_rate_provider")
        assert config.http_config is not None
        assert config.http_config.rate == pytest.approx(25.0)
        assert config.http_config.capacity == 50

    def test_decorator_with_requires_http_client_false(self) -> None:
        """requires_http_client=False should set http_config to None."""

        @register_provider("no_http_provider", requires_http_client=False)
        @dataclass
        class _NoHttpAdapter:
            logger: Any = None

        config = ProviderRegistry.get("no_http_provider")
        assert config.requires_http_client is False
        assert config.http_config is None

    def test_decorator_with_rate_overrides(self) -> None:
        """rate_overrides should be stored in http_config."""

        @register_provider(
            "override_provider",
            http_rate=10.0,
            rate_overrides={"pubmed_api_key": 100.0},
        )
        @dataclass
        class _OverrideAdapter:
            http_client: Any = None
            logger: Any = None

        config = ProviderRegistry.get("override_provider")
        assert config.http_config is not None
        assert config.http_config.rate_overrides == {"pubmed_api_key": 100.0}

    def test_decorator_with_default_kwargs(self) -> None:
        """Extra kwargs passed to @register_provider become default_kwargs."""

        @register_provider("kwargs_decorator_provider", batch_size=500, timeout=60)
        @dataclass
        class _KwargsDecoratorAdapter:
            http_client: Any = None
            logger: Any = None

        config = ProviderRegistry.get("kwargs_decorator_provider")
        assert config.default_kwargs == {"batch_size": 500, "timeout": 60}

    def test_decorator_with_custom_creator(self) -> None:
        """custom_creator kwarg should be stored in config."""

        def custom_creator(**_: Any) -> _FakeAdapter:
            return _create_fake_adapter()

        @register_provider("custom_creator_decorated", custom_creator=custom_creator)
        @dataclass
        class _CustomCreatorAdapter:
            http_client: Any = None
            logger: Any = None

        config = ProviderRegistry.get("custom_creator_decorated")
        assert config.custom_creator is custom_creator

    def test_decorator_sets_provider_name_on_class(self) -> None:
        """__provider_name__ attribute should be set on decorated class."""

        @register_provider("name_attr_provider")
        @dataclass
        class _NameAttrAdapter:
            http_client: Any = None
            logger: Any = None

        assert _NameAttrAdapter.__provider_name__ == "name_attr_provider"  # type: ignore[attr-defined]

    def test_decorated_class_still_instantiable(self) -> None:
        """Decorated class should still be instantiable as normal."""

        @register_provider("instantiable_provider")
        @dataclass
        class _InstantiableAdapter:
            http_client: Any = None
            logger: Any = None

        adapter = _InstantiableAdapter(http_client=None, logger=None)
        assert isinstance(adapter, _InstantiableAdapter)

    def test_decorator_with_requires_logger_false(self) -> None:
        """requires_logger=False should be stored in config."""

        @register_provider("no_logger_provider", requires_logger=False)
        @dataclass
        class _NoLoggerAdapter:
            http_client: Any = None

        config = ProviderRegistry.get("no_logger_provider")
        assert config.requires_logger is False
