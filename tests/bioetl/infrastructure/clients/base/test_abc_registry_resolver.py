import pytest

from bioetl.infrastructure.clients.base.abc_registry_resolver import (
    ABCRegistryResolver,
    ImplementationNotFoundError,
    RoleNotFoundError,
)
from bioetl.infrastructure.observability.factories import default_logging_port
from bioetl.infrastructure.output.impl.csv_writer import CsvWriterImpl


@pytest.fixture()
def registry_resolver() -> ABCRegistryResolver:
    return ABCRegistryResolver()


def test_resolve_default_factory(registry_resolver: ABCRegistryResolver) -> None:
    factory = registry_resolver.resolve_default_factory("LoggingPortABC")

    assert factory is default_logging_port


def test_resolve_implementation(registry_resolver: ABCRegistryResolver) -> None:
    implementation_class = registry_resolver.resolve_implementation("WriterABC", "Csv")

    assert implementation_class is CsvWriterImpl


def test_missing_role_raises(registry_resolver: ABCRegistryResolver) -> None:
    with pytest.raises(RoleNotFoundError):
        registry_resolver.resolve_default_factory("UnknownRole")


def test_missing_implementation_raises(registry_resolver: ABCRegistryResolver) -> None:
    with pytest.raises(ImplementationNotFoundError):
        registry_resolver.resolve_implementation("WriterABC", "UnknownImpl")
