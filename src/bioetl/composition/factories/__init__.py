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

_EXPORT_MAP: dict[str, tuple[str, str | None]] = {
    "BaseServicesFactory": (
        "bioetl.composition.factories.services.factory",
        "BaseServicesFactory",
    ),
    "DQServicesFactory": (
        "bioetl.composition.factories.dq.factory",
        "DQServicesFactory",
    ),
    "DataSourceCreatorProtocol": (
        "bioetl.composition.factories.datasource.data_source_factory",
        "DataSourceCreatorProtocol",
    ),
    "DataSourceFactory": (
        "bioetl.composition.factories.datasource.data_source_factory",
        "DataSourceFactory",
    ),
    "ServicesBuilder": (
        "bioetl.composition.factories.services.factory",
        "ServicesBuilder",
    ),
    "StorageBundle": (
        "bioetl.composition.factories.storage",
        "StorageBundle",
    ),
    "StorageContext": (
        "bioetl.composition.factories.storage",
        "StorageContext",
    ),
    "StorageFactory": (
        "bioetl.composition.factories.storage",
        "StorageFactory",
    ),
    "create_data_normalization_service": (
        "bioetl.composition.factories.services.factory",
        "create_data_normalization_service",
    ),
    "create_transformer": (
        "bioetl.composition.factories.transformer_factory",
        "create_transformer",
    ),
    "datasource": ("bioetl.composition.factories.datasource", None),
    "get_data_source_creator": (
        "bioetl.composition.factories.datasource.data_source_factory",
        "get_data_source_creator",
    ),
    "get_transformer_class": (
        "bioetl.composition.factories.transformer_factory",
        "get_transformer_class",
    ),
    "register_all_transformers": (
        "bioetl.composition.factories.transformer_factory",
        "register_all_transformers",
    ),
    "register_transformer": (
        "bioetl.composition.factories.transformer_factory",
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
