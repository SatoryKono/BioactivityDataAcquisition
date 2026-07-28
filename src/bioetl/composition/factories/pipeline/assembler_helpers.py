"""Compatibility re-export; implementation lives in pipeline_support."""

from __future__ import annotations

from bioetl.composition.factories.pipeline_support.assembler_helpers import (
    _FactoryLike,
    build_factory_context,
    build_factory_services,
    create_pipeline_instance_with_services,
    create_runner_from_factory,
    create_with_services_from_factory,
    extract_entity_type,
)

__all__ = [
    "_FactoryLike",
    "build_factory_context",
    "build_factory_services",
    "create_pipeline_instance_with_services",
    "create_runner_from_factory",
    "create_with_services_from_factory",
    "extract_entity_type",
]
