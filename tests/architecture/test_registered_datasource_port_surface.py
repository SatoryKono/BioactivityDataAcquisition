"""Contract surface for adapters registered through ``load_providers``.

The checks compare the declared provider slug, callable shape, and
``DataSourcePort.fetch`` parameter names. They do not call ``fetch``,
``health_check``, or ``aclose`` and are not behavioral conformance.
"""

from __future__ import annotations

import dataclasses
import importlib
import inspect
from collections.abc import Callable
from typing import Any

import pytest

from bioetl.domain.ports.data_source import DataSourcePort

pytestmark = pytest.mark.architecture

_FETCH_PARAMETERS = (
    "entity_type",
    "limit",
    "query",
    "filter_ids",
    "filter_field",
    "offset",
)

# provider slug, module, class, fetch shape.
# asyncgen: HTTP adapters declare ``async def fetch`` and yield records.
# iterator_return: ID mapping returns an async iterator from a sync function,
# matching the Protocol stub rather than an async-generator function.
_REGISTERED_ADAPTERS = (
    ("chembl", "bioetl.infrastructure.adapters.chembl", "ChemblAdapter", "asyncgen"),
    ("pubchem", "bioetl.infrastructure.adapters.pubchem", "PubChemAdapter", "asyncgen"),
    ("uniprot", "bioetl.infrastructure.adapters.uniprot", "UniProtAdapter", "asyncgen"),
    (
        "crossref",
        "bioetl.infrastructure.adapters.crossref",
        "CrossRefAdapter",
        "asyncgen",
    ),
    (
        "openalex",
        "bioetl.infrastructure.adapters.openalex",
        "OpenAlexAdapter",
        "asyncgen",
    ),
    ("pubmed", "bioetl.infrastructure.adapters.pubmed", "PubMedAdapter", "asyncgen"),
    (
        "semanticscholar",
        "bioetl.infrastructure.adapters.semanticscholar",
        "SemanticScholarAdapter",
        "asyncgen",
    ),
    (
        "uniprot_idmapping",
        "bioetl.application.core.data_sources.idmapping",
        "IDMappingDataSource",
        "iterator_return",
    ),
)


def _declared_provider_name(adapter_cls: type[Any]) -> str:
    if dataclasses.is_dataclass(adapter_cls):
        declared = {
            item.name: item.default
            for item in dataclasses.fields(adapter_cls)
            if item.name == "provider_name"
        }
        default = declared.get("provider_name", dataclasses.MISSING)
        if isinstance(default, str):
            return default
        raise AssertionError(
            f"{adapter_cls.__name__} provider_name default is not a string"
        )
    value = adapter_cls.__dict__.get("provider_name")
    if isinstance(value, str):
        return value
    raise AssertionError(f"{adapter_cls.__name__} provider_name is not a class string")


def _load(module_name: str, class_name: str) -> type[Any]:
    module = importlib.import_module(module_name)
    adapter_cls = getattr(module, class_name)
    if not isinstance(adapter_cls, type):
        raise AssertionError(f"{module_name}.{class_name} is not a class")
    return adapter_cls


def _parameters(method: Callable[..., Any]) -> list[str]:
    signature = inspect.signature(method)
    return [
        name
        for name, parameter in signature.parameters.items()
        if name not in {"self", "cls"}
        and parameter.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        }
    ]


@pytest.mark.parametrize(
    ("provider", "module_name", "class_name", "fetch_shape"),
    _REGISTERED_ADAPTERS,
    ids=[item[0] for item in _REGISTERED_ADAPTERS],
)
def test_registered_provider_exposes_datasource_port_surface(
    provider: str,
    module_name: str,
    class_name: str,
    fetch_shape: str,
) -> None:
    """Registered adapters expose the DataSourcePort callable surface."""
    adapter_cls = _load(module_name, class_name)
    assert _declared_provider_name(adapter_cls) == provider
    fetch = getattr(adapter_cls, "fetch", None)
    health_check = getattr(adapter_cls, "health_check", None)
    aclose = getattr(adapter_cls, "aclose", None)
    assert callable(fetch), f"{class_name}.fetch is missing"
    assert callable(health_check), f"{class_name}.health_check is missing"
    assert callable(aclose), f"{class_name}.aclose is missing"
    assert inspect.iscoroutinefunction(health_check)
    assert inspect.iscoroutinefunction(aclose)
    assert inspect.iscoroutinefunction(adapter_cls.__aenter__)
    assert inspect.iscoroutinefunction(adapter_cls.__aexit__)
    assert tuple(_parameters(fetch)) == _FETCH_PARAMETERS
    port_fetch = DataSourcePort.fetch
    assert tuple(_parameters(port_fetch)) == _FETCH_PARAMETERS
    if fetch_shape == "asyncgen":
        assert inspect.isasyncgenfunction(fetch), (
            f"{class_name}.fetch must be an async generator"
        )
        return
    assert fetch_shape == "iterator_return"
    assert not inspect.isasyncgenfunction(fetch)
    assert not inspect.iscoroutinefunction(fetch)
