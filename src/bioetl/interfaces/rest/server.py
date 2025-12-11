"""Минимальный REST-сервер для запуска пайплайнов через RunPipelineUseCase."""

from __future__ import annotations

import asyncio

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from bioetl.application.use_cases import (
    InterfaceDisabledError,
    RunPipelineRequest,
)
from bioetl.interfaces.use_case_factory import get_use_case_factory


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


def create_rest_app() -> FastAPI:
    """Создает и возвращает FastAPI-приложение для запуска пайплайнов."""

    app = FastAPI(title="BioETL REST Interface")

    @app.post("/pipelines/run", response_model=PipelineRunResponse)
    async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
        """Run a pipeline via REST API."""
        domain_request = RunPipelineRequest(
            pipeline_name=request.pipeline_name,
            profile=request.profile,
            dry_run=request.dry_run,
            limit=request.limit,
            require_rest_interface=True,
        )

        use_case = get_use_case_factory().create_run_pipeline_use_case()

        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(None, use_case.execute, domain_request)
        except InterfaceDisabledError:
            raise HTTPException(status_code=503, detail="REST interface disabled")

        return PipelineRunResponse(
            run_id=response.run_id,
            success=response.success,
            row_count=response.row_count,
            duration_sec=response.duration_sec,
            errors=response.errors,
        )

    return app


__all__ = ["create_rest_app", "PipelineRunRequest", "PipelineRunResponse"]
