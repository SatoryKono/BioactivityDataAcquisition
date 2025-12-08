"""Обработчики MQ-заданий для запуска пайплайнов."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.models import RunResult
from bioetl.domain.provider_registry import (
    InMemoryProviderRegistry,
    ProviderRegistryABC,
    ProviderRegistryLoaderABC,
)
from bioetl.infrastructure.clients.provider_registry_loader import (
    create_provider_loader,
)
from bioetl.interfaces.wiring import (
    create_config_loader,
    create_container_factory,
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
        """Execute pipeline run for a queued MQ job."""
        pipeline_id = _to_pipeline_id(job.pipeline_name)
        config_loader = create_config_loader()
        config = build_runtime_config(
            pipeline_id=pipeline_id, profile=job.profile, loader=config_loader
        )
        if not config.features.mq_interface_enabled:
            raise RuntimeError("MQ interface is disabled by configuration")

        providers_path = Path("configs") / "providers.yaml"
        provider_loader_factory: Callable[[], ProviderRegistryLoaderABC] | None = partial(
            create_provider_loader, config_path=providers_path
        )
        provider_loader: ProviderRegistryLoaderABC | None = None
        provider_registry: ProviderRegistryABC | None = None
        try:
            provider_loader = provider_loader_factory()
        except FileNotFoundError:
            provider_registry = InMemoryProviderRegistry()
            provider_loader_factory = None
        container_factory = create_container_factory()
        orchestrator = PipelineOrchestrator(
            pipeline_name=job.pipeline_name,
            config=config,
            provider_registry=provider_registry,
            provider_loader=provider_loader,
            provider_loader_factory=provider_loader_factory,
            container_factory=container_factory,
        )
        return orchestrator.run_pipeline(dry_run=job.dry_run, limit=job.limit)


__all__ = ["MQJob", "MQJobHandler"]
