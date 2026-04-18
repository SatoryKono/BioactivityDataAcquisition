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
from bioetl.composition.factories.pipeline.runner_assembly import (
    assemble_runner_impl as _rf014_assemble_runner_impl,
)

_RF014_HELPER_OWNERS = (
    _rf014_get_data_source_creator,
    _rf014_extract_dq_configs,
    _rf014_build_factory_services,
    _rf014_assemble_runner_impl,
)

__all__ = ["GenericPipelineFactory", "assemble_runner", "create_pipeline_factory"]
