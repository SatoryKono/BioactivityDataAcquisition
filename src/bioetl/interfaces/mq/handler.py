"""Обработчики MQ-заданий для запуска пайплайнов."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.models import RunResult
from bioetl.domain.provider_registry import InMemoryProviderRegistry
from bioetl.infrastructure.clients.provider_registry_loader import (
    load_provider_registry,
)


@dataclass
class MQJob:
    """Описание задания на запуск пайплайна из очереди."""

    pipeline_name: str
    profile: str = "default"
    dry_run: bool = False
    limit: int | None = None


def _to_pipeline_id(pipeline_name: str) -> str:
    try:
        entity, provider = pipeline_name.rsplit("_", 1)
    except ValueError:
        entity = pipeline_name
        provider = "chembl"
    return f"{provider}.{entity}"


class MQJobHandler:
    """Обрабатывает задания, инициируя запуск пайплайна."""

    def handle(self, job: MQJob) -> RunResult:
        pipeline_id = _to_pipeline_id(job.pipeline_name)
        config = build_runtime_config(pipeline_id=pipeline_id, profile=job.profile)
        if not config.features.mq_interface_enabled:
            raise RuntimeError("MQ interface is disabled by configuration")

        registry = load_provider_registry(registry=InMemoryProviderRegistry())
        orchestrator = PipelineOrchestrator(
            pipeline_name=job.pipeline_name,
            config=config,
            provider_registry=registry,
        )
        return orchestrator.run_pipeline(dry_run=job.dry_run, limit=job.limit)


__all__ = ["MQJob", "MQJobHandler"]
