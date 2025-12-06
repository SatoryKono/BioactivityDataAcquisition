import pytest

from bioetl.domain.provider_registry import (
    ProviderAlreadyRegisteredError,
    get_provider,
    list_providers,
    register_provider,
    reset_provider_registry,
    restore_provider_registry,
)
from bioetl.domain.providers import (
    BaseProviderConfig,
    ProviderComponents,
    ProviderDefinition,
    ProviderId,
)


class DummyProviderConfig(BaseProviderConfig):
    """Minimal config for testing."""


class DummyProviderComponents(
    ProviderComponents[object, object, object | None, object]
):
    """Stub implementations of provider component factories."""

    def create_client(self, config: BaseProviderConfig) -> object:
        return {"client_config": config}

    def create_extraction_service(
        self, config: BaseProviderConfig, *, client: object | None = None
    ) -> object:
        return {"extraction_config": config, "client": client}

    def create_normalization_service(
        self,
        config: BaseProviderConfig,
        *,
        client: object | None = None,
        pipeline_config: object | None = None,
    ) -> object | None:
        return {
            "normalization_config": config,
            "client": client,
            "pipeline_config": pipeline_config,
        }

    def create_writer(
        self, config: BaseProviderConfig, *, client: object | None = None
    ) -> object:
        return {"writer_config": config, "client": client}


@pytest.fixture(autouse=True)
def restore_registry_state() -> None:
    original_definitions = list_providers()
    yield
    restore_provider_registry(original_definitions)


@pytest.fixture
def dummy_provider_definition() -> ProviderDefinition:
    return ProviderDefinition(
        id=ProviderId.DUMMY,
        config_type=DummyProviderConfig,
        components=DummyProviderComponents(),
        description="dummy provider",
    )


@pytest.fixture
def chembl_provider_definition() -> ProviderDefinition:
    return ProviderDefinition(
        id=ProviderId.CHEMBL,
        config_type=DummyProviderConfig,
        components=DummyProviderComponents(),
        description="chembl provider",
    )


def test_register_and_get_provider(
    dummy_provider_definition: ProviderDefinition,
) -> None:
    reset_provider_registry()

    register_provider(dummy_provider_definition)

    assert get_provider(dummy_provider_definition.id) is dummy_provider_definition
    assert list_providers() == [dummy_provider_definition]


def test_register_provider_duplicate(
    dummy_provider_definition: ProviderDefinition,
) -> None:
    reset_provider_registry()
    register_provider(dummy_provider_definition)

    with pytest.raises(ProviderAlreadyRegisteredError):
        register_provider(dummy_provider_definition)


def test_reset_and_restore_provider_registry(
    dummy_provider_definition: ProviderDefinition,
    chembl_provider_definition: ProviderDefinition,
) -> None:
    definitions = [dummy_provider_definition, chembl_provider_definition]

    restore_provider_registry(definitions)
    assert list_providers() == definitions

    reset_provider_registry()
    assert list_providers() == []

    restore_provider_registry(definitions)
    assert list_providers() == definitions
