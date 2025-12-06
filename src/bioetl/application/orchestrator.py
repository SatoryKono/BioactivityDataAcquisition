from __future__ import annotations

from concurrent.futures import Future, ProcessPoolExecutor
from pathlib import Path
from typing import Callable

from prometheus_client import start_http_server

from bioetl.application.config.pipeline_config_schema import PipelineConfig
from bioetl.application.container import PipelineContainer, build_pipeline_dependencies
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.registry import get_pipeline_class
from bioetl.domain.models import RunResult


class PipelineOrchestrator:
    """Управляет сборкой и выполнением пайплайнов."""

    def __init__(
        self,
        pipeline_name: str,
        config: PipelineConfig,
        container_factory: Callable[[PipelineConfig], PipelineContainer] | None = None,
    ) -> None:
        self._pipeline_name = pipeline_name
        self._config = config
        self._container_factory = container_factory or build_pipeline_dependencies

    def build_pipeline(self, *, limit: int | None = None) -> PipelineBase:
        """Создает экземпляр пайплайна с зависимостями."""
        pipeline_cls = get_pipeline_class(self._pipeline_name)
        container = self._container_factory(self._config)

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

        pipeline = pipeline_cls(
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
        start_http_server(9108, addr="0.0.0.0")
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
    ) -> RunResult:
        config = PipelineConfig(**config_payload)
        orchestrator = PipelineOrchestrator(pipeline_name, config)
        return orchestrator.run_pipeline(dry_run=dry_run, limit=limit)


__all__ = ["PipelineOrchestrator"]
