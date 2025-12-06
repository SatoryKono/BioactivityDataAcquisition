from __future__ import annotations

from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path
from typing import Callable, cast

from bioetl.application.container import build_pipeline_dependencies
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.contracts import PipelineContainerABC
from bioetl.application.pipelines.registry import get_pipeline_class
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunResult
from bioetl.domain.provider_loader import ProviderLoaderProtocol
from bioetl.domain.provider_registry import (
    InMemoryProviderRegistry,
    ProviderRegistryABC,
)


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
        use_provider_loader_port: bool | None = None,
    ) -> None:
        self._pipeline_name = pipeline_name
        self._config = config
        self._provider_registry = provider_registry
        self._provider_registry_provider = provider_registry_provider
        self._container_factory = container_factory or build_pipeline_dependencies
        self._provider_loader = provider_loader
        self._provider_loader_factory = provider_loader_factory
        self._use_provider_loader_port = use_provider_loader_port or False

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
        extraction_service = container.get_extraction_service()
        normalization_service = container.get_normalization_service()
        record_source = container.get_record_source(
            extraction_service, limit=limit, logger=logger
        )
        hash_service = container.get_hash_service()
        hooks = container.get_hooks()
        error_policy = container.get_error_policy()

        pipeline_factory: Callable[..., PipelineBase] = cast(
            Callable[..., PipelineBase], pipeline_cls
        )
        pipeline: PipelineBase = pipeline_factory(
            config=self._config,
            logger=logger,
            validation_service=validation_service,
            output_writer=output_writer,
            extraction_service=extraction_service,
            record_source=record_source,
            normalization_service=normalization_service,
            hash_service=hash_service,
            hooks=hooks,
            error_policy=error_policy,
        )

        pipeline.set_post_transformer(
            container.get_post_transformer(version_provider=pipeline.get_version)
        )

        pipeline.add_hooks(hooks)
        pipeline.set_error_policy(error_policy)

        return pipeline

    def run_pipeline(
        self, *, dry_run: bool = False, limit: int | None = None
    ) -> RunResult:
        """Запускает пайплайн в текущем процессе."""
        pipeline = self.build_pipeline(limit=limit)
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
        future = executor_to_use.submit(
            self._execute_in_subprocess,
            self._pipeline_name,
            self._config.model_dump(),
            dry_run,
            limit,
            self._use_provider_loader_port,
            self._provider_loader_factory,
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
        use_provider_loader_port: bool,
        provider_loader_factory: Callable[[], ProviderLoaderProtocol] | None,
    ) -> RunResult:
        config = PipelineConfig(**config_payload)
        if provider_loader_factory is None:
            raise RuntimeError(
                "Provider loader factory is required for background runs"
            )
        loader = provider_loader_factory()
        registry = (
            loader.load_registry(registry=InMemoryProviderRegistry())
            if loader
            else InMemoryProviderRegistry()
        )
        orchestrator = PipelineOrchestrator(
            pipeline_name,
            config,
            provider_registry=registry,
            provider_loader=loader,
            provider_loader_factory=provider_loader_factory,
            use_provider_loader_port=use_provider_loader_port,
        )
        return orchestrator.run_pipeline(dry_run=dry_run, limit=limit)

    def _get_provider_registry(self) -> ProviderRegistryABC:
        if self._provider_registry is not None:
            return self._provider_registry

        registry = self._load_registry_via_loader()
        if registry is not None:
            return registry

        return self._resolve_registry_from_provider()

    def _load_registry_via_loader(self) -> ProviderRegistryABC | None:
        """Попытаться загрузить реестр через loader (если включён порт)."""
        if not self._use_provider_loader_port:
            return None

        loader = self._provider_loader
        if loader is None and self._provider_loader_factory is not None:
            loader = self._provider_loader_factory()
            self._provider_loader = loader

        if loader is None:
            return None

        self._provider_registry = loader.load_registry(
            registry=self._provider_registry
        )
        return self._provider_registry

    def _resolve_registry_from_provider(self) -> ProviderRegistryABC:
        """Получить реестр через provider (fallback)."""
        if self._provider_registry_provider is None:
            raise RuntimeError("Provider registry is not configured")

        registry = self._provider_registry_provider()
        if registry is None:
            raise RuntimeError("Provider registry provider returned None")

        self._provider_registry = registry
        return registry


__all__ = ["PipelineOrchestrator"]
