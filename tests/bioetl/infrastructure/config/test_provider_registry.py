"""Unit tests for the unified provider registry module."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Callable

import pytest
import yaml

from bioetl.domain.configs import (
    DummyProviderConfig,
    HttpClientConfig,
    ProviderHttpConfig,
)
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.infrastructure.config.provider_registry import (
    DEFAULT_PROVIDERS_REGISTRY_PATH,
    ProviderLoaderImpl,
    ProviderNotConfiguredError,
    ProviderRegistryConfig,
    ProviderRegistryEntryModel,
    ProviderRegistryError,
    ProviderRegistryFormatError,
    ProviderRegistryNotFoundError,
    clear_provider_registry_cache,
    create_provider_loader,
    create_provider_registry,
    create_provider_registry_loader,
    ensure_provider_known,
)

# ---------------------------------------------------------------------------
# Test Fixtures and Helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DummyComponents(ProviderComponents):
    """Test provider components."""

    def create_client(self, config: DummyProviderConfig) -> dict[str, str]:
        return {"provider": config.provider}

    def create_extraction_service(
        self, config: DummyProviderConfig, *, client: dict[str, str] | None = None
    ) -> tuple[dict[str, str], str]:
        resolved_client = client or self.create_client(config)
        return resolved_client, config.provider


class RecordingLogger(LoggingPortABC):
    """Logger that records all log calls for testing."""

    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, Any]]] = []

    def info(self, msg: str, **ctx: Any) -> None:
        self.records.append(("info", msg, ctx))

    def error(self, msg: str, **ctx: Any) -> None:
        self.records.append(("error", msg, ctx))

    def debug(self, msg: str, **ctx: Any) -> None:
        self.records.append(("debug", msg, ctx))

    def warning(self, msg: str, **ctx: Any) -> None:
        self.records.append(("warning", msg, ctx))

    def apply_bind(self, **ctx: Any) -> RecordingLogger:
        self.records.append(("bind", "", ctx))
        return self

    @property
    def errors(self) -> list[tuple[str, str, dict[str, Any]]]:
        return [record for record in self.records if record[0] == "error"]

    @property
    def debugs(self) -> list[tuple[str, str, dict[str, Any]]]:
        return [record for record in self.records if record[0] == "debug"]


@pytest.fixture
def provider_definition_factory() -> Callable[[ProviderId], ProviderDefinition]:
    """Factory fixture for creating test provider definitions."""

    def _factory(provider_id: ProviderId) -> ProviderDefinition:
        return ProviderDefinition(
            id=provider_id,
            config_type=DummyProviderConfig,
            components=DummyComponents(),
            description="Test provider",
        )

    return _factory


@pytest.fixture
def recording_logger() -> RecordingLogger:
    """Fixture for recording logger."""
    return RecordingLogger()


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    """Clear registry cache before and after each test."""
    clear_provider_registry_cache()
    yield
    clear_provider_registry_cache()


def _register_module(
    module_name: str, factory_name: str, factory: Callable[..., Any]
) -> None:
    """Register a synthetic module with a factory function."""
    module = ModuleType(module_name)
    setattr(module, factory_name, factory)
    sys.modules[module_name] = module


def _unregister_module(module_name: str) -> None:
    """Remove a synthetic module from sys.modules."""
    sys.modules.pop(module_name, None)


# ---------------------------------------------------------------------------
# Tests: Exceptions
# ---------------------------------------------------------------------------


class TestProviderRegistryExceptions:
    """Tests for exception classes."""

    def test_provider_registry_not_found_error(self) -> None:
        path = Path("/nonexistent/providers.yaml")
        error = ProviderRegistryNotFoundError(path)
        assert error.registry_path == path
        assert error.path == path  # Alias
        assert "not found" in str(error).lower()

    def test_provider_registry_format_error(self) -> None:
        path = Path("/test/providers.yaml")
        error = ProviderRegistryFormatError(path, "invalid schema")
        assert error.registry_path == path
        assert error.path == path  # Alias
        assert "invalid schema" in str(error)

    def test_provider_not_configured_error(self) -> None:
        path = Path("/test/providers.yaml")
        error = ProviderNotConfiguredError("unknown_provider", path)
        assert error.provider == "unknown_provider"
        assert error.registry_path == path
        assert "unknown_provider" in str(error)

    def test_exception_inheritance(self) -> None:
        assert issubclass(ProviderRegistryNotFoundError, ProviderRegistryError)
        assert issubclass(ProviderRegistryFormatError, ProviderRegistryError)
        assert issubclass(ProviderNotConfiguredError, ProviderRegistryError)


# ---------------------------------------------------------------------------
# Tests: Pydantic Models
# ---------------------------------------------------------------------------


class TestProviderRegistryModels:
    """Tests for Pydantic models."""

    def test_entry_model_with_string_id(self) -> None:
        entry = ProviderRegistryEntryModel(
            id="chembl",
            module="bioetl.infrastructure.clients.chembl.provider",
            factory="register_chembl_provider",
        )
        assert entry.id == "chembl"
        assert entry.active is True
        assert entry.description is None
        assert entry.http_client is None

    def test_entry_model_with_provider_id_enum(self) -> None:
        entry = ProviderRegistryEntryModel(
            id=ProviderId.CHEMBL,
            module="bioetl.infrastructure.clients.chembl.provider",
            factory="register_chembl_provider",
            active=False,
            description="ChEMBL provider",
        )
        assert entry.id == ProviderId.CHEMBL
        assert entry.active is False
        assert entry.description == "ChEMBL provider"

    def test_entry_model_with_http_client(self) -> None:
        """Test entry model with HTTP config (legacy http_client field name)."""
        http_config = ProviderHttpConfig(
            base_url="https://api.example.com", timeout_sec=60.0, max_retries=5
        )
        entry = ProviderRegistryEntryModel(
            id="custom",
            module="custom.module",
            factory="create_provider",
            http=http_config,
        )
        assert entry.http is not None
        assert entry.http.timeout_sec == 60.0
        assert entry.http.max_retries == 5
        # Legacy property still works
        assert entry.http_client is entry.http

    def test_registry_config_model(self) -> None:
        config = ProviderRegistryConfig(
            providers=[
                ProviderRegistryEntryModel(
                    id="chembl",
                    module="bioetl.infrastructure.clients.chembl.provider",
                    factory="register_chembl_provider",
                ),
                ProviderRegistryEntryModel(
                    id="pubchem",
                    module="bioetl.infrastructure.clients.pubchem.provider",
                    factory="register_pubchem_provider",
                    active=False,
                ),
            ]
        )
        assert len(config.providers) == 2
        assert config.providers[0].id == "chembl"
        assert config.providers[1].active is False

    def test_registry_config_empty_providers(self) -> None:
        config = ProviderRegistryConfig()
        assert config.providers == []


# ---------------------------------------------------------------------------
# Tests: ensure_provider_known
# ---------------------------------------------------------------------------


class TestEnsureProviderKnown:
    """Tests for ensure_provider_known function."""

    def test_known_provider_returns_id(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "providers": [
                        {
                            "id": "chembl",
                            "module": "test.module",
                            "factory": "create",
                            "active": True,
                        }
                    ]
                }
            )
        )

        result = ensure_provider_known("chembl", registry_path=config_file)
        assert result == "chembl"

    def test_unknown_provider_raises_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "providers": [
                        {
                            "id": "chembl",
                            "module": "test.module",
                            "factory": "create",
                            "active": True,
                        }
                    ]
                }
            )
        )

        with pytest.raises(ProviderNotConfiguredError) as exc_info:
            ensure_provider_known("unknown", registry_path=config_file)
        assert exc_info.value.provider == "unknown"

    def test_inactive_provider_not_found(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "providers": [
                        {
                            "id": "chembl",
                            "module": "test.module",
                            "factory": "create",
                            "active": False,
                        }
                    ]
                }
            )
        )

        with pytest.raises(ProviderNotConfiguredError):
            ensure_provider_known("chembl", registry_path=config_file)

    def test_missing_registry_file_raises_error(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nonexistent.yaml"

        with pytest.raises(ProviderRegistryNotFoundError) as exc_info:
            ensure_provider_known("chembl", registry_path=nonexistent)
        assert exc_info.value.registry_path == nonexistent

    def test_invalid_registry_format_raises_error(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(
            yaml.dump({"providers": [{"invalid": "schema"}]})  # Missing required fields
        )

        with pytest.raises(ProviderRegistryFormatError):
            ensure_provider_known("chembl", registry_path=config_file)


# ---------------------------------------------------------------------------
# Tests: ProviderLoaderImpl
# ---------------------------------------------------------------------------


class TestProviderLoaderImpl:
    """Tests for ProviderLoaderImpl class."""

    def test_loader_raises_on_missing_config(
        self, tmp_path: Path, recording_logger: RecordingLogger
    ) -> None:
        nonexistent = tmp_path / "nonexistent.yaml"
        loader = ProviderLoaderImpl(config_path=nonexistent, logger=recording_logger)

        with pytest.raises(ProviderRegistryNotFoundError):
            loader.get_providers()

    def test_loader_raises_on_invalid_config(
        self, tmp_path: Path, recording_logger: RecordingLogger
    ) -> None:
        config_file = tmp_path / "providers.yaml"
        # Write valid YAML but invalid schema (missing required fields)
        config_file.write_text(
            yaml.dump(
                {
                    "providers": [
                        {
                            "invalid_field": "value"
                        }  # Missing required id, module, factory
                    ]
                }
            )
        )
        loader = ProviderLoaderImpl(config_path=config_file, logger=recording_logger)

        with pytest.raises(ProviderRegistryFormatError):
            loader.get_providers()

    def test_loader_skips_disabled_entries(
        self,
        tmp_path: Path,
        recording_logger: RecordingLogger,
        provider_definition_factory: Callable[[ProviderId], ProviderDefinition],
    ) -> None:
        # Register test module
        def factory(http: HttpClientConfig | None = None) -> ProviderDefinition:
            return provider_definition_factory(ProviderId.DUMMY)

        _register_module("test_module_disabled", "create_provider", factory)

        try:
            config_file = tmp_path / "providers.yaml"
            config_file.write_text(
                yaml.dump(
                    {
                        "providers": [
                            {
                                "id": "dummy",
                                "module": "test_module_disabled",
                                "factory": "create_provider",
                                "active": False,
                            }
                        ]
                    }
                )
            )

            loader = ProviderLoaderImpl(
                config_path=config_file, logger=recording_logger
            )
            providers = loader.get_providers()

            # Should fallback to ChEMBL since no active providers
            assert len(providers) == 1
            assert providers[0].id == ProviderId.CHEMBL

            # Should have logged debug message about disabled entry
            debug_msgs = [r[1] for r in recording_logger.debugs]
            assert any("disabled" in msg.lower() for msg in debug_msgs)
        finally:
            _unregister_module("test_module_disabled")

    def test_loader_handles_module_import_error(
        self, tmp_path: Path, recording_logger: RecordingLogger
    ) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "providers": [
                        {
                            "id": "dummy",
                            "module": "nonexistent.module",
                            "factory": "create_provider",
                            "active": True,
                        }
                    ]
                }
            )
        )

        loader = ProviderLoaderImpl(config_path=config_file, logger=recording_logger)
        providers = loader.get_providers()

        # Should fallback to ChEMBL
        assert len(providers) == 1
        assert providers[0].id == ProviderId.CHEMBL

        # Should have logged error about import failure
        error_msgs = [r[1] for r in recording_logger.errors]
        assert any("import" in msg.lower() for msg in error_msgs)

    def test_loader_handles_missing_factory(
        self, tmp_path: Path, recording_logger: RecordingLogger
    ) -> None:
        # Register test module without factory
        _register_module("test_module_no_factory", "other_function", lambda: None)

        try:
            config_file = tmp_path / "providers.yaml"
            config_file.write_text(
                yaml.dump(
                    {
                        "providers": [
                            {
                                "id": "dummy",
                                "module": "test_module_no_factory",
                                "factory": "create_provider",
                                "active": True,
                            }
                        ]
                    }
                )
            )

            loader = ProviderLoaderImpl(
                config_path=config_file, logger=recording_logger
            )
            providers = loader.get_providers()

            # Should fallback to ChEMBL
            assert len(providers) == 1
            assert providers[0].id == ProviderId.CHEMBL

            # Should have logged error about missing factory
            error_msgs = [r[1] for r in recording_logger.errors]
            assert any("not found" in msg.lower() for msg in error_msgs)
        finally:
            _unregister_module("test_module_no_factory")

    def test_loader_handles_factory_returning_wrong_type(
        self, tmp_path: Path, recording_logger: RecordingLogger
    ) -> None:
        # Register test module with factory returning wrong type
        def wrong_factory(
            http: HttpClientConfig | None = None,
        ) -> dict[str, str]:
            return {"not": "a provider"}

        _register_module("test_module_wrong_type", "create_provider", wrong_factory)

        try:
            config_file = tmp_path / "providers.yaml"
            config_file.write_text(
                yaml.dump(
                    {
                        "providers": [
                            {
                                "id": "dummy",
                                "module": "test_module_wrong_type",
                                "factory": "create_provider",
                                "active": True,
                            }
                        ]
                    }
                )
            )

            loader = ProviderLoaderImpl(
                config_path=config_file, logger=recording_logger
            )
            providers = loader.get_providers()

            # Should fallback to ChEMBL
            assert len(providers) == 1
            assert providers[0].id == ProviderId.CHEMBL

            # Should have logged error about unexpected type
            error_msgs = [r[1] for r in recording_logger.errors]
            assert any("unexpected type" in msg.lower() for msg in error_msgs)
        finally:
            _unregister_module("test_module_wrong_type")

    def test_loader_registers_provider_successfully(
        self,
        tmp_path: Path,
        recording_logger: RecordingLogger,
        provider_definition_factory: Callable[[ProviderId], ProviderDefinition],
    ) -> None:
        # Register test module with valid factory
        def valid_factory(
            http: HttpClientConfig | None = None,
        ) -> ProviderDefinition:
            return provider_definition_factory(ProviderId.DUMMY)

        _register_module("test_module_valid", "create_provider", valid_factory)

        try:
            config_file = tmp_path / "providers.yaml"
            config_file.write_text(
                yaml.dump(
                    {
                        "providers": [
                            {
                                "id": "dummy",
                                "module": "test_module_valid",
                                "factory": "create_provider",
                                "active": True,
                            }
                        ]
                    }
                )
            )

            loader = ProviderLoaderImpl(
                config_path=config_file, logger=recording_logger
            )
            providers = loader.get_providers()

            assert len(providers) == 1
            assert providers[0].id == ProviderId.DUMMY
        finally:
            _unregister_module("test_module_valid")

    def test_get_registry_returns_populated_registry(
        self,
        tmp_path: Path,
        recording_logger: RecordingLogger,
        provider_definition_factory: Callable[[ProviderId], ProviderDefinition],
    ) -> None:
        def valid_factory(
            http: HttpClientConfig | None = None,
        ) -> ProviderDefinition:
            return provider_definition_factory(ProviderId.DUMMY)

        _register_module("test_module_registry", "create_provider", valid_factory)

        try:
            config_file = tmp_path / "providers.yaml"
            config_file.write_text(
                yaml.dump(
                    {
                        "providers": [
                            {
                                "id": "dummy",
                                "module": "test_module_registry",
                                "factory": "create_provider",
                                "active": True,
                            }
                        ]
                    }
                )
            )

            loader = ProviderLoaderImpl(
                config_path=config_file, logger=recording_logger
            )
            registry = loader.get_registry()

            assert registry is not None
            provider = registry.get_provider(ProviderId.DUMMY)
            assert provider.id == ProviderId.DUMMY
        finally:
            _unregister_module("test_module_registry")

    def test_load_method_is_alias_for_get_providers(
        self, tmp_path: Path, recording_logger: RecordingLogger
    ) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump({"providers": []}))

        loader = ProviderLoaderImpl(config_path=config_file, logger=recording_logger)

        providers_via_get = loader.get_providers()
        providers_via_load = loader.load()

        # Both should return ChEMBL fallback
        assert len(providers_via_get) == len(providers_via_load) == 1
        assert providers_via_get[0].id == providers_via_load[0].id == ProviderId.CHEMBL


# ---------------------------------------------------------------------------
# Tests: Factory Functions
# ---------------------------------------------------------------------------


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_provider_loader(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump({"providers": []}))

        loader = create_provider_loader(config_path=config_file)

        assert isinstance(loader, ProviderLoaderImpl)

    def test_default_provider_registry_loader(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump({"providers": []}))

        loader = create_provider_registry_loader(config_path=config_file)

        assert isinstance(loader, ProviderLoaderImpl)

    def test_get_provider_registry_function(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(yaml.dump({"providers": []}))

        registry = create_provider_registry(config_path=config_file)

        assert registry is not None
        # Should have ChEMBL fallback
        provider = registry.get_provider(ProviderId.CHEMBL)
        assert provider.id == ProviderId.CHEMBL


# ---------------------------------------------------------------------------
# Tests: Cache
# ---------------------------------------------------------------------------


class TestRegistryCache:
    """Tests for registry caching behavior."""

    def test_clear_cache_function(self, tmp_path: Path) -> None:
        config_file = tmp_path / "providers.yaml"
        config_file.write_text(
            yaml.dump(
                {
                    "providers": [
                        {
                            "id": "chembl",
                            "module": "test.module",
                            "factory": "create",
                            "active": True,
                        }
                    ]
                }
            )
        )

        # First call caches the result
        result1 = ensure_provider_known("chembl", registry_path=config_file)
        assert result1 == "chembl"

        # Modify file
        config_file.write_text(
            yaml.dump(
                {
                    "providers": [
                        {
                            "id": "pubchem",
                            "module": "test.module",
                            "factory": "create",
                            "active": True,
                        }
                    ]
                }
            )
        )

        # Without clearing cache, should still find chembl (cached)
        result2 = ensure_provider_known("chembl", registry_path=config_file)
        assert result2 == "chembl"

        # After clearing cache, should not find chembl
        clear_provider_registry_cache()
        with pytest.raises(ProviderNotConfiguredError):
            ensure_provider_known("chembl", registry_path=config_file)


# ---------------------------------------------------------------------------
# Tests: Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Tests for module constants."""

    def test_default_paths(self) -> None:
        assert DEFAULT_PROVIDERS_REGISTRY_PATH == Path("configs/providers.yaml")


