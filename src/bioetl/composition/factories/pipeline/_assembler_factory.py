"""Implementation module for GenericPipelineFactory."""

from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar, cast

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
from bioetl.composition.factories.pipeline.assembler_helpers import (
    build_factory_context,
    create_runner_from_factory,
    create_with_services_from_factory,
)
from bioetl.composition.factories.pipeline.factory_method_helpers import (
    _BuildFactoryServicesRequest,
    _CreateFactoryRunnerRequest,
    _CreatePipelineWithServicesRequest,
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
    LoggerPort,
    MetricsPort,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.ports.runtime.runner import (
    PipelineControlPlaneArtifacts,
    PipelineCreateRunnerRequest,
)
from bioetl.domain.services import IdentityService
from bioetl.domain.types import GoldSchemaType
from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

TPipeline = TypeVar("TPipeline", bound="BasePipeline")
_OPTIONAL_STRING_TYPE = "str | None"


def _public_assembler_seam(name: str) -> object:
    from bioetl.composition.factories.pipeline import assembler as public_assembler

    return getattr(public_assembler, name)


def _public_assembler_callable(name: str) -> Callable[..., object]:
    """Resolve a callable from the public assembler façade with explicit typing."""
    return cast(Callable[..., object], _public_assembler_seam(name))


def _optional_string_kwarg(kwargs: dict[str, object], key: str) -> str | None:
    """Return one optional string kwarg with explicit typing for runner shims."""
    return cast(_OPTIONAL_STRING_TYPE, kwargs.get(key))


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
            get_data_source_creator_fn=_public_assembler_seam(
                "get_data_source_creator"
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
                factory_context=build_factory_context(self),
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
                self,
                request=request,
                create_pipeline_instance_with_services_fn=_public_assembler_callable(
                    "create_pipeline_instance_with_services"
                ),
            ),
        )

    def create_runner(
        self,
        request: PipelineCreateRunnerRequest | None = None,
        **kwargs: object,
    ) -> PipelineRunner:
        if request is None:
            request = PipelineCreateRunnerRequest(
                run_id=kwargs["run_id"],
                runtime=kwargs["runtime"],
                started_at=cast("datetime", kwargs["started_at"]),
                settings=cast("Settings", kwargs["settings"]),
                observability=cast("ObservabilityBundle", kwargs["observability"]),
                control_plane=cast(
                    "PipelineControlPlaneArtifacts",
                    kwargs.get("control_plane"),
                ),
                filter_config=cast(
                    "InputFilterConfig | None",
                    kwargs.get("filter_config"),
                ),
                config=cast("PipelineYamlConfig | None", kwargs.get("config")),
                cached_bronze=kwargs.get("cached_bronze"),
            )
            if kwargs.get("control_plane") is None:
                request = PipelineCreateRunnerRequest(
                    run_id=request.run_id,
                    runtime=request.runtime,
                    started_at=request.started_at,
                    settings=request.settings,
                    observability=request.observability,
                    control_plane=PipelineControlPlaneArtifacts(
                        manifest_id=_optional_string_kwarg(kwargs, "manifest_id"),
                        execution_fingerprint=_optional_string_kwarg(
                            kwargs,
                            "execution_fingerprint",
                        ),
                        config_hash=_optional_string_kwarg(kwargs, "config_hash"),
                        resolved_config_hash=_optional_string_kwarg(
                            kwargs,
                            "resolved_config_hash",
                        ),
                        effective_config_hash=_optional_string_kwarg(
                            kwargs,
                            "effective_config_hash",
                        ),
                        dq_contract_compatibility_hash=_optional_string_kwarg(
                            kwargs,
                            "dq_contract_compatibility_hash",
                        ),
                        effective_config_artifact_id=_optional_string_kwarg(
                            kwargs,
                            "effective_config_artifact_id",
                        ),
                    ),
                    filter_config=request.filter_config,
                    config=request.config,
                    cached_bronze=request.cached_bronze,
                )
        return create_runner_from_factory(
            self,
            request=_CreateFactoryRunnerRequest(
                pipeline_name=self.pipeline_name,
                silver_schema=self.silver_schema,
                gold_schema=self.gold_schema,
                run_id=request.run_id,
                runtime=request.runtime,
                started_at=request.started_at,
                settings=cast("Settings", request.settings),
                observability=cast("ObservabilityBundle", request.observability),
                manifest_id=request.control_plane.manifest_id,
                execution_fingerprint=request.control_plane.execution_fingerprint,
                config_hash=request.control_plane.config_hash,
                resolved_config_hash=request.control_plane.resolved_config_hash,
                effective_config_hash=request.control_plane.effective_config_hash,
                dq_contract_compatibility_hash=(
                    request.control_plane.dq_contract_compatibility_hash
                ),
                effective_config_artifact_id=(
                    request.control_plane.effective_config_artifact_id
                ),
                filter_config=cast("InputFilterConfig | None", request.filter_config),
                config=cast("PipelineYamlConfig | None", request.config),
                cached_bronze=request.cached_bronze,
            ),
            assemble_runner_fn=_public_assembler_seam("assemble_runner"),
        )


__all__ = ["GenericPipelineFactory"]
