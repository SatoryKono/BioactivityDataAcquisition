# src/bioetl/composition/factories/__init__.py
"""Pipeline factories module.

Provides lazy access to composition factories without eagerly importing the
entire factory graph at package import time.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceCreatorProtocol,
        DataSourceFactory,
        get_data_source_creator,
    )
    from bioetl.composition.factories.dq.factory import DQServicesFactory
    from bioetl.composition.factories.services.factory import (
        BaseServicesFactory,
        ServicesBuilder,
        create_data_normalization_service,
    )
    from bioetl.composition.factories.storage import (
        StorageBundle,
        StorageContext,
        StorageFactory,
    )
    from bioetl.composition.factories.transformer_factory import (
        create_transformer,
        get_transformer_class,
        register_all_transformers,
        register_transformer,
    )

_DATASOURCE_MODULE = "bioetl.composition.factories.datasource"
_DATASOURCE_FACTORY_MODULE = (
    "bioetl.composition.factories.datasource.data_source_factory"
)
_DQ_FACTORY_MODULE = "bioetl.composition.factories.dq.factory"
_SERVICES_FACTORY_MODULE = "bioetl.composition.factories.services.factory"
_STORAGE_MODULE = "bioetl.composition.factories.storage"
_TRANSFORMER_FACTORY_MODULE = "bioetl.composition.factories.transformer_factory"

_EXPORT_MAP: dict[str, tuple[str, str | None]] = {
    "BaseServicesFactory": (
        _SERVICES_FACTORY_MODULE,
        "BaseServicesFactory",
    ),
    "DQServicesFactory": (
        _DQ_FACTORY_MODULE,
        "DQServicesFactory",
    ),
    "DataSourceCreatorProtocol": (
        _DATASOURCE_FACTORY_MODULE,
        "DataSourceCreatorProtocol",
    ),
    "DataSourceFactory": (
        _DATASOURCE_FACTORY_MODULE,
        "DataSourceFactory",
    ),
    "ServicesBuilder": (
        _SERVICES_FACTORY_MODULE,
        "ServicesBuilder",
    ),
    "StorageBundle": (
        _STORAGE_MODULE,
        "StorageBundle",
    ),
    "StorageContext": (
        _STORAGE_MODULE,
        "StorageContext",
    ),
    "StorageFactory": (
        _STORAGE_MODULE,
        "StorageFactory",
    ),
    "create_data_normalization_service": (
        _SERVICES_FACTORY_MODULE,
        "create_data_normalization_service",
    ),
    "create_transformer": (
        _TRANSFORMER_FACTORY_MODULE,
        "create_transformer",
    ),
    "datasource": (_DATASOURCE_MODULE, None),
    "get_data_source_creator": (
        _DATASOURCE_FACTORY_MODULE,
        "get_data_source_creator",
    ),
    "get_transformer_class": (
        _TRANSFORMER_FACTORY_MODULE,
        "get_transformer_class",
    ),
    "register_all_transformers": (
        _TRANSFORMER_FACTORY_MODULE,
        "register_all_transformers",
    ),
    "register_transformer": (
        _TRANSFORMER_FACTORY_MODULE,
        "register_transformer",
    ),
}

_PIPELINE_FACTORY_EXPORTS = frozenset(
    {
        "chembl_activity_factory",
        "pubchem_compound_factory",
        "pubmed_publication_factory",
        "uniprot_protein_factory",
    }
)

_PIPELINE_EXPORTS = frozenset(
    {
        "GenericPipelineFactory",
        "assemble_runner",
        "build_pipeline_services",
        "create_pipeline_factory",
    }
)


def __getattr__(name: str) -> object:
    export = _EXPORT_MAP.get(name)
    if export is not None:
        module_name, attr_name = export
        module = import_module(module_name)
        value = module if attr_name is None else getattr(module, attr_name)
        globals()[name] = value
        return value
    if name in _PIPELINE_EXPORTS:
        from bioetl.composition.factories import pipeline as _pipeline

        return getattr(_pipeline, name)
    if name in _PIPELINE_FACTORY_EXPORTS:
        from bioetl.composition.factories.pipeline import registry as _registry

        return getattr(_registry, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseServicesFactory",
    "DQServicesFactory",
    "DataSourceCreatorProtocol",
    "DataSourceFactory",
    "GenericPipelineFactory",
    "ServicesBuilder",
    "StorageBundle",
    "StorageContext",
    "StorageFactory",
    "assemble_runner",
    "build_pipeline_services",
    "chembl_activity_factory",
    "create_data_normalization_service",
    "create_pipeline_factory",
    "create_transformer",
    "datasource",
    "get_data_source_creator",
    "get_transformer_class",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_transformers",
    "register_transformer",
    "uniprot_protein_factory",
]
