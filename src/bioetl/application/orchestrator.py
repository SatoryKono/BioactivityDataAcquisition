"""Pipeline orchestration utilities for BioETL."""

from __future__ import annotations

from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path
from typing import Callable, cast

from bioetl.application.pipelines.base import OutputWriterLoaderAdapter, PipelineBase
from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.application.pipelines.registry import get_pipeline_class
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.pipelines.types import PipelineType
from bioetl.domain.provider_registry import (
    InMemoryProviderRegistry,
    ProviderRegistryABC,
    ProviderRegistryLoaderABC,
)
from bioetl.domain.providers import ProviderDefinition

ProviderLoaderProtocol = ProviderRegistryLoaderABC


class PipelineOrchestrator:
    """Управляет сборкой и выполнением пайплайнов."""

    def __init__(
        self,
        pipeline_name: str,
        config: PipelineConfig,
        *,
        provider_registry: ProviderRegistryABC | None = None,
        provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
        container_factory: Callable[..., PipelineContainerABC] | None = None,
        provider_loader: ProviderLoaderProtocol | None = None,
        provider_loader_factory: Callable[[], ProviderLoaderProtocol] | None = None,
    ) -> None:
        self._pipeline_name = pipeline_name
        self._config = config
        self._provider_registry = provider_registry
        self._provider_registry_provider = provider_registry_provider
        self._container_factory = self._resolve_container_factory(container_factory)
        self._provider_loader = provider_loader
        self._provider_loader_factory = provider_loader_factory

    def build_pipeline(self, *, limit: int | None = None) -> PipelineBase:
        """Создает экземпляр пайплайна с зависимостями."""
        pipeline_cls = get_pipeline_class(self._pipeline_name)
        registry = self._get_provider_registry()
        container: PipelineContainerABC = self._container_factory(
            self._config,
            provider_registry=registry,
            provider_registry_provider=None,
        )

        logger = container.get_logger()
        validation_service = container.get_validation_service()
        output_writer = container.get_output_writer()
        loader = OutputWriterLoaderAdapter(output_writer)
        extraction_service = container.get_extraction_service()
        normalization_service = container.get_normalization_service()
        record_source = container.get_record_source(
            extraction_service, limit=limit, logger=logger
        )
        hash_service = container.get_hash_service()
        metadata_builder = container.get_metadata_builder()
        hooks = container.get_hooks()
        error_policy = container.get_error_policy()

        pipeline_factory: Callable[..., PipelineBase] = cast(
            Callable[..., PipelineBase], pipeline_cls
        )
        pipeline: PipelineBase = pipeline_factory(
            config=self._config,
            logger=logger,
            validation_service=validation_service,
            loader=loader,
            extraction_service=extraction_service,
            record_source=record_source,
            normalization_service=normalization_service,
            hash_service=hash_service,
            metadata_builder=metadata_builder,
            hooks=hooks,
            error_policy=error_policy,
        )

        pipeline.set_post_transformer(
            container.get_post_transformer(version_provider=pipeline.get_version)
        )

        pipeline.register_hooks(hooks)
        pipeline.set_error_policy(error_policy)

        return pipeline

    def run_pipeline(
        self,
        *,
        dry_run: bool = False,
        limit: int | None = None,
        pipeline_type: PipelineType | None = None,
    ) -> RunResult:
        """Запускает пайплайн в текущем процессе."""
        effective_type = pipeline_type or self._config.pipeline_type
        pipeline = self.build_pipeline(limit=limit)

        if effective_type == PipelineType.TRANSFORM_ONLY:
            # Выполнить трансформацию и валидацию, пропустив запись
            return pipeline.run(
                output_path=Path(self._config.output_path),
                dry_run=True,
                limit=limit,
            )

        if effective_type == PipelineType.EXTRACT_ONLY:
            # Только извлечение
            context = self._build_simple_context()
            extract_callable = pipeline._get_extract_callable()  # noqa: SLF001
            iterator = pipeline._normalize_extract_result(extract_callable())  # noqa: SLF001

            total_rows = 0
            total_chunks = 0
            for chunk in iterator:
                if chunk is None:
                    continue
                total_rows += len(chunk)
                total_chunks += 1

            stage = StageResult(
                stage_name="extract",
                success=True,
                records_processed=total_rows,
                chunks_processed=max(total_chunks, 1),
                duration_sec=0.0,
                errors=[],
            )

            return RunResult(
                run_id=context.run_id,
                success=True,
                entity_name=self._config.entity_name,
                row_count=total_rows,
                output_path=None,
                duration_sec=0.0,
                stages=[stage],
                errors=[],
                meta={
                    "run_id": context.run_id,
                    "provider": self._config.provider,
                    "entity": self._config.entity_name,
                    "row_count": total_rows,
                    "dry_run": True,
                },
            )

        # FULL (по умолчанию)
        return pipeline.run(
            output_path=Path(self._config.output_path),
            dry_run=dry_run,
            limit=limit,
        )

    def run_in_background(
        self,
        *,
        dry_run: bool = False,
        limit: int | None = None,
        executor: ProcessPoolExecutor | None = None,
    ) -> Future[RunResult]:
        """Запускает пайплайн в отдельном процессе."""
        executor_to_use = executor or ProcessPoolExecutor(max_workers=1)
        created_executor = executor is None
        registry_snapshot = self._serialize_provider_registry()
        future = executor_to_use.submit(
            self._execute_in_subprocess,
            self._pipeline_name,
            self._config.model_dump(by_alias=False),
            dry_run,
            limit,
            self._provider_loader_factory,
            self._container_factory,
            registry_snapshot,
        )

        if created_executor:
            future.add_done_callback(lambda _: executor_to_use.shutdown(wait=False))

        return future

    @staticmethod
    def _execute_in_subprocess(
        pipeline_name: str,
        config_payload: dict,
        dry_run: bool,
        limit: int | None,
        provider_loader_factory: Callable[[], ProviderLoaderProtocol] | None,
        container_factory: Callable[..., PipelineContainerABC] | None,
        registry_payload: list[ProviderDefinition] | None,
    ) -> RunResult:
        config = PipelineConfig(**config_payload)
        loader = provider_loader_factory() if provider_loader_factory else None
        registry = PipelineOrchestrator._build_registry_for_subprocess(
            loader=loader, registry_payload=registry_payload
        )
        orchestrator = PipelineOrchestrator(
            pipeline_name,
            config,
            provider_registry=registry,
            provider_loader=loader,
            provider_loader_factory=provider_loader_factory,
            container_factory=container_factory,
        )
        return orchestrator.run_pipeline(
            dry_run=dry_run,
            limit=limit,
            pipeline_type=config.pipeline_type,
        )

    def _build_simple_context(self) -> RunContext:
        return RunContext(
            entity_name=self._config.entity_name,
            provider=self._config.provider,
            config=self._config.model_dump(),
            dry_run=True,
        )

    @staticmethod
    def _resolve_container_factory(
        container_factory: Callable[..., PipelineContainerABC] | None,
    ) -> Callable[..., PipelineContainerABC]:
        if container_factory is not None:
            return container_factory

        from bioetl.application.container import create_default_container_factory

        return create_default_container_factory()

    def _get_provider_registry(self) -> ProviderRegistryABC:
        if self._provider_registry is not None:
            return self._provider_registry

        registry = self._load_registry_via_loader()
        if registry is not None:
            return registry

        return self._resolve_registry_from_provider()

    def _serialize_provider_registry(self) -> list[ProviderDefinition] | None:
        """Снимок реестра провайдеров для передачи в подпроцесс."""
        if self._provider_registry is None:
            return None
        return list(self._provider_registry.list_providers())

    def _load_registry_via_loader(self) -> ProviderRegistryABC | None:
        """Попытаться загрузить реестр через loader."""
        loader = self._provider_loader
        if loader is None and self._provider_loader_factory is not None:
            loader = self._provider_loader_factory()
            self._provider_loader = loader

        if loader is None:
            return None

        registry = loader.get_registry(registry=InMemoryProviderRegistry())
        self._provider_registry = registry
        return registry

    def _resolve_registry_from_provider(self) -> ProviderRegistryABC:
        """Получить реестр через provider (fallback)."""
        if self._provider_registry_provider is None:
            raise RuntimeError("Provider registry is not configured")

        registry = self._provider_registry_provider()
        if registry is None:
            raise RuntimeError("Provider registry provider returned None")

        self._provider_registry = registry
        return registry

    @staticmethod
    def _build_registry_for_subprocess(
        *,
        loader: ProviderLoaderProtocol | None,
        registry_payload: list[ProviderDefinition] | None,
    ) -> ProviderRegistryABC:
        if registry_payload is not None:
            registry = InMemoryProviderRegistry()
            registry.restore_provider_registry(registry_payload)
            return registry

        if loader is not None:
            return loader.get_registry(registry=InMemoryProviderRegistry())

        return InMemoryProviderRegistry()


__all__ = ["PipelineOrchestrator"]
