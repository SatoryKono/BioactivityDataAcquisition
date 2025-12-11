"""
Pipeline orchestration utilities for BioETL.

This module provides the main entry point for assembling and executing pipelines.
The orchestrator acts as a facade that coordinates:
    - ProviderRegistryResolver for registry lifecycle
    - BackgroundPipelineExecutor for subprocess execution
    - Pipeline factory selection and instantiation

Architecture notes:
    - Orchestrator delegates registry management to ProviderRegistryResolver
    - Orchestrator delegates background execution to BackgroundPipelineExecutor
    - Uses factory pattern for container creation
    - Supports both synchronous and background (subprocess) execution

Execution modes:
    FULL: Extract → Transform → Validate → Write (default)
    TRANSFORM_ONLY: Extract → Transform → Validate (dry_run=True)
    EXTRACT_ONLY: Extract only, returns record counts

Example::

    orchestrator = PipelineOrchestrator(
        "chembl_assay",
        config,
        provider_registry=registry,
        provider_registry_factory=factory,
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
from bioetl.application.pipelines.registry import get_factory
from bioetl.application.services.background_executor import BackgroundPipelineExecutor
from bioetl.application.services.provider_registry_resolver import (
    ProviderRegistryResolver,
)
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunContext, RunResult, StageResult
from bioetl.domain.pipelines.types import PipelineType
from bioetl.domain.provider_registry import (
    ProviderRegistryABC,
    ProviderRegistryFactory,
    ProviderRegistryLoaderABC,
)
from bioetl.domain.providers import ProviderId
from bioetl.domain.value_objects import EntityName, StageName

ProviderLoaderProtocol = ProviderRegistryLoaderABC


class PipelineOrchestrator:
    """Manages pipeline assembly and execution.

    This class is a thin facade that coordinates specialized services:
    - ProviderRegistryResolver: handles registry resolution and caching
    - BackgroundPipelineExecutor: handles subprocess execution

    Args:
        pipeline_name: Name of the pipeline to execute.
        config: Pipeline configuration.
        provider_registry: Optional pre-configured provider registry.
        provider_registry_provider: Callable that returns a provider registry.
        provider_registry_factory: Factory for creating provider registries.
            Required parameter - use create_provider_registry_factory()
            from bioetl.interfaces.factories.
        container_factory: Factory for creating pipeline containers.
        provider_loader: Loader for provider definitions.
        provider_loader_factory: Factory for creating provider loaders.

    Raises:
        ValueError: If provider_registry_factory is not provided.
    """

    def __init__(
        self,
        pipeline_name: str,
        config: PipelineConfig,
        *,
        provider_registry: ProviderRegistryABC | None = None,
        provider_registry_provider: Callable[[], ProviderRegistryABC] | None = None,
        provider_registry_factory: ProviderRegistryFactory,
        container_factory: Callable[..., PipelineContainerABC] | None = None,
        provider_loader: ProviderLoaderProtocol | None = None,
        provider_loader_factory: Callable[[], ProviderLoaderProtocol] | None = None,
    ) -> None:
        self._pipeline_name = pipeline_name
        self._config = config
        self._container_factory = self._resolve_container_factory(container_factory)

        # Delegate registry management to ProviderRegistryResolver
        self._registry_resolver = ProviderRegistryResolver(
            provider_registry=provider_registry,
            provider_registry_provider=provider_registry_provider,
            provider_registry_factory=provider_registry_factory,
            provider_loader=provider_loader,
            provider_loader_factory=provider_loader_factory,
        )

    def build_pipeline(self, *, limit: int | None = None) -> PipelineBase:
        """
        Create a pipeline instance by delegating to the appropriate factory.

        This method is the single entry point for pipeline creation. It:
        1. Resolves the provider registry via ProviderRegistryResolver
        2. Creates a dependency container
        3. Delegates pipeline creation to the registered factory

        Args:
            limit: Optional record limit for extraction.

        Returns:
            Fully configured pipeline ready to run.
        """
        factory = get_factory(self._pipeline_name)
        registry = self._registry_resolver.get_registry()
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
            pipeline_type: Override pipeline execution mode
                (FULL, TRANSFORM_ONLY, etc.).

        Returns:
            RunResult containing execution status, metrics, and metadata.
        """
        effective_type = pipeline_type or self._config.pipeline_type
        pipeline = self.build_pipeline(limit=limit)

        if effective_type == PipelineType.TRANSFORM_ONLY:
            return pipeline.run(
                output_path=Path(self._config.sink.output_path),
                dry_run=True,
                limit=limit,
            )

        if effective_type == PipelineType.EXTRACT_ONLY:
            return self._run_extract_only(pipeline, limit)

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

        Delegates to BackgroundPipelineExecutor for subprocess management.

        Args:
            dry_run: If True, skip the write stage.
            limit: Optional maximum number of records to process.
            executor: Optional ProcessPoolExecutor (creates one if not provided).

        Returns:
            Future that resolves to RunResult when pipeline completes.
        """
        return BackgroundPipelineExecutor.execute(
            pipeline_name=self._pipeline_name,
            config=self._config,
            registry_snapshot=self._registry_resolver.serialize_registry(),
            registry_factory=self._registry_resolver.registry_factory,
            provider_loader_factory=self._registry_resolver.provider_loader_factory,
            container_factory=self._container_factory,
            dry_run=dry_run,
            limit=limit,
            executor=executor,
        )

    def _run_extract_only(
        self, pipeline: PipelineBase, limit: int | None
    ) -> RunResult:
        """Execute extract-only mode."""
        context = self._build_simple_context()
        extract_result = pipeline.run_extract_only(limit=limit)

        stage = StageResult(
            stage_name=StageName.EXTRACT,
            success=True,
            records_processed=extract_result.total_rows,
            chunks_processed=extract_result.total_chunks,
            duration_sec=0.0,
            errors=[],
        )

        return RunResult(
            run_id=context.run_id,
            success=True,
            entity_name=self._config.entity_name,
            row_count=extract_result.total_rows,
            output_path=None,
            duration_sec=0.0,
            stages=[stage],
            errors=[],
            meta={
                "run_id": context.run_id,
                "provider": self._config.provider,
                "entity": self._config.entity_name,
                "row_count": extract_result.total_rows,
                "dry_run": True,
            },
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


__all__ = ["PipelineOrchestrator"]
