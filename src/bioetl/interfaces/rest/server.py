"""Минимальный REST-сервер для запуска пайплайнов через PipelineOrchestrator."""

from __future__ import annotations

import asyncio
from functools import partial
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from bioetl.application.config.runtime import build_runtime_config
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.models import RunResult
from bioetl.domain.provider_registry import (
    ProviderRegistryABC,
    ProviderRegistryLoaderABC,
)
from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry
from bioetl.infrastructure.config.provider_registry import (
    create_provider_loader,
)
from bioetl.interfaces.container_factory import create_config_loader


class PipelineRunRequest(BaseModel):
    """Запрос на запуск пайплайна."""

    pipeline_name: str = Field(
        ..., description="Имя пайплайна в формате entity_provider"
    )
    profile: str = Field(
        default="default", description="Активный конфигурационный профиль"
    )
    dry_run: bool = Field(default=False, description="Запуск без записи вывода")
    limit: int | None = Field(
        default=None, description="Ограничение на количество записей"
    )


class PipelineRunResponse(BaseModel):
    """Ответ с результатами выполнения пайплайна."""

    run_id: str
    success: bool
    row_count: int
    duration_sec: float
    errors: list[str]


def _to_pipeline_id(pipeline_name: str) -> str:
    try:
        entity, provider = pipeline_name.rsplit("_", 1)
    except ValueError:
        entity = pipeline_name
        provider = "chembl"
    return f"{provider}.{entity}"


def _create_orchestrator(pipeline_name: str, profile: str) -> PipelineOrchestrator:
    pipeline_id = _to_pipeline_id(pipeline_name)
    config_loader = create_config_loader()
    config = build_runtime_config(
        pipeline_id=pipeline_id, profile=profile, loader=config_loader
    )
    if not config.features.rest_interface_enabled:
        raise HTTPException(
            status_code=503,
            detail="REST interface is disabled by configuration",
        )
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
    return PipelineOrchestrator(
        pipeline_name=pipeline_name,
        config=config,
        provider_registry=provider_registry,
        provider_loader=provider_loader,
        provider_loader_factory=provider_loader_factory,
    )


def _run_pipeline_sync(
    orchestrator: PipelineOrchestrator, dry_run: bool, limit: int | None
) -> RunResult:
    return orchestrator.run_pipeline(dry_run=dry_run, limit=limit)


def create_rest_app() -> FastAPI:
    """Создает и возвращает FastAPI-приложение для запуска пайплайнов."""

    app = FastAPI(title="BioETL REST Interface")

    @app.post("/pipelines/run", response_model=PipelineRunResponse)
    async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
        """Run a pipeline asynchronously and return execution result."""
        orchestrator = _create_orchestrator(
            pipeline_name=request.pipeline_name,
            profile=request.profile,
        )
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            _run_pipeline_sync,
            orchestrator,
            request.dry_run,
            request.limit,
        )
        return PipelineRunResponse(
            run_id=result.run_id,
            success=result.success,
            row_count=result.row_count,
            duration_sec=result.duration_sec,
            errors=result.errors,
        )

    return app


__all__ = ["create_rest_app", "PipelineRunRequest", "PipelineRunResponse"]
