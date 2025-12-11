"""Background pipeline execution service.

This service handles asynchronous pipeline execution in separate processes,
enabling non-blocking execution for long-running pipelines.
"""

from __future__ import annotations

from concurrent.futures import Future
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from concurrent.futures import ProcessPoolExecutor

    from bioetl.application.contracts import PipelineContainerABC
    from bioetl.domain.configs import PipelineConfig
    from bioetl.domain.models import RunResult
    from bioetl.domain.provider_registry import (
        ProviderRegistryFactory,
        ProviderRegistryLoaderABC,
    )
    from bioetl.domain.providers import ProviderDefinition


class BackgroundPipelineExecutor:
    """Executes pipelines asynchronously in separate processes.

    This service handles the complexity of:
    - Serializing configuration for subprocess transfer
    - Managing process pool executors
    - Reconstructing pipeline context in subprocess
    """

    @staticmethod
    def execute(
        *,
        pipeline_name: str,
        config: "PipelineConfig",
        registry_snapshot: "list[ProviderDefinition] | None",
        registry_factory: "ProviderRegistryFactory",
        provider_loader_factory: "Callable[[], ProviderRegistryLoaderABC] | None",
        container_factory: "Callable[..., PipelineContainerABC] | None",
        dry_run: bool = False,
        limit: int | None = None,
        executor: "ProcessPoolExecutor | None" = None,
    ) -> "Future[RunResult]":
        """Execute a pipeline in a background process.

        Args:
            pipeline_name: Name of the pipeline to execute.
            config: Pipeline configuration.
            registry_snapshot: Serialized provider definitions.
            registry_factory: Factory for creating provider registries.
            provider_loader_factory: Factory for creating provider loaders.
            container_factory: Factory for creating pipeline containers.
            dry_run: If True, skip the write stage.
            limit: Optional maximum number of records to process.
            executor: Optional ProcessPoolExecutor (creates one if not provided).

        Returns:
            Future that resolves to RunResult when pipeline completes.
        """
        from concurrent.futures import ProcessPoolExecutor

        executor_to_use = executor or ProcessPoolExecutor(max_workers=1)
        created_executor = executor is None

        future = executor_to_use.submit(
            BackgroundPipelineExecutor.run_in_subprocess,
            pipeline_name,
            config.model_dump(by_alias=False),
            dry_run,
            limit,
            provider_loader_factory,
            container_factory,
            registry_snapshot,
            registry_factory,
        )

        if created_executor:
            future.add_done_callback(lambda _: executor_to_use.shutdown(wait=False))

        return future

    @staticmethod
    def run_in_subprocess(
        pipeline_name: str,
        config_payload: dict,
        dry_run: bool,
        limit: int | None,
        provider_loader_factory: "Callable[[], ProviderRegistryLoaderABC] | None",
        container_factory: "Callable[..., PipelineContainerABC] | None",
        registry_payload: "list[ProviderDefinition] | None",
        registry_factory: "ProviderRegistryFactory",
    ) -> "RunResult":
        """Execute pipeline in subprocess context.

        This static method is the entry point for subprocess execution.
        It reconstructs all necessary dependencies from serialized data.
        """
        from bioetl.application.orchestrator import PipelineOrchestrator
        from bioetl.application.services.provider_registry_resolver import (
            ProviderRegistryResolver,
        )
        from bioetl.domain.configs import PipelineConfig

        config = PipelineConfig(**config_payload)
        loader = provider_loader_factory() if provider_loader_factory else None
        registry = ProviderRegistryResolver.build_for_subprocess(
            loader=loader,
            registry_payload=registry_payload,
            registry_factory=registry_factory,
        )

        orchestrator = PipelineOrchestrator(
            pipeline_name,
            config,
            provider_registry=registry,
            provider_registry_factory=registry_factory,
            provider_loader=loader,
            provider_loader_factory=provider_loader_factory,
            container_factory=container_factory,
        )

        return orchestrator.run_pipeline(
            dry_run=dry_run,
            limit=limit,
            pipeline_type=config.pipeline_type,
        )


__all__ = ["BackgroundPipelineExecutor"]
