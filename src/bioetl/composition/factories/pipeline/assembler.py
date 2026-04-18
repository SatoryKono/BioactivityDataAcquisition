"""Thin RF-014 façade for pipeline factory assembly."""

from __future__ import annotations

from bioetl.composition.factories.datasource.data_source_factory import (
    get_data_source_creator as _rf014_get_data_source_creator,
)
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_configs as _rf014_extract_dq_configs,
)
from bioetl.composition.factories.pipeline._assembler_factory import (
    GenericPipelineFactory,
    assemble_runner,
    create_pipeline_factory,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    build_factory_services as _rf014_build_factory_services,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    create_pipeline_instance_with_services as _rf014_create_pipeline_instance_with_services,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    extract_entity_type as _rf014_extract_entity_type,
)
from bioetl.composition.factories.pipeline.runner_assembly import (
    assemble_runner_impl as _rf014_assemble_runner_impl,
)

get_data_source_creator = _rf014_get_data_source_creator
build_factory_services = _rf014_build_factory_services
create_pipeline_instance_with_services = (
    _rf014_create_pipeline_instance_with_services
)
_extract_entity_type = _rf014_extract_entity_type
_extract_dq_configs = _rf014_extract_dq_configs
_assemble_runner_impl = _rf014_assemble_runner_impl

_RF014_HELPER_OWNERS = (
    get_data_source_creator,
    _extract_dq_configs,
    build_factory_services,
    _assemble_runner_impl,
)

__all__ = [
    "GenericPipelineFactory",
    "_extract_entity_type",
    "assemble_runner",
    "create_pipeline_factory",
]
