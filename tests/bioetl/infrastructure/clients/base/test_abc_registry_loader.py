import pytest

from bioetl.infrastructure.clients.base.abc_registry_loader import (
    ABCRegistryLoader,
    ImplementationNotFoundError,
    RoleNotFoundError,
)
from bioetl.infrastructure.observability.factories import default_logging_port
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl


@pytest.fixture()
def registry_loader() -> ABCRegistryLoader:
    return ABCRegistryLoader()


def test_resolve_default_factory(registry_loader: ABCRegistryLoader) -> None:
    factory = registry_loader.resolve_default_factory("LoggingPortABC")

    assert factory is default_logging_port


def test_resolve_implementation(registry_loader: ABCRegistryLoader) -> None:
    implementation_class = registry_loader.resolve_implementation("WriterABC", "Csv")

    assert implementation_class is CsvWriterImpl


def test_missing_role_raises(registry_loader: ABCRegistryLoader) -> None:
    with pytest.raises(RoleNotFoundError):
        registry_loader.resolve_default_factory("UnknownRole")


def test_missing_implementation_raises(registry_loader: ABCRegistryLoader) -> None:
    with pytest.raises(ImplementationNotFoundError):
        registry_loader.resolve_implementation("WriterABC", "UnknownImpl")
