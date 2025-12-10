"""REST interface for BioETL pipeline execution.

This module provides a FastAPI-based HTTP API for running pipelines remotely.

Available endpoints:
    - POST /pipelines/run: Execute a pipeline with specified configuration

Request/Response models:
    - PipelineRunRequest: Input parameters for pipeline execution
    - PipelineRunResponse: Execution results including run_id, success status, metrics

Example usage:
    from bioetl.interfaces.rest import create_rest_app

    app = create_rest_app()

    # Run with uvicorn
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

from bioetl.interfaces.rest.server import (
    PipelineRunRequest,
    PipelineRunResponse,
    create_rest_app,
)

__all__ = [
    # Factory
    "create_rest_app",
    # Request/Response DTOs
    "PipelineRunRequest",
    "PipelineRunResponse",
]
