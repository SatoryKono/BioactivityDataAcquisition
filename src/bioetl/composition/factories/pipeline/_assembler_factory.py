"""Implementation module for GenericPipelineFactory."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Generic, TypeVar, cast

import pyarrow as pa

from bioetl.application.core.wiring.factory import (
    BasePipeline,
    PipelineRunner,
    PipelineService,
)
from bioetl.application.core.wiring.transformer import (
    BaseTransformer,
    TransformerDependencyContext,
)
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    build_pipeline_create_runner_request_from_kwargs as _build_pipeline_create_runner_request_from_kwargs,
)
from bioetl.composition.factories.pipeline.assembler_helpers import (
    _FactoryLike,
    build_factory_context,
    create_runner_from_factory,
    create_with_services_from_factory,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    _BuildFactoryServicesRequest,
    _CreateFactoryRunnerRequest,
    _CreatePipelineWithServicesRequest,
    build_create_factory_runner_request,
    create_factory_data_source,
    create_transformer_instance,
    resolve_data_source_creator,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    extract_entity_type as _extract_entity_type,
)
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.domain.filtering import (
    GoldFilterConfig,
    InputFilterConfig,
    SilverFilterConfig,
)
from bioetl.domain.ports import (
    AuditPort,
    ContractPolicyPort,
    DataNormalizationPort,
    DataSourcePort,
    DQMonitorPort,
    ExecutionObservabilityPort,
    LoggerPort,
    MetricsPort,
    PiiHasherPort,
    PipelineCreateRunnerRequest,
    TracingPort,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldSchemaType
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.context import CachedBronzeContext
    from bioetl.domain.types import RunID

TPipeline = TypeVar("TPipeline", bound="BasePipeline")


def _public_assembler_seam(name: str) -> object:
    from bioetl.composition.factories.pipeline import assembler as public_assembler

    return getattr(public_assembler, name)


def _public_assembler_callable(name: str) -> Callable[..., object]:
    """Resolve a callable from the public assembler facade with explicit typing."""
    return cast(Callable[..., object], _public_assembler_seam(name))


def _optional_string_kwarg(kwargs: dict[str, object], key: str) -> str | None:
    """Return one optional string kwarg with explicit typing for runner shims."""
    return cast(str | None, kwargs.get(key))


class GenericPipelineFactory(Generic[TPipeline]):
    """Composition-layer factory for assembling pipelines and runners."""

    def __init__(
        self,
        pipeline_name: str,
        pipeline_class: type[TPipeline],
        provider: str,
        silver_schema: pa.Schema | None = None,
        gold_schema: GoldSchemaType | None = None,
        pandera_silver_schema: object | None = None,
        data_source_creator: DataSourceCreatorProtocol | None = None,
        transformer_class: type[BaseTransformer] | None = None,
        provider_registry: ProviderRegistry | None = None,
    ) -> None:
        if gold_schema is None:
            raise ValueError(
                f"gold_schema is required for pipeline '{pipeline_name}' "
                "to enforce Gold validation."
            )
        self.pipeline_name, self.pipeline_class, self.provider = (
            pipeline_name,
            pipeline_class,
            provider,
        )
        self.silver_schema, self.gold_schema, self.pandera_silver_schema = (
            silver_schema,
            gold_schema,
            pandera_silver_schema,
        )
        self.transformer_class, self.provider_registry = (
            transformer_class,
            provider_registry,
        )
        self._create_data_source = resolve_data_source_creator(
            provider=provider,
            provider_registry=provider_registry,
            data_source_creator=data_source_creator,
            get_data_source_creator_fn=cast(
                Callable[..., DataSourceCreatorProtocol],
                _public_assembler_seam("get_data_source_creator"),
            ),
        )

    def create_transformer(
        self,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
        contract_policy: ContractPolicyPort | None = None,
        dependencies: TransformerDependencyContext | None = None,
    ) -> BaseTransformer | None:
        return create_transformer_instance(
            transformer_class=self.transformer_class,
            provider=self.provider,
            pipeline_name=self.pipeline_name,
            extract_entity_type=_extract_entity_type,
            tracer=tracer,
            metrics=metrics,
            silver_filters=silver_filters,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
            dependencies=dependencies,
        )

    def create_data_source(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
    ) -> DataSourcePort:
        return create_factory_data_source(
            create_data_source_fn=self._create_data_source,
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            pipeline_name=self.pipeline_name,
            filter_config=filter_config,
        )

    def build_services(
        self,
        settings: Settings,
        logger: LoggerPort,
        audit: AuditPort | None = None,
        config: PipelineYamlConfig | None = None,
        filter_config: InputFilterConfig | None = None,
        tracer: TracingPort | None = None,
        dq_monitor: DQMonitorPort | None = None,
    ) -> PipelineService:
        return cast(
            PipelineService,
            _public_assembler_callable("build_factory_services")(
                factory_context=build_factory_context(cast(_FactoryLike, self)),
                request=_BuildFactoryServicesRequest(
                    settings,
                    logger,
                    audit,
                    config,
                    filter_config,
                    tracer,
                    dq_monitor,
                ),
            ),
        )

    def create_with_services(
        self,
        request: _CreatePipelineWithServicesRequest,
    ) -> TPipeline:
        return cast(
            TPipeline,
            create_with_services_from_factory(
                cast(_FactoryLike, self),
                request=request,
                create_pipeline_instance_with_services_fn=cast(
                    Callable[..., BasePipeline],
                    _public_assembler_callable(
                        "create_pipeline_instance_with_services"
                    ),
                ),
            ),
        )

    def create_runner(
        self,
        request: PipelineCreateRunnerRequest | None = None,
        **kwargs: object,
    ) -> PipelineRunner:
        if request is None:
            request = _build_pipeline_create_runner_request_from_kwargs(**kwargs)
        return create_runner_from_factory(
            cast(_FactoryLike, self),
            request=build_create_factory_runner_request(
                pipeline_name=self.pipeline_name,
                silver_schema=self.silver_schema,
                gold_schema=self.gold_schema,
                request=cast("PipelineCreateRunnerRequest", request),
            ),
            assemble_runner_fn=cast(
                Callable[..., PipelineRunner],
                _public_assembler_seam("assemble_runner"),
            ),
        )


__all__ = ["GenericPipelineFactory"]
