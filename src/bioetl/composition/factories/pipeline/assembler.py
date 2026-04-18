"""Thin RF-014 façade for pipeline factory assembly."""

from __future__ import annotations

from typing import TypeVar

from bioetl.application.core.wiring.factory import BasePipeline
from bioetl.composition.factories.datasource.data_source_factory import (
    get_data_source_creator as _rf014_get_data_source_creator,
)
from bioetl.composition.factories.dq.context_resolver import (
    extract_dq_configs as _rf014_extract_dq_configs,
)
from bioetl.composition.factories.pipeline._assembler_factory import (
    assemble_runner,
    GenericPipelineFactory as _GenericPipelineFactory,
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
TPipeline = TypeVar("TPipeline", bound=BasePipeline)


class GenericPipelineFactory(_GenericPipelineFactory[TPipeline]):
    def create_transformer(self, *args: object, **kwargs: object) -> object:
        return super().create_transformer(*args, **kwargs)


def create_pipeline_factory(*args: object, **kwargs: object) -> GenericPipelineFactory[object]:
    return GenericPipelineFactory(*args, **kwargs)

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
