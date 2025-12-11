"""Minimal REST server for running pipelines via RunPipelineUseCase."""

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
    """Pipeline run request."""

    pipeline_name: str = Field(
        ..., description="Pipeline name in entity_provider format"
    )
    profile: str = Field(default="default", description="Active configuration profile")
    dry_run: bool = Field(default=False, description="Run without writing output")
    limit: int | None = Field(default=None, description="Record count limit")


class PipelineRunResponse(BaseModel):
    """Pipeline execution result response."""

    run_id: str
    success: bool
    row_count: int
    duration_sec: float
    errors: list[str]


def create_rest_app() -> FastAPI:
    """Create and return FastAPI application for running pipelines."""

    app = FastAPI(title="BioETL REST Interface")

    @app.post("/pipelines/run", response_model=PipelineRunResponse)
    async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
        """Run a pipeline asynchronously and return execution result."""
        # 1. Map REST DTO to application DTO
        domain_request = RunPipelineRequest(
            pipeline_name=request.pipeline_name,
            profile=request.profile,
            dry_run=request.dry_run,
            limit=request.limit,
            require_rest_interface=True,
        )

        # 2. Get use case via factory
        use_case = get_use_case_factory().create_run_pipeline_use_case()

        # 3. Execute in thread pool
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None, use_case.execute, domain_request
            )
        except InterfaceDisabledError:
            raise HTTPException(status_code=503, detail="REST interface is disabled")

        # 4. Map application response to REST response
        return PipelineRunResponse(
            run_id=response.run_id,
            success=response.success,
            row_count=response.row_count,
            duration_sec=response.duration_sec,
            errors=response.errors,
        )

    return app


__all__ = ["create_rest_app", "PipelineRunRequest", "PipelineRunResponse"]
