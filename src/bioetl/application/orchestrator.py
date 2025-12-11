"""
Pipeline orchestration utilities for BioETL.

This module provides the main entry point for assembling and executing pipelines.
The orchestrator acts as a facade that hides the complexity of:
    - Provider registry resolution and lifecycle
    - Container assembly and dependency injection
    - Pipeline factory selection and instantiation
    - Subprocess execution for background runs

Architecture notes:
    - Orchestrator is stateless except for registry caching
    - Uses factory pattern for container and registry creation
    - Supports both synchronous and background (subprocess) execution
    - Registry can be injected directly or via lazy provider callback

Execution modes:
    FULL: Extract → Transform → Validate → Write (default)
    TRANSFORM_ONLY: Extract → Transform → Validate (dry_run=True)
    EXTRACT_ONLY: Extract only, returns record counts

Example::

    orchestrator = PipelineOrchestrator(
        "chembl_assay",
        config,
        provider_registry=registry,
    )
    result = orchestrator.run_pipeline(dry_run=False, limit=1000)
"""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from concurrent.futures import ProcessPoolExecutor

from bioetl.application.contracts import PipelineContainerABC
from bioetl.application.pipelines.base import PipelineBase
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
from bioetl.application.pipelines.registry import get_factory
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.pipelines.types import PipelineType
from bioetl.domain.provider_registry import (
    ProviderRegistryABC,
    ProviderRegistryLoaderABC,
)
from bioetl.domain.providers import ProviderDefinition, ProviderId
from bioetl.domain.value_objects import EntityName, StageName

ProviderLoaderProtocol = ProviderRegistryLoaderABC


class PipelineOrchestrator:
    """Manages pipeline assembly and execution."""

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
        """
        Create a pipeline instance by delegating to the appropriate factory.

        This method is the single entry point for pipeline creation. It:
        1. Resolves the provider registry
        2. Creates a dependency container
        3. Delegates pipeline creation to the registered factory

        Args:
            limit: Optional record limit for extraction.

        Returns:
            Fully configured pipeline ready to run.
        """
        factory = get_factory(self._pipeline_name)
        registry = self._get_provider_registry()
        container: PipelineContainerABC = self._container_factory(
            self._config,
            provider_registry=registry,
            provider_registry_provider=None,
        )

        return factory.create(container, limit=limit)

    def run_pipeline(
        self,
        *,
        dry_run: bool = False,
        limit: int | None = None,
        pipeline_type: PipelineType | None = None,
    ) -> RunResult:
        """
        Execute the pipeline synchronously in the current process.

        Args:
            dry_run: If True, skip the write stage (validate only).
            limit: Optional maximum number of records to process.
            pipeline_type: Override pipeline execution mode (FULL, TRANSFORM_ONLY, etc.).

        Returns:
            RunResult containing execution status, metrics, and metadata.
        """
        effective_type = pipeline_type or self._config.pipeline_type
        pipeline = self.build_pipeline(limit=limit)

        if effective_type == PipelineType.TRANSFORM_ONLY:
            # Execute transform and validate, skipping write
            return pipeline.run(
                output_path=Path(self._config.sink.output_path),
                dry_run=True,
                limit=limit,
            )

        if effective_type == PipelineType.EXTRACT_ONLY:
            # Extract only
            context = self._build_simple_context()
            extract_callable = pipeline._get_extract_callable()  # noqa: SLF001
            iterator = pipeline._normalize_extract_result(
                extract_callable()
            )  # noqa: SLF001

            total_rows = 0
            total_chunks = 0
            for chunk in iterator:
                if chunk is None:
                    continue
                total_rows += len(chunk)
                total_chunks += 1

            stage = StageResult(
                stage_name=StageName.EXTRACT,
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

        # FULL (default)
        return pipeline.run(
            output_path=Path(self._config.sink.output_path),
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
        """
        Execute the pipeline asynchronously in a separate process.

        Useful for long-running pipelines to avoid blocking the main thread.
        The pipeline configuration is serialized and executed in a subprocess.

        Args:
            dry_run: If True, skip the write stage.
            limit: Optional maximum number of records to process.
            executor: Optional ProcessPoolExecutor (creates one if not provided).

        Returns:
            Future that resolves to RunResult when pipeline completes.
        """
        from concurrent.futures import ProcessPoolExecutor

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
            entity_name=EntityName(self._config.entity_name),
            provider=ProviderId(self._config.provider),
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
        """Provider registry snapshot for subprocess transfer."""
        if self._provider_registry is None:
            return None
        return list(self._provider_registry.list_providers())

    def _load_registry_via_loader(self) -> ProviderRegistryABC | None:
        """Try to load registry via loader."""
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
        """Get registry via provider (fallback)."""
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
