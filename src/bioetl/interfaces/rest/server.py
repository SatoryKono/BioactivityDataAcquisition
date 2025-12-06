"""Минимальный REST-сервер для запуска пайплайнов через PipelineOrchestrator."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from bioetl.application.config_loader import load_pipeline_config
from bioetl.application.orchestrator import PipelineOrchestrator
from bioetl.domain.models import RunResult
from bioetl.infrastructure.clients.provider_registry_loader import (
    load_provider_registry,
)


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
    config = load_pipeline_config(pipeline_id, profile=profile)
    if not config.features.rest_interface_enabled:
        raise HTTPException(
            status_code=503,
            detail="REST interface is disabled by configuration",
        )
    registry = load_provider_registry()
    return PipelineOrchestrator(
        pipeline_name=pipeline_name,
        config=config,
        provider_registry=registry,
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
